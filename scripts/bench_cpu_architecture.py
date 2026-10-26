#!/usr/bin/env python3
"""Run bounded CPU comparisons on an otherwise idle Linux validation host.

Input directory: bin/seine, bin/seine-old-avx2, bin/verify-current,
bin/verify-old-avx2, and scripts/bench_cpu_ab.sh. Both miner builds must be
identical apart from the old versus paired AVX2 implementation. On AVX-512
hosts this compares two paths in the current binary; on AVX2-only hosts it
compares the old and current AVX2 implementation. Requires sudo for a temporary
HugeTLB pool sized for the requested workers, restored in finally. No cloud provisioning is performed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2) + '\n')


def counters():
    vm = dict(line.split() for line in Path('/proc/vmstat').read_text().splitlines())
    cpu = [int(v) for v in Path('/proc/stat').read_text().splitlines()[0].split()[1:]]
    return {k: int(vm[k]) for k in ('pswpin', 'pswpout', 'oom_kill')} | {
        'cpu_total': sum(cpu[:8]), 'cpu_steal': cpu[7]}


def run(args, log, timeout=180):
    with log.open('w') as handle:
        subprocess.run(args, stdout=handle, stderr=subprocess.STDOUT,
                       check=True, timeout=timeout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--pairs', type=int, default=4)
    parser.add_argument('--seconds', type=int, default=12)
    parser.add_argument('--configs', nargs='+', choices=['regular-t1', 'large-t1', 'large-t4', 'regular-t8', 'large-t8', 'large-t12'],
                        default=['regular-t1', 'large-t1', 'large-t4'])
    args = parser.parse_args()
    root = args.root.resolve()
    out = root / 'results'
    out.mkdir(exist_ok=False)
    assert args.pairs >= 2 and args.seconds >= 10
    assert len(Path('/proc/swaps').read_text().splitlines()) == 1, 'disable swap first'
    flags = Path('/proc/cpuinfo').read_text().split('flags', 1)[1].split('\n', 1)[0].split()
    assert 'avx2' in flags, 'this matrix requires x86 AVX2'
    avx512 = {'avx512f', 'avx512vl'}.issubset(flags)
    comparison = 'avx2-vs-avx512' if avx512 else 'old-vs-paired-avx2'
    write_json(out / 'experiment.json', {'comparison': comparison, 'pairs': args.pairs,
               'seconds': args.seconds, 'rounds': 2, 'warmup_rounds': 1,
               'affinity': 'os', 'autotune': False, 'configs': args.configs})
    binaries = list((root / 'bin').iterdir())
    identities = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in binaries}
    write_json(out / 'binary-sha256.json', identities)
    run(['lscpu', '--json'], out / 'lscpu.json')
    run(['lscpu', '-e=CPU,NODE,SOCKET,CORE,ONLINE'], out / 'topology.txt')
    run(['uname', '-a'], out / 'uname.txt')
    for name in ('cpuinfo', 'meminfo'):
        (out / (name + '.txt')).write_text(Path('/proc', name).read_text())
    for name in ('verify-current', 'verify-old-avx2'):
        run([str(root / 'bin' / name)], out / (name + '.log'), timeout=300)
    print(comparison + ': full-size correctness passed', flush=True)
    huge_pages = max((int(c.rsplit('-t', 1)[1]) for c in args.configs
                      if c.startswith('large-')), default=0) * 1024
    old_pages = int(Path('/proc/sys/vm/nr_hugepages').read_text())
    assert old_pages == 0, 'use a dedicated VM with no pre-existing page pool'
    try:
        for label in args.configs:
            mode, workers_text = label.rsplit('-t', 1)
            workers = int(workers_text)
            if mode == 'large':
                run(['sudo', 'sysctl', '-w', f'vm.nr_hugepages={huge_pages}'], out / 'reserve-pages.log')
                assert int(Path('/proc/sys/vm/nr_hugepages').read_text()) == huge_pages
            label = f'{mode}-t{workers}'
            before = counters()
            start = time.monotonic()
            baseline = 'seine' if avx512 else 'seine-old-avx2'
            cmd = ['bash', str(root / 'scripts/bench_cpu_ab.sh'),
                   '--baseline-dir', str(root), '--candidate-dir', str(root),
                   '--baseline-binary', str(root / 'bin' / baseline),
                   '--candidate-binary', str(root / 'bin/seine'),
                   '--threads', str(workers), '--page-mode', mode, '--bench-kind', 'backend',
                   '--pairs', str(args.pairs), '--bench-secs', str(args.seconds),
                   '--bench-rounds', '2', '--bench-warmup-rounds', '1', '--cooldown-secs', '2',
                   '--baseline-miner-arg', '--bench-cpu-kernel', '--baseline-miner-arg', 'avx2',
                   '--candidate-miner-arg', '--bench-cpu-kernel', '--candidate-miner-arg',
                   'avx512' if avx512 else 'avx2', '--output-dir', str(out / label),
                   '--', '--cpu-affinity', 'os', '--data-dir', str(root / 'config')]
            run(cmd, out / (label + '.log'), timeout=900)
            after = counters()
            delta = {k: after[k] - before[k] for k in before}
            checks = {'elapsed_seconds': time.monotonic() - start, 'delta': delta,
                      'steal_pct': 100 * delta['cpu_steal'] / max(1, delta['cpu_total'])}
            write_json(out / (label + '-checks.json'), checks)
            assert all(delta[k] == 0 for k in ('pswpin', 'pswpout', 'oom_kill')), checks
            assert checks['steal_pct'] < 2, checks
            for report_path in (out / label).glob('*_pair*.json'):
                report = json.loads(report_path.read_text())
                expected = 'avx512' if avx512 and report_path.name.startswith('candidate') else 'avx2'
                assert report['config_fingerprint']['cpu_kernel'] == expected
                assert report['cpu_threads'] == workers
                for sample in report['runs']:
                    for backend in sample['backend_runs']:
                        for key in ('memory_allocation_failures', 'dropped_events',
                                    'assignment_enqueue_timeouts', 'assignment_execution_timeouts',
                                    'control_enqueue_timeouts', 'control_execution_timeouts'):
                            assert backend[key] == 0, (report_path, key)
            print(label + ': ' + (out / label / 'summary.txt').read_text(), flush=True)
    finally:
        run(['sudo', 'sysctl', '-w', f'vm.nr_hugepages={old_pages}'], out / 'release-pages.log')
    assert identities == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in binaries}
    (out / 'COMPLETE').write_text('All architecture checks passed.\n')


if __name__ == '__main__':
    main()
