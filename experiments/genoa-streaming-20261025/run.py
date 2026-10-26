#!/usr/bin/env python3
"""Frozen, bounded Genoa validation on one exclusively owned disposable VM."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

from bench import counters, paired

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'results'
START = time.monotonic()
BUDGET = 104 * 60


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def interrupt(signum, frame):
    raise InterruptedError(signum)


def run(label, command, timeout):
    remaining = BUDGET - (time.monotonic() - START)
    if remaining < timeout:
        raise RuntimeError('insufficient remaining campaign time for ' + label)
    save(OUT / 'progress.json', {'phase': label, 'elapsed_secs': time.monotonic() - START})
    print(label, 'starting', flush=True)
    with (OUT / (label + '.log')).open('w') as log:
        child = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                 start_new_session=True)
        try:
            if child.wait(timeout=timeout):
                raise RuntimeError(label + ' failed; inspect its log')
        finally:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGINT)
                try:
                    child.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=5)
    print(label, 'complete', flush=True)


def main():
    os.chdir(ROOT)
    OUT.mkdir(exist_ok=False)
    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGINT, interrupt)
    expected = json.loads((ROOT / 'expected-binaries.json').read_text())
    for name, digest in expected.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    hardware = json.loads(subprocess.check_output(['lscpu', '-J'], text=True))
    save(OUT / 'hardware.json', hardware)
    fields = {r['field'].rstrip(':'): r['data'] for r in hardware['lscpu']}
    assert fields['Vendor ID'] == 'AuthenticAMD'
    assert int(fields['CPU family']) == 25 and int(fields['Model']) == 17
    # Prior c7a.8xlarge native evidence reports KVM through lscpu. This is an
    # EC2 Linux VM, not a bare-metal host; both labels identify that scope.
    assert int(fields['CPU(s)']) == 32 and fields.get('Hypervisor vendor') in ('KVM', 'AWS')
    assert int(fields['Thread(s) per core']) == 1
    assert {'avx2', 'avx512f', 'avx512vl'} <= set(fields['Flags'].split())
    assert len(Path('/proc/swaps').read_text().splitlines()) == 1
    assert subprocess.check_output(['systemctl', 'is-active', 'seine-expiry.timer'], text=True).strip() == 'active'
    (OUT / 'expiry-timer.txt').write_text(subprocess.check_output(
        ['systemctl', 'list-timers', 'seine-expiry.timer', '--all'], text=True))
    pool = Path('/proc/sys/vm/nr_hugepages')
    assert int(pool.read_text()) == 0
    before = counters()
    status, failure = 'FAILED', None
    sources = OUT / 'protocol-source'
    sources.mkdir()
    for path in ROOT.glob('*.py'):
        shutil.copy2(path, sources / path.name)
    try:
        run('reference-parity', ['./verify_streaming_dispatch'], 180)
        subprocess.run(['sudo', 'sysctl', '-w', 'vm.nr_hugepages=24576'], check=True, timeout=30)
        assert int(pool.read_text()) == 24576
        save(OUT / 'progress.json', {'phase': 'fixed-avx2-control', 'elapsed_secs': time.monotonic() - START})
        paired(ROOT, OUT / 'fixed-avx2-control',
               {'binary': 'control', 'kernel': 'avx2'},
               {'binary': 'candidate', 'kernel': 'avx2'},
               24, pairs=2, seconds=15, rounds=2, warmup=1)
        subprocess.run(['sudo', 'sysctl', '-w', 'vm.nr_hugepages=0'], check=True, timeout=30)
        order = [('control', 'a'), ('candidate', 'a'), ('candidate', 'b'), ('control', 'b')]
        for binary, suffix in order:
            label = f'joint-{binary}-{suffix}'
            run(label, ['python3', 'joint_probe.py', '--binary', binary, '--label', label,
                        '--seconds', '900', '--workers', '24'], 1020)
            assert (OUT / label / 'COMPLETE').exists()
        for binary, suffix in reversed(order):
            label = f'joint-warm-{binary}-{suffix}'
            run(label, ['python3', 'joint_probe.py', '--binary', binary, '--label', label,
                        '--seconds', '180', '--workers', '24', '--cache-source',
                        str(OUT / f'joint-{binary}-{suffix}')], 300)
            assert (OUT / label / 'COMPLETE').exists()
        run('resource-lifecycle', ['python3', 'lifecycle_source.py', '--binary', 'candidate',
                                  '--initial-seconds', '600', '--page', 'regular', '--cpus', '0-3'], 1350)
        assert (OUT / 'lifecycle' / 'COMPLETE').exists()
        delta = {k: v - before[k] for k, v in counters().items()}
        save(OUT / 'vm-checks.json', delta)
        assert all(delta[k] == 0 for k in ('pswpin', 'pswpout', 'oom_kill')), delta
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
        units = [f'joint-{warm}{binary}-{suffix}' for binary in ['control', 'candidate']
                 for suffix in ['a', 'b'] for warm in ['', 'warm-']]
        units += ['cpu-load', 'lifecycle-first', 'lifecycle-restart', 'lifecycle-optout']
        for name in units:
            unit = 'seine-campaign-' + name + '.service'
            try:
                subprocess.run(['sudo', 'systemctl', 'stop', unit], capture_output=True, timeout=30)
                active = subprocess.check_output(['systemctl', 'show', unit, '--property=ActiveState', '--value'],
                                                 text=True, timeout=15).strip()
                assert active not in ('active', 'activating', 'deactivating'), unit
            except Exception as error:
                cleanup.append(str(error))
        try:
            subprocess.run(['sudo', 'sysctl', '-w', 'vm.nr_hugepages=0'], check=True, timeout=30)
            assert int(pool.read_text()) == 0
        except Exception as error:
            cleanup.append(str(error))
        if cleanup:
            status = 'FAILED'
        save(OUT / 'outcome.json', {'status': status, 'failure': failure, 'cleanup_failures': cleanup,
                                  'elapsed_secs': time.monotonic() - START})
        save(ROOT / 'result-manifest.json', {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                          for p in OUT.rglob('*') if p.is_file()})
        subprocess.run(['tar', '-czf', 'results.tar.gz', 'results', 'result-manifest.json',
                        'expected-binaries.json'], check=True, timeout=60)
        assert not cleanup, cleanup
    print(status, flush=True)


if __name__ == '__main__':
    main()
