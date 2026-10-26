#!/usr/bin/python3
"""Wait for free quota, run one frozen lease, collect evidence and always clean up."""
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import tarfile
import time

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / 'data/genoa-streaming-20261025'
FROZEN = DATA / 'frozen'
LEASE = DATA / 'genoa-productive-20261025'
CLOUD = REPO / 'experiments/cpu-followups-20261025/cloud.py'
REMOTE = '/home/ubuntu/genoa-validation'
UNIT = 'seine-genoa-validation.service'
RATE = 1.64224


def run(command, timeout=90, check=True):
    return subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=check)


def aws(service, action, *args):
    return json.loads(run(['aws', '--profile', 'seine-bench', '--region', 'us-east-1',
                           service, action, *args, '--output', 'json']).stdout or '{}')


def save(name, value):
    p = DATA / name
    tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    tmp.replace(p)


def cloud(action, *args):
    try:
        return run([sys.executable, str(CLOUD), action, '--root', str(LEASE), *args], timeout=180)
    except subprocess.CalledProcessError as error:
        (DATA / ('cloud-' + action + '-error.log')).write_text(error.stderr or '')
        raise


def ssh(command, timeout=30, check=True):
    return run(['ssh', '-F', str(LEASE / 'ssh-config'), 'ep', command], timeout, check)


def owned_instance():
    state = json.loads((LEASE / 'session.json').read_text())
    instance = aws('ec2', 'describe-instances', '--instance-ids', state['instance_id'])['Reservations'][0]['Instances'][0]
    tags = {t['Key']: t['Value'] for t in instance['Tags']}
    assert tags['Experiment'] == LEASE.name and tags['Project'] == 'seine-avx2-validation'
    return instance


def interrupted(signum, frame):
    raise InterruptedError(signum)


