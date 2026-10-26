#!/usr/bin/env python3
"""Fresh 32/48/64-worker stock-power sweep after physical-core screening."""
import argparse
import hashlib
import json
from pathlib import Path
import signal
import subprocess
import sys
import time

import run as controller

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'smt-results'
POOL = Path('/proc/sys/vm/nr_hugepages')
CAP = Path('/sys/devices/platform/AMDI0097:00/hwmon/hwmon4/power1_cap')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deadline-epoch', type=float, required=True)
    args = parser.parse_args()
    prior = json.loads((ROOT / 'results/outcome.json').read_text())
    assert prior['status'].startswith('COMPLETE') and not prior['cleanup_failures']
    assert int(POOL.read_text()) == 0 and int(CAP.read_text()) == 280_000_000
    original_swaps = Path('/proc/swaps').read_text().splitlines()
    assert len(original_swaps) == 2 and original_swaps[1].split()[0] == '/swap.img'
    assert int(original_swaps[1].split()[3]) == 0
    assert time.time() + 1860 + 120 < args.deadline_epoch
    expected = json.loads((ROOT / 'expected-files.json').read_text())
    for name, digest in expected.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    OUT.mkdir(exist_ok=False)
    controller.OUT = OUT
    signal.signal(signal.SIGTERM, controller.interrupt)
    signal.signal(signal.SIGINT, controller.interrupt)
    controller.save('protocol.json', {'workers': [32, 48, 64], 'baseline_threads': 32,
        'seconds': 60, 'pairs': 4, 'stock_cap_uw': int(CAP.read_text()),
        'controller_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'binary_sha256': expected['seine'], 'initial_swaps': original_swaps,
        'scope': 'SMT exploration after physical-core sweep; separate paired controls'})
    status, failure = 'FAILED', None
    try:
        subprocess.run(['swapoff', '/swap.img'], check=True, timeout=30)
        POOL.write_text('65536\n')
        assert int(POOL.read_text()) == 65536
        command = [sys.executable, '-B', str(ROOT / 'bench_cpu_energy.py'), 'sweep',
            '--binary', str(ROOT / 'seine'), '--kernel', 'avx512-256-stream',
            '--threads', '32', '48', '64', '--baseline-threads', '32', '--page-mode', 'large',
            '--seconds', '60', '--rounds', '1', '--pairs', '4', '--settle-secs', '10',
            '--timeout', '240', '--max-seconds', '1800', '--retain-throughput', '.95',
            '--label', 'epyc-9355p-smt-stock', '--output-dir', str(OUT / 'sweep')]
        controller.run('smt-sweep', command, 1860, args.deadline_epoch)
        assert int(CAP.read_text()) == 280_000_000
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
        controller.save('outcome.json', {'status': status if restored and not cleanup else 'FAILED',
            'failure': failure, 'settings_restored': restored, 'cleanup_failures': cleanup,
            'finished_at_epoch': time.time()})
        controller.save('manifest.json', {str(p.relative_to(OUT)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in OUT.rglob('*') if p.is_file() and p.name != 'manifest.json'})
        assert restored and not cleanup, cleanup
    print(status, flush=True)


if __name__ == '__main__':
    main()
