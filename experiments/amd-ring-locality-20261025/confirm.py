#!/usr/bin/env python3
"""Fresh confirmation of the predeclared shortlist, then conditional energy pairs."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import run_native as controller

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'confirmation-results'
POOL, CAP = controller.POOL, controller.CAP
save, digest = controller.save, controller.digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deadline-epoch', type=float)
    parser.add_argument('--paired', action='store_true')
    parser.add_argument('--ring', type=int, choices=(16, 32))
    parser.add_argument('--workers', type=int, choices=(32, 64))
    args = parser.parse_args()
    if args.paired:
        from bench import paired
        return paired(ROOT, OUT / 'throughput',
            {'binary': 'ring-64', 'kernel': controller.KERNEL},
            {'binary': 'ring-' + str(args.ring), 'kernel': controller.KERNEL},
            args.workers, pairs=4, seconds=30, rounds=2, warmup=1)
    assert args.deadline_epoch and time.time() + 2700 < args.deadline_epoch
    assert os.geteuid() == 0
    os.chdir(ROOT)
    prior = json.loads((ROOT / 'results/outcome.json').read_text())
    assert prior['status'] == 'COMPLETE' and prior['settings_restored'] and not prior['cleanup_failures']
    manifest = json.loads((ROOT / 'results/manifest.json').read_text())
    for name, sha in manifest.items():
        assert digest(ROOT / 'results' / name) == sha, name
    selected = json.loads((ROOT / 'results/screen-selection.json').read_text())['shortlist']
    assert selected is not None, 'no positive screen; preserve the negative result'
    workers, ring = selected['workers'], selected['ring']
    assert workers in (32, 64) and ring in (16, 32)
    assert int(POOL.read_text()) == 0 and int(CAP.read_text()) == 280_000_000
    swaps = Path('/proc/swaps').read_text().splitlines()
    assert len(swaps) == 2 and swaps[1].split()[0] == '/swap.img'
    assert int(swaps[1].split()[3]) == 0
    expected = json.loads((ROOT / 'expected-files.json').read_text())
    for name, sha in expected.items():
        assert digest(ROOT / name) == sha, name
    binaries = {'baseline': expected['ring-64'], 'candidate': expected['ring-' + str(ring)]}
    OUT.mkdir(exist_ok=False)
    controller.OUT = OUT
    signal.signal(signal.SIGTERM, controller.interrupted)
    signal.signal(signal.SIGINT, controller.interrupted)
    save(OUT / 'protocol.json', {'workers': workers, 'ring': ring, 'shortlist': selected,
        'binary_sha256': binaries, 'expected_files': expected,
        'screen_manifest_sha256': digest(ROOT / 'results/manifest.json'),
        'initial_swaps': swaps, 'stock_cap_uw': 280_000_000,
        'deadline_epoch': args.deadline_epoch,
        'throughput_gate': 'Fresh four-pair lower descriptive 95% delta strictly above +1%',
        'energy': 'Four fresh alternating 120-second pairs only after throughput gate; same stock cap/count/pages.'})
    status, failure = 'FAILED', None
    try:
        subprocess.run(['swapoff', '/swap.img'], check=True, timeout=30)
        POOL.write_text(str(workers * 1024) + '\n')
        assert int(POOL.read_text()) == workers * 1024
        controller.run('throughput-confirmation', [sys.executable, '-B', str(Path(__file__).resolve()),
            '--paired', '--ring', str(ring), '--workers', str(workers)], 1020, args.deadline_epoch)
        throughput = json.loads((OUT / 'throughput/summary.json').read_text())
        passed = throughput['paired_resampling_interval_pct'][0] > 1
        save(OUT / 'throughput-gate.json', {'passed': passed, 'summary': throughput,
            'shipping_change_accepted': False})
        if passed:
            for pair in range(1, 5):
                for role in (('baseline', 'candidate') if pair % 2 else ('candidate', 'baseline')):
                    label = f'pair-{pair:02d}-{role}'
                    binary = 'ring-64' if role == 'baseline' else 'ring-' + str(ring)
                    before = int(CAP.read_text())
                    assert before == 280_000_000
                    command = [sys.executable, '-B', str(ROOT / 'bench_cpu_energy.py'), 'run',
                        '--binary', str(ROOT / binary), '--threads', str(workers),
                        '--kernel', controller.KERNEL, '--page-mode', 'large', '--seconds', '120',
                        '--rounds', '1', '--timeout', '180', '--label', label,
                        '--output-dir', str(OUT / label)]
                    controller.run(label, command, 210, args.deadline_epoch)
                    after = int(CAP.read_text())
                    save(OUT / (label + '-cap.json'), {'before_uw': before,
                        'after_uw': after, 'requested_uw': 280_000_000})
                    assert after == before
            from compare_energy import compare
            save(OUT / 'energy-comparison.json', compare(OUT, binaries, workers))
            status = 'COMPLETE_WITH_ENERGY'
        else:
            status = 'COMPLETE_THROUGHPUT_REJECTED'
        for name, sha in expected.items():
            assert digest(ROOT / name) == sha, name
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
