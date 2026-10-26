#!/usr/bin/env python3
"""Fresh AVX-512 2x2 layout ablation after the main controller has stopped.

Keep build-alignment effects separate from the architecture/enum changes.
Four passes rotate/reverse all four frozen executables on the same owned host.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import shutil
import statistics
import subprocess
import time

from bench import run_case

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'results'


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def interrupt(signum, frame):
    raise InterruptedError(signum)


def main():
    os.chdir(ROOT)
    OUT.mkdir(exist_ok=False)
    (OUT/'protocol-source').mkdir()
    for name in ['bench.py', 'run_alignment.py', 'after_main.py']:
        shutil.copy2(ROOT/name, OUT/'protocol-source'/name)
    signal.signal(signal.SIGINT, interrupt)
    signal.signal(signal.SIGTERM, interrupt)
    expected = json.loads((ROOT / 'expected-binaries.json').read_text())
    assert len(expected) == 4 and len(set(expected.values())) == 4
    for name, digest in expected.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
    assert json.loads((ROOT.parent / 'results/outcome.json').read_text())['status'] == 'COMPLETE'
    state = subprocess.check_output(['systemctl', 'show', 'seine-followups-controller', '--property=ActiveState', '--value'], text=True).strip()
    assert state not in ['active', 'activating', 'deactivating'], state
    pool = Path('/proc/sys/vm/nr_hugepages')
    assert int(pool.read_text()) == 0
    started = time.monotonic()
    status = 'FAILED'
    values = []
    cases = ['baseline21', 'arm-ungated', 'baseline21-aligned', 'arm-aligned']
    orders = [cases, cases[::-1], cases[2:]+cases[:2], (cases[2:]+cases[:2])[::-1]]
    save(OUT / 'protocol.json', {'expected': expected, 'orders': orders, 'workers': 12,
        'kernel': 'avx512', 'seconds': 15, 'rounds': 1, 'warmup': 1,
        'aligned_rustflags': '-C llvm-args=-align-all-functions=6',
        'scope': 'Fresh same-host original/aligned 2x2; layout ablation does not prove unique root cause.'})
    try:
        subprocess.run(['sudo', 'sysctl', '-w', 'vm.nr_hugepages=12288'], check=True)
        assert int(pool.read_text()) == 12288
        for index, order in enumerate(orders):
            row = {}
            for name in order:
                assert time.monotonic() - started < 840, 'bounded alignment deadline'
                row[name] = run_case(ROOT, OUT, f'{index}-{name}', {'binary': name, 'kernel': 'avx512'}, 12, 15, 1, 1)
            values.append(row)
            save(OUT / 'passes.json', values)
        summary = {}
        for label, baseline, candidate in [('original', 'baseline21', 'arm-ungated'), ('aligned', 'baseline21-aligned', 'arm-aligned')]:
            ratios = [row[candidate]['completed_hps'] / row[baseline]['completed_hps'] for row in values]
            summary[label] = {'paired_deltas_pct': [100*(x-1) for x in ratios],
                'geometric_delta_pct': 100*(math.exp(statistics.mean(map(math.log, ratios)))-1)}
        for name, digest in expected.items():
            assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
        save(OUT / 'summary.json', summary)
        status = 'COMPLETE'
    finally:
        subprocess.run(['sudo', 'sysctl', '-w', 'vm.nr_hugepages=0'], check=True, timeout=30)
        assert int(pool.read_text()) == 0
        save(OUT / 'outcome.json', {'status': status, 'elapsed_secs': time.monotonic()-started})
        save(ROOT / 'result-manifest.json', {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.rglob('*') if p.is_file()})
        subprocess.run(['tar', '-czf', 'results.tar.gz', 'results', 'result-manifest.json', 'expected-binaries.json'], check=True, timeout=60)
    print(status, flush=True)


if __name__ == '__main__':
    main()