def main():
    assert hasattr(tarfile, 'data_filter'), 'use /usr/bin/python3 with safe tar extraction support'
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    assert not (DATA / 'operation.json').exists(), 'one lease only; inspect previous operation before retrying'
    budget = json.loads((DATA / 'budget.json').read_text())
    assert budget['total_cap_usd'] == 3.25 and budget['max_lease_minutes'] == 110
    manifest = json.loads((DATA / 'bundle-manifest.json').read_text())
    for name, digest in manifest.items():
        assert hashlib.sha256((FROZEN / name).read_bytes()).hexdigest() == digest, name
    # Use the live standard-vCPU limit, and wait instead of changing another run.
    quota = aws('service-quotas', 'get-service-quota', '--service-code', 'ec2',
                '--quota-code', 'L-1216C47A')['Quota']['Value']
    wait_until = time.monotonic() + 40 * 60
    while True:
        # A terminating instance may still hold quota during shutdown. Count
        # it conservatively until AWS reports termination, not just until its
        # state stops being "running".
        active = aws('ec2', 'describe-instances', '--filters',
                     'Name=instance-state-name,Values=pending,running,stopping,shutting-down')
        instances = [i for r in active['Reservations'] for i in r['Instances']
                     if i['InstanceType'][0] in 'acdhimrtz' and i.get('InstanceLifecycle') != 'spot']
        types = sorted({i['InstanceType'] for i in instances})
        vcpus = ({t['InstanceType']: t['VCpuInfo']['DefaultVCpus'] for t in aws(
            'ec2', 'describe-instance-types', '--instance-types', *types)['InstanceTypes']} if types else {})
        used = sum(vcpus[i['InstanceType']] for i in instances)
        save('quota.json', {'quota': quota, 'used': used, 'needed': 32})
        if quota - used >= 32:
            break
        assert time.monotonic() < wait_until, 'quota did not become free; no server launched'
        print('Waiting for quota:', used, '/', quota, flush=True)
        # Other owned campaigns reuse the entire quota between short gaps.
        # Observe free capacity promptly without touching their instances. This
        # changes only pre-launch waiting, never the frozen measurement protocol.
        time.sleep(5)
    started = time.time()
    save('operation.json', {'status': 'launching', 'started_at': started, 'cap_usd': 3.25})
    lease_created = False
    try:
        cloud('launch', '--type', 'c7a.8xlarge', '--minutes', '110', '--image', 'ami-0d6dd9e8265d48906',
              '--vpc', 'vpc-011004097d89589bb', '--subnet', 'subnet-0175eae5171bc2a55')
        lease_created = True
        instance = owned_instance()
        mode = aws('ec2', 'describe-instance-attribute', '--instance-id', instance['InstanceId'],
                   '--attribute', 'instanceInitiatedShutdownBehavior')
        assert mode['InstanceInitiatedShutdownBehavior']['Value'] == 'terminate'
        save('shutdown-behavior.json', {'mode': 'terminate'})
        for attempt in range(30):
            try:
                cloud('connect')
                if ssh('true', check=False).returncode == 0:
                    break
            except (subprocess.SubprocessError, KeyError):
                pass
            if attempt == 29:
                raise RuntimeError('SSH did not become ready')
            time.sleep(5)
        ssh('sudo cloud-init status --wait', timeout=180)
        assert ssh('systemctl is-active seine-expiry.timer').stdout.strip() == 'active'
        ssh('mkdir -p ' + REMOTE)
        run(['scp', '-q', '-F', str(LEASE / 'ssh-config'),
             *[str(FROZEN / name) for name in manifest], str(DATA / 'binary-provenance.json'),
             'ep:' + REMOTE + '/'], timeout=120)
        ssh('chmod +x ' + REMOTE + '/control ' + REMOTE + '/candidate ' + REMOTE + '/verify_streaming_dispatch')
        command = ['sudo', 'systemd-run', '--quiet', '--unit=' + UNIT, '--uid=ubuntu',
                   '--property=Type=exec', '--property=WorkingDirectory=' + REMOTE,
                   '--property=RuntimeMaxSec=6240', '--property=TimeoutStopSec=120',
                   '--property=KillSignal=SIGINT', '--property=StandardOutput=append:' + REMOTE + '/controller.log',
                   '--property=StandardError=append:' + REMOTE + '/controller.log',
                   '/usr/bin/python3', REMOTE + '/run.py']
        ssh(shlex.join(command))
        save('operation.json', {'status': 'running', 'started_at': started, 'cap_usd': 3.25})
        while True:
            # Leave several minutes to archive and terminate before VM expiry.
            if time.time() - started > 106 * 60:
                ssh('sudo systemctl stop ' + UNIT, timeout=150)
                break
            state = ssh('systemctl show ' + UNIT + ' --property=ActiveState --value').stdout.strip()
            progress = ssh('cat ' + REMOTE + '/results/progress.json 2>/dev/null || true').stdout.strip()
            save('progress.json', {'service': state, 'remote': progress, 'elapsed_secs': time.time() - started})
            print(state, progress, flush=True)
            if state not in ('active', 'activating', 'deactivating'):
                break
            time.sleep(30)
        # Preserve the controller log even if an early preflight made no archive.
        run(['scp', '-q', '-F', str(LEASE / 'ssh-config'), 'ep:' + REMOTE + '/controller.log',
             str(DATA / 'remote-controller.log')], timeout=30)
        run(['scp', '-q', '-F', str(LEASE / 'ssh-config'), 'ep:' + REMOTE + '/results.tar.gz',
             str(DATA / 'results.tar.gz')], timeout=120)
        dest = DATA / 'collected'
        dest.mkdir(exist_ok=False)
        with tarfile.open(DATA / 'results.tar.gz') as archive:
            archive.extractall(dest, filter='data')
        records = json.loads((dest / 'result-manifest.json').read_text())
        for name, digest in records.items():
            assert hashlib.sha256((dest / name).read_bytes()).hexdigest() == digest, name
        save('archive-verification.json', {'verified_files': len(records),
             'sha256': hashlib.sha256((DATA / 'results.tar.gz').read_bytes()).hexdigest()})
        outcome = json.loads((dest / 'results/outcome.json').read_text())
        save('operation.json', {'status': outcome['status'], 'started_at': started, 'outcome': outcome})
        assert outcome['status'] == 'COMPLETE', outcome
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        if (LEASE / 'session.json').exists():
            state = json.loads((LEASE / 'session.json').read_text())
            if 'instance_id' not in state and (LEASE / 'launch.json').exists():
                # A RunInstances transport error can occur after AWS accepted
                # the launch. Recover only this task's unique launch tags.
                found = aws('ec2', 'describe-instances', '--filters',
                            'Name=tag:Experiment,Values=' + LEASE.name,
                            'Name=tag:Name,Values=seine-' + LEASE.name,
                            'Name=tag:Project,Values=seine-avx2-validation')
                instances = [i for r in found['Reservations'] for i in r['Instances']]
                assert len(instances) <= 1, 'ambiguous launch ownership; do not terminate'
                if instances:
                    state['instance_id'] = instances[0]['InstanceId']
                    (LEASE / 'session.json').write_text(json.dumps(state, indent=2) + '\n')
            if 'instance_id' in state:
                # Verify both ledger ID and unique task tag before destructive cleanup.
                instance = owned_instance()
                cloud('cleanup')
                launched = dt.datetime.fromisoformat(instance['LaunchTime'].replace('Z', '+00:00')).timestamp()
                hours = math.ceil((time.time() - launched) / 60) / 60
                cost = hours * (RATE + 0.005 + 8 * 0.08 / 730) + 0.10
                save('spending.json', {'hours_rounded_up': hours, 'upper_estimate_usd': cost,
                                      'cap_usd': 3.25, 'basis': 'on-demand compute, 8 GiB gp3, IPv4, $0.10 transfer allowance'})
                assert cost <= 3.25, cost
            elif not lease_created:
                # Launch failure may leave only the security group. The existing
                # helper removes just that recorded group and the temporary key.
                cloud('cleanup')
        print('Owned lease cleanup finished', flush=True)


if __name__ == '__main__':
    main()
