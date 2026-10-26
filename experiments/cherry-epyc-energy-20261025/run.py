#!/usr/bin/env python3
"""Bounded package-energy sweep on an already qualified, exclusively owned host."""
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


def save(name, value):
    p = OUT / name
    temporary = p.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(p)


def interrupt(signum, frame):
    raise InterruptedError(signum)


def run(label, argv, timeout, deadline):
    assert time.time() + timeout + 120 < deadline, 'leave collection time before deadline'
    save('progress.json', {'phase': label, 'started_at_epoch': time.time()})
    print(label, 'starting', flush=True)
    with (OUT / (label + '.log')).open('w') as log:
        child = subprocess.Popen(argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                 start_new_session=True)
        try:
            assert child.wait(timeout=timeout) == 0, label + ' failed; inspect log'
        finally:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGINT)
                try:
                    child.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=5)
    print(label, 'complete', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deadline-epoch', type=float, required=True)
    args = parser.parse_args()
    assert os.geteuid() == 0, 'owned bare-metal host root required'
    OUT.mkdir(exist_ok=False)
    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGINT, interrupt)
    expected = json.loads((ROOT / 'expected-files.json').read_text())
    for name, digest in expected.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    qualification = json.loads((ROOT / 'qualification/summary.json').read_text())
    assert qualification['cpu']['Vendor ID'] == 'AuthenticAMD'
    assert qualification['cpu']['CPU family'] == '26' and qualification['cpu']['Model'] == '2'
    assert qualification['cpu']['Socket(s)'] == '1'
    assert qualification['cpu']['Core(s) per socket'] == '32'
    assert qualification['virtualization'] == 'none'
    assert len(qualification['installed_dimms']) == 12, 'review channel population before measuring'
    assert len(Path('/proc/swaps').read_text().splitlines()) == 1
    pool = Path('/proc/sys/vm/nr_hugepages')
    initial_pool = int(pool.read_text())
    save('initial-pool.json', {'nr_hugepages': initial_pool})
    common = [sys.executable, '-B', str(ROOT / 'bench_cpu_energy.py')]
    measured = ['--binary', str(ROOT / 'seine'), '--kernel', 'avx512-256-stream',
                '--rounds', '1', '--timeout', '240']
    status, failure = 'FAILED', None
    try:
        run('reference-parity', [str(ROOT / 'verify_streaming_dispatch')], 240, args.deadline_epoch)
        run('sensor-smoke', common + ['run', *measured, '--threads', '1', '--page-mode', 'regular',
            '--seconds', '20', '--label', 'stock-one-worker-plumbing', '--output-dir', str(OUT / 'smoke')],
            300, args.deadline_epoch)
        pool.write_text('32768\n')
        assert int(pool.read_text()) == 32768
        sweep = common + ['sweep', *measured, '--page-mode', 'large', '--pairs', '4',
                         '--settle-secs', '10', '--retain-throughput', '.95']
        run('worker-sweep', sweep + ['--threads', '8', '16', '24', '32', '--baseline-threads', '24',
            '--seconds', '60', '--max-seconds', '2400', '--label', 'epyc-9355-stock-power',
            '--output-dir', str(OUT / 'sweep')], 2460, args.deadline_epoch)
        summary = json.loads((OUT / 'sweep/summary.json').read_text())
        peak, shortlist = summary['observed_peak_threads'], summary['efficiency_shortlist_threads']
        save('confirmation-selection.json', {'peak': peak, 'shortlist': shortlist,
             'rule': 'Different lower-joules/hash count retaining 95% of observed peak throughput'})
        if peak != shortlist:
            run('confirmation', sweep + ['--threads', str(peak), str(shortlist),
                '--baseline-threads', str(peak), '--seconds', '120', '--max-seconds', '1400',
                '--label', 'epyc-9355-stock-confirmation', '--output-dir', str(OUT / 'confirmation')],
                1460, args.deadline_epoch)
            status = 'COMPLETE_WITH_CONFIRMATION'
        else:
            status = 'COMPLETE_EXPLORATORY_ONLY'
        for name, digest in expected.items():
            assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    except BaseException as error:
        failure = repr(error)
        raise
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        cleanup, restored, swap_restored = [], False, None
        try:
            pool.write_text(str(initial_pool) + '\n')
            restored = int(pool.read_text()) == initial_pool
            assert restored
        except Exception as error:
            cleanup.append('hugepages: ' + repr(error))
        if (ROOT / 'task-disabled-swap.txt').exists():
            try:
                # This marker records the image's one unused swap file, which
                # was disabled during host preparation, before any measurement.
                original = (ROOT / 'task-disabled-swap.txt').read_text().splitlines()
                assert len(original) == 2 and original[1].split()[0] == '/swap.img'
                subprocess.run(['swapon', '/swap.img'], check=True, timeout=30)
                swap_restored = any(line.split()[0] == '/swap.img'
                                    for line in Path('/proc/swaps').read_text().splitlines()[1:])
                assert swap_restored
            except Exception as error:
                cleanup.append('swap: ' + repr(error))
        save('outcome.json', {'status': status if not cleanup else 'FAILED', 'failure': failure,
             'initial_pool_restored': restored, 'initial_swap_restored': swap_restored,
             'cleanup_failures': cleanup, 'finished_at_epoch': time.time()})
        save('manifest.json', {str(p.relative_to(OUT)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in OUT.rglob('*') if p.is_file() and p.name != 'manifest.json'})
        assert not cleanup, cleanup
    print(status, flush=True)


if __name__ == '__main__':
    main()
