#!/usr/bin/env python3
"""Bounded full-socket automatic-tuner experiment on one qualified owned host."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from bench import counters, paired

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'results'
POOL = Path('/proc/sys/vm/nr_hugepages')
CAP = Path('/sys/devices/platform/AMDI0097:00/hwmon/hwmon4/power1_cap')


def save(name, value):
    path = OUT / name
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def interrupted(signum, frame):
    raise InterruptedError(signum)


def run(label, command, timeout, deadline):
    assert time.time() + timeout + 120 < deadline, 'insufficient time for ' + label
    save('progress.json', {'phase': label, 'at_epoch': time.time()})
    print(label, 'starting', flush=True)
    with (OUT / (label + '.log')).open('w') as log:
        child = subprocess.Popen(command, cwd=ROOT, stdout=log,
                                 stderr=subprocess.STDOUT, start_new_session=True)
        try:
            assert child.wait(timeout=timeout) == 0, label + ' failed; inspect its log'
        finally:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGINT)
                try:
                    child.wait(timeout=45)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=10)
    print(label, 'complete', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deadline-epoch', type=float, required=True)
    args = parser.parse_args()
    os.chdir(ROOT)
    assert os.geteuid() == 0
    assert time.time() + 14400 + 120 < args.deadline_epoch
    fields = {r['field'].rstrip(':'): r['data'] for r in json.loads(
        subprocess.check_output(['lscpu', '-J'], text=True))['lscpu']}
    assert fields['Vendor ID'] == 'AuthenticAMD'
    assert int(fields['CPU family']) == 26 and int(fields['Model']) == 2
    assert int(fields['CPU(s)']) == 64 and int(fields['Socket(s)']) == 1
    assert int(fields['NUMA node(s)']) == 1
    assert int(POOL.read_text()) == 0 and int(CAP.read_text()) == 280_000_000
    original_swaps = Path('/proc/swaps').read_text().splitlines()
    assert len(original_swaps) == 2 and original_swaps[1].split()[0] == '/swap.img'
    assert int(original_swaps[1].split()[3]) == 0
    prior = json.loads(Path('/root/seine-energy-20261025/power-results/outcome.json').read_text())
    assert prior['status'] == 'COMPLETE' and prior['settings_restored'] and not prior['cleanup_failures']
    expected = json.loads((ROOT / 'expected-files.json').read_text())
    for name, digest in expected.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    OUT.mkdir(exist_ok=False)
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    order = [(binary, pair) for pair in range(1, 5)
             for binary in (('control', 'candidate') if pair % 2 else ('candidate', 'control'))]
    labels = ['joint-plumbing'] + [f'joint-{b}-{p}' for b, p in order]
    labels += [f'joint-warm-{b}-{p}' for b, p in reversed(order)]
    save('protocol.json', {'order': order, 'cold_seconds': 1200, 'warm_seconds': 180,
        'cpu_count': 64, 'thread_count_override': None, 'kernel_override': None,
        'page_mode': 'large', 'affinity': 'auto', 'cap_uw': int(CAP.read_text()),
        'initial_swaps': original_swaps, 'deadline_epoch': args.deadline_epoch,
        'controller_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'hardware': fields, 'binary_sha256': {k: expected[k] for k in ('control', 'candidate')}})
    before = counters()
    status, failure = 'FAILED', None
    try:
        subprocess.run(['swapoff', '/swap.img'], check=True, timeout=30)
        run('reference-parity', ['./verify_streaming_dispatch'], 180, args.deadline_epoch)
        parity = (OUT / 'reference-parity.log').read_text().splitlines()
        assert len([line for line in parity if line.startswith('PASS nonce=')]) == 21
        run('joint-plumbing', [sys.executable, '-B', 'productive.py', '--binary', 'control',
            '--label', 'joint-plumbing', '--seconds', '60'], 180, args.deadline_epoch)
        assert (OUT / 'joint-plumbing/COMPLETE').exists()
        save('progress.json', {'phase': 'fixed-streaming-control', 'at_epoch': time.time()})
        POOL.write_text('32768\n')
        assert int(POOL.read_text()) == 32768
        paired(ROOT, OUT / 'fixed-streaming-control',
               {'binary': 'control', 'kernel': 'avx512-256-stream'},
               {'binary': 'candidate', 'kernel': 'avx512-256-stream'},
               32, pairs=3, seconds=20, rounds=2, warmup=1)
        POOL.write_text('0\n')
        for binary, pair in order:
            label = f'joint-{binary}-{pair}'
            run(label, [sys.executable, '-B', 'productive.py', '--binary', binary,
                        '--label', label, '--seconds', '1200'], 1320, args.deadline_epoch)
            assert (OUT / label / 'COMPLETE').exists()
            assert int(POOL.read_text()) == 0 and int(CAP.read_text()) == 280_000_000
        for binary, pair in reversed(order):
            label = f'joint-warm-{binary}-{pair}'
            run(label, [sys.executable, '-B', 'productive.py', '--binary', binary,
                        '--label', label, '--seconds', '180', '--cache-source',
                        str(OUT / f'joint-{binary}-{pair}')], 300, args.deadline_epoch)
            assert (OUT / label / 'COMPLETE').exists()
        run('resource-lifecycle', [sys.executable, '-B', 'lifecycle.py', '--binary', 'candidate',
            '--initial-seconds', '600', '--page', 'regular', '--cpus', '0-3'], 1350, args.deadline_epoch)
        assert (OUT / 'lifecycle/COMPLETE').exists()
        delta = {k: v - before[k] for k, v in counters().items()}
        save('vm-checks.json', delta)
        assert all(delta[k] == 0 for k in ('pswpin', 'pswpout', 'oom_kill'))
        for name, digest in expected.items():
            assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
        status = 'COMPLETE'
    except BaseException as error:
        failure = repr(error)
        raise
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        cleanup = []
        for label in labels + ['lifecycle-first', 'lifecycle-restart', 'lifecycle-optout', 'cpu-load']:
            unit = 'seine-overnight-' + label + '.service'
            try:
                subprocess.run(['systemctl', 'stop', unit], capture_output=True, timeout=30)
                state = subprocess.check_output(['systemctl', 'show', unit,
                    '--property=ActiveState', '--value'], text=True, timeout=15).strip()
                assert state not in ('active', 'activating', 'deactivating'), unit
            except Exception as error:
                cleanup.append(label + ': ' + repr(error))
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
        save('outcome.json', {'status': status if restored and not cleanup else 'FAILED',
            'failure': failure, 'settings_restored': restored, 'cleanup_failures': cleanup,
            'finished_at_epoch': time.time()})
        save('manifest.json', {str(p.relative_to(OUT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in OUT.rglob('*') if p.is_file() and p.name != 'manifest.json'})
        assert restored and not cleanup, cleanup
    print(status, flush=True)


if __name__ == '__main__':
    main()
