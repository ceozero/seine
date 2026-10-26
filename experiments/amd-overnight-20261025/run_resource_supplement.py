#!/usr/bin/python3
"""Supplement an archived fixture failure without rewriting any earlier evidence."""
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
UNIT = 'seine-amd-resource-supplement.service'
CHILDREN = ['seine-overnight-supplement-' + suffix + '.service' for suffix in
            ('lifecycle-first', 'cpu-load', 'lifecycle-restart', 'lifecycle-optout')]
CAP = Path('/sys/devices/platform/AMDI0097:00/hwmon/hwmon4/power1_cap')


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def counters():
    data = dict(line.split() for line in Path('/proc/vmstat').read_text().splitlines())
    return {key: int(data[key]) for key in ('pswpin', 'pswpout', 'oom_kill')}


def check_pools():
    return all(int(path.read_text()) == 0 for path in
               Path('/sys/kernel/mm/hugepages').glob('hugepages-*/nr_hugepages'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deadline-epoch', type=float, required=True)
    args = parser.parse_args()
    assert os.geteuid() == 0 and time.time() + 1500 < args.deadline_epoch
    expected = json.loads((ROOT / 'expected-files.json').read_text())
    for name, sha in expected.items():
        assert digest(ROOT / name) == sha, name
    provenance = json.loads((ROOT / 'supplement-provenance.json').read_text())
    assert expected['candidate'] == provenance['original_candidate_sha256']
    previous = json.loads((ROOT / 'original-collection-verification.json').read_text())
    assert previous['archive_sha256'] == provenance['original_archive_sha256']
    assert previous['outcome']['status'] == 'FAILED'
    assert previous['outcome']['settings_restored'] and not previous['outcome']['cleanup_failures']
    active = subprocess.check_output(['systemctl', 'list-units', '--type=service',
        '--state=active,activating,deactivating,reloading', '--no-legend', '--plain',
        'seine-amd-*', 'seine-overnight-*', 'seine-cherry-*'], text=True, timeout=30)
    assert all(line.split()[0] == UNIT for line in active.splitlines() if line.strip()), active
    hardware = {v['field'].rstrip(':'): v['data'] for v in json.loads(
        subprocess.check_output(['lscpu', '-J'], text=True))['lscpu']}
    assert (hardware['Vendor ID'], hardware['CPU family'], hardware['Model']) == ('AuthenticAMD', '26', '2')
    assert check_pools() and int(CAP.read_text()) == 280_000_000
    swaps = Path('/proc/swaps').read_text().splitlines()
    assert len(swaps) == 2 and swaps[1].split()[0] == '/swap.img' and int(swaps[1].split()[3]) == 0
    OUT.mkdir(exist_ok=False)
    def interrupt(signum, frame):
        raise InterruptedError(signum)
    signal.signal(signal.SIGINT, interrupt)
    signal.signal(signal.SIGTERM, interrupt)
    save('protocol.json', {'candidate_sha256': expected['candidate'], 'hardware': hardware,
        'original_archive_sha256': provenance['original_archive_sha256'],
        'initial_seconds': 600, 'memory_recovery_seconds': 90,
        'injected_bytes_maximum': 2 * 1024**3, 'injection_seconds': 20,
        'cpus': '0-3', 'page_mode': 'regular', 'worker_ceiling': 4,
        'deadline_epoch': args.deadline_epoch, 'original_swaps': swaps,
        'scope': 'Separate resource-only supplement. Original failed campaign and all productive windows remain unchanged.'})
    before = counters()
    status, failure, child = 'FAILED', None, None
    try:
        subprocess.run(['swapoff', '/swap.img'], check=True, timeout=30)
        save('progress.json', {'phase': 'resource-lifecycle', 'at_epoch': time.time()})
        with (OUT / 'resource-lifecycle.log').open('w') as log:
            child = subprocess.Popen([sys.executable, '-B', str(ROOT / 'lifecycle.py'),
                '--binary', str(ROOT / 'candidate'), '--cpus', '0-3', '--page', 'regular',
                '--initial-seconds', '600'], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True)
            assert child.wait(timeout=1380) == 0, 'supplemental lifecycle failed'
        assert (OUT / 'lifecycle/COMPLETE').exists()
        for name, sha in expected.items():
            assert digest(ROOT / name) == sha, name
        status = 'COMPLETE'
    except BaseException as error:
        failure = repr(error)
        raise
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        cleanup = []
        if child is not None and child.poll() is None:
            try:
                os.killpg(child.pid, signal.SIGINT)
                try:
                    child.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=10)
            except ProcessLookupError:
                pass
            except Exception as error:
                cleanup.append('lifecycle child: ' + repr(error))
        for unit in CHILDREN:
            try:
                result = subprocess.run(['systemctl', 'stop', unit], capture_output=True, text=True, timeout=30)
                if result.returncode and 'not loaded' not in result.stderr:
                    cleanup.append(unit + ': ' + result.stderr)
                state = subprocess.check_output(['systemctl', 'show', unit, '--property=ActiveState',
                                                 '--value'], text=True, timeout=15).strip()
                assert state not in ('active', 'activating', 'deactivating'), (unit, state)
            except Exception as error:
                cleanup.append(unit + ': ' + repr(error))
        try:
            if len(Path('/proc/swaps').read_text().splitlines()) == 1:
                subprocess.run(['swapon', '/swap.img'], check=True, timeout=30)
        except Exception as error:
            cleanup.append('swap restore: ' + repr(error))
        restored = check_pools() and int(CAP.read_text()) == 280_000_000 and any(
            line.split()[0] == '/swap.img' and int(line.split()[3]) == 0
            for line in Path('/proc/swaps').read_text().splitlines()[1:])
        delta = {key: value - before[key] for key, value in counters().items()}
        save('vm-checks.json', delta)
        if any(delta.values()):
            cleanup.append('swap/OOM counters changed')
        save('outcome.json', {'status': status if restored and not cleanup else 'FAILED',
            'failure': failure, 'settings_restored': restored, 'cleanup_failures': cleanup,
            'finished_at_epoch': time.time()})
        save('manifest.json', {str(path.relative_to(OUT)): digest(path)
            for path in OUT.rglob('*') if path.is_file() and path.name != 'manifest.json'})
        assert restored and not cleanup, cleanup


if __name__ == '__main__':
    main()
