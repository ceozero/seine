#!/usr/bin/env python3
"""Bounded ring screen; run only after collecting the prior experiment."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'results'
POOL = Path('/proc/sys/vm/nr_hugepages')
CAP = Path('/sys/devices/platform/AMDI0097:00/hwmon/hwmon4/power1_cap')
KERNEL = 'avx512-256-stream'


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def interrupted(signum, frame):
    raise InterruptedError(signum)


def run(label, command, timeout, deadline, required=True):
    assert time.time() + timeout + 120 < deadline, 'insufficient time for ' + label
    save(OUT / 'progress.json', {'phase': label, 'at_epoch': time.time()})
    print(label, 'starting', flush=True)
    with (OUT / (label + '.log')).open('w') as log:
        child = subprocess.Popen(command, cwd=ROOT, stdout=log,
                                 stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = child.wait(timeout=timeout)
            if required:
                assert code == 0, label + ' failed; inspect log'
        finally:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGINT)
                try:
                    child.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=10)
    return code


def paired(args):
    from bench import paired as measure
    measure(ROOT, OUT / args.label,
            {'binary': 'ring-64', 'kernel': KERNEL},
            {'binary': 'ring-' + str(args.ring), 'kernel': KERNEL},
            args.workers, pairs=args.pairs, seconds=args.seconds, rounds=2, warmup=1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deadline-epoch', type=float)
    parser.add_argument('--paired', action='store_true')
    parser.add_argument('--label')
    parser.add_argument('--ring', type=int, choices=(16, 32))
    parser.add_argument('--workers', type=int, choices=(32, 64))
    parser.add_argument('--pairs', type=int)
    parser.add_argument('--seconds', type=int)
    args = parser.parse_args()
    if args.paired:
        return paired(args)
    assert args.deadline_epoch and time.time() + 2400 < args.deadline_epoch
    assert os.geteuid() == 0
    os.chdir(ROOT)
    assert not OUT.exists(), 'never overwrite measurements'
    prior_path = Path('/root/seine-overnight-20261025/results/outcome.json')
    prior = json.loads(prior_path.read_text())
    assert prior['settings_restored'] and not prior['cleanup_failures']
    assert (ROOT / 'prior-evidence-collected.json').is_file(), 'collect prior evidence first'
    state = subprocess.check_output(['systemctl', 'show', 'seine-amd-productive.service',
        '--property=ActiveState', '--value'], text=True).strip()
    assert state not in ('active', 'activating', 'deactivating')
    fields = {v['field'].rstrip(':'): v['data'] for v in json.loads(
        subprocess.check_output(['lscpu', '-J'], text=True))['lscpu']}
    assert fields['Vendor ID'] == 'AuthenticAMD'
    assert int(fields['CPU family']) == 26 and int(fields['Model']) == 2
    assert int(fields['CPU(s)']) == 64 and int(fields['Socket(s)']) == 1
    assert int(fields['NUMA node(s)']) == 1
    assert int(POOL.read_text()) == 0 and int(CAP.read_text()) == 280_000_000
    swaps = Path('/proc/swaps').read_text().splitlines()
    assert len(swaps) == 2 and swaps[1].split()[0] == '/swap.img'
    assert int(swaps[1].split()[3]) == 0
    expected = json.loads((ROOT / 'expected-files.json').read_text())
    for name, sha in expected.items():
        assert digest(ROOT / name) == sha, name
    OUT.mkdir()
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    save(OUT / 'protocol.json', {'hardware': fields, 'initial_swaps': swaps,
        'cap_uw': int(CAP.read_text()), 'deadline_epoch': args.deadline_epoch,
        'seconds': 15, 'rounds': 2, 'warmup_rounds': 1, 'pairs': 2,
        'workers': [32, 64], 'ring_order': [32, 16],
        'candidate_selection': 'Largest positive geometric screen delta; screen is not confirmation',
        'expected_files': expected, 'prior_outcome_sha256': digest(prior_path)})
    status, failure = 'FAILED', None
    try:
        subprocess.run(['swapoff', '/swap.img'], check=True, timeout=30)
        for ring in (64, 32, 16):
            label = 'reference-ring-' + str(ring)
            run(label, [str(ROOT / ('verify-ring-' + str(ring)))], 240, args.deadline_epoch)
            lines = (OUT / (label + '.log')).read_text().splitlines()
            assert sum(line.startswith('PASS nonce=') for line in lines) == 21
        POOL.write_text('65536\n')
        assert int(POOL.read_text()) == 65536
        events = json.loads(subprocess.check_output(['perf', 'list', '--json'], text=True))
        wanted = ('cycles', 'instructions', 'l2_cache_req_stat.dc_access_in_l2',
                  'l2_cache_req_stat.ls_rd_blk_c')
        selected = [event for event in events if event.get('EventName') in wanted]
        save(OUT / 'perf-event-definitions.json', selected)
        if {v['EventName'] for v in selected} == set(wanted):
            for workers in (32, 64):
                label = 'profile-control-' + str(workers)
                # Whole invocation, including allocation and teardown, with no
                # uncounted warmup. Core L2 requests are not DRAM bandwidth.
                command = [sys.executable, '-B', str(ROOT / 'profile.py'), '--workers', str(workers)]
                code = run(label, command, 120, args.deadline_epoch, required=False)
                save(OUT / (label + '-status.json'), {'exit_code': code,
                    'interpretation': 'Diagnostic only; validate counter scheduling and report before interpreting.'})
        else:
            save(OUT / 'profile-unavailable.json', {'reason': 'required event definitions missing'})
        screens = []
        for workers in (32, 64):
            for ring in (32, 16):
                label = f'screen-{workers}-ring-{ring}'
                run(label, [sys.executable, '-B', str(Path(__file__).resolve()), '--paired',
                    '--label', label, '--ring', str(ring), '--workers', str(workers),
                    '--pairs', '2', '--seconds', '15'], 360, args.deadline_epoch)
                summary = json.loads((OUT / label / 'summary.json').read_text())
                screens.append({'workers': workers, 'ring': ring, 'label': label, **summary})
        shortlist = max(screens, key=lambda s: s['paired_geometric_delta_pct'])
        save(OUT / 'screen-selection.json', {'screens': screens,
            'shortlist': shortlist if shortlist['paired_geometric_delta_pct'] > 0 else None,
            'shipping_change_accepted': False})
        for name, sha in expected.items():
            assert digest(ROOT / name) == sha, name
        status = 'COMPLETE'
    except BaseException as error:
        failure = repr(error)
        raise
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        cleanup = []
        for label, action in (
            ('hugepages', lambda: POOL.write_text('0\n')),
            ('swap', lambda: subprocess.run(['swapon', '/swap.img'], check=True, timeout=30)
             if len(Path('/proc/swaps').read_text().splitlines()) == 1 else None),
        ):
            try:
                action()
            except Exception as error:
                cleanup.append(label + ': ' + repr(error))
        restored = (int(POOL.read_text()) == 0 and int(CAP.read_text()) == 280_000_000
            and any(line.split()[0] == '/swap.img'
                    for line in Path('/proc/swaps').read_text().splitlines()[1:]))
        save(OUT / 'outcome.json', {'status': status if restored and not cleanup else 'FAILED',
            'failure': failure, 'settings_restored': restored, 'cleanup_failures': cleanup,
            'finished_at_epoch': time.time()})
        save(OUT / 'manifest.json', {str(p.relative_to(OUT)): digest(p)
            for p in OUT.rglob('*') if p.is_file() and p.name != 'manifest.json'})
        assert restored and not cleanup, cleanup


if __name__ == '__main__':
    main()
