#!/usr/bin/env python3
"""Fresh paired stock/240 W comparison, after the worker sweep has finished."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import bench_cpu_energy as energy
import run as controller

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'power-results'
CAP = Path('/sys/devices/platform/AMDI0097:00/hwmon/hwmon4/power1_cap')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deadline-epoch', type=float, required=True)
    args = parser.parse_args()
    assert os.geteuid() == 0
    outcome = json.loads((ROOT / 'results/outcome.json').read_text())
    assert outcome['status'].startswith('COMPLETE') and not outcome['cleanup_failures']
    assert (CAP.parent / 'name').read_text().strip() == 'amd_hsmp_hwmon'
    original_cap = int(CAP.read_text())
    assert original_cap == 280_000_000
    assert int((CAP.parent / 'power1_cap_max').read_text()) >= original_cap
    original_pool = int(Path('/proc/sys/vm/nr_hugepages').read_text())
    assert original_pool == 0
    original_swaps = Path('/proc/swaps').read_text().splitlines()
    assert len(original_swaps) == 2 and original_swaps[1].split()[0] == '/swap.img'
    assert int(original_swaps[1].split()[3]) == 0
    expected = json.loads((ROOT / 'expected-files.json').read_text())
    for name, digest in expected.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    count_phase = 'smt-results' if (ROOT / 'smt-results').exists() else 'results'
    count_outcome = json.loads((ROOT / count_phase / 'outcome.json').read_text())
    assert count_outcome['status'].startswith('COMPLETE') and not count_outcome['cleanup_failures']
    summary = json.loads((ROOT / count_phase / 'sweep/summary.json').read_text())
    workers = summary['observed_peak_threads']
    assert workers in (8, 16, 24, 32, 48, 64)
    assert time.time() + 1500 + 120 < args.deadline_epoch
    OUT.mkdir(exist_ok=False)
    controller.OUT = OUT
    signal.signal(signal.SIGTERM, controller.interrupt)
    signal.signal(signal.SIGINT, controller.interrupt)
    controller.save('protocol.json', {'workers': workers, 'caps_uw': {'baseline': original_cap,
        'candidate': 240_000_000}, 'cap_path': str(CAP), 'seconds': 120, 'pairs': 4,
        'settle_seconds': 10, 'baseline_binary_sha256': expected['seine'],
        'controller_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'initial_hugepages': original_pool, 'initial_swaps': original_swaps,
        'selection': 'Peak-throughput count from ' + count_phase + '; all power pairs are fresh',
        'gain_rule': 'All four J/hash pairs improve, upper descriptive 95% delta below zero, and lower throughput delta at least -5%.'})
    status, failure, completed = 'FAILED', None, []
    try:
        subprocess.run(['swapoff', '/swap.img'], check=True, timeout=30)
        Path('/proc/sys/vm/nr_hugepages').write_text(str(workers * 1024) + '\n')
        assert int(Path('/proc/sys/vm/nr_hugepages').read_text()) == workers * 1024
        for pair in range(1, 5):
            for role in (('baseline', 'candidate') if pair % 2 else ('candidate', 'baseline')):
                label = f'pair-{pair:02d}-{role}'
                requested = original_cap if role == 'baseline' else 240_000_000
                CAP.write_text(str(requested) + '\n')
                assert int(CAP.read_text()) == requested
                time.sleep(10)
                before = int(CAP.read_text())
                command = [sys.executable, '-B', str(ROOT / 'bench_cpu_energy.py'), 'run',
                    '--binary', str(ROOT / 'seine'), '--threads', str(workers),
                    '--kernel', 'avx512-256-stream', '--page-mode', 'large', '--seconds', '120',
                    '--rounds', '1', '--timeout', '180', '--label', 'hsmp-' + label,
                    '--output-dir', str(OUT / label)]
                controller.run(label, command, 210, args.deadline_epoch)
                after = int(CAP.read_text())
                controller.save(label + '-cap.json', {'before_uw': before, 'after_uw': after,
                                                       'requested_uw': requested})
                assert before == after == requested
                completed.append(label)
                controller.save('completed.json', completed)
        result = energy.compare([OUT / f'pair-{i:02d}-baseline' for i in range(1, 5)],
                                [OUT / f'pair-{i:02d}-candidate' for i in range(1, 5)])
        controller.save('comparison.json', result)
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
            ('power_cap', lambda: CAP.write_text(str(original_cap) + '\n')),
            ('hugepages', lambda: Path('/proc/sys/vm/nr_hugepages').write_text(str(original_pool) + '\n')),
            ('swap', lambda: subprocess.run(['swapon', '/swap.img'], check=True, timeout=30)
             if len(Path('/proc/swaps').read_text().splitlines()) == 1 else None),
        ):
            try:
                action()
            except Exception as error:
                cleanup.append(label + ': ' + repr(error))
        restored = (int(CAP.read_text()) == original_cap
                    and int(Path('/proc/sys/vm/nr_hugepages').read_text()) == original_pool
                    and any(line.split()[0] == '/swap.img'
                            for line in Path('/proc/swaps').read_text().splitlines()[1:]))
        controller.save('outcome.json', {'status': status if restored and not cleanup else 'FAILED',
            'failure': failure, 'completed': completed, 'settings_restored': restored,
            'cleanup_failures': cleanup, 'finished_at_epoch': time.time()})
        controller.save('manifest.json', {str(p.relative_to(OUT)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in OUT.rglob('*') if p.is_file() and p.name != 'manifest.json'})
        assert restored and not cleanup, cleanup
    print(status, flush=True)


if __name__ == '__main__':
    main()
