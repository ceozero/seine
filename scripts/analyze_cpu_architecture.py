#!/usr/bin/env python3
"""Summarize a collected architecture matrix; accepts completed cells only."""
import argparse
import csv
import hashlib
import itertools
import json
from pathlib import Path
import statistics


def quantile(values, p):
    values = sorted(values)
    rank = (len(values) - 1) * p
    low = int(rank)
    high = min(low + 1, len(values) - 1)
    return values[low] + (values[high] - values[low]) * (rank - low)


def summarize_trial(path, experiment):
    with (path / 'results.tsv').open() as handle:
        rows = list(csv.DictReader(handle, delimiter='\t'))
    assert len(rows) == 2 * experiment['pairs'], path
    pairs, reports = {}, []
    for row in rows:
        report = json.loads((path / Path(row['report']).name).read_text())
        assert report['rounds'] == experiment['rounds']
        assert len(report['runs']) == experiment['rounds']
        assert report['warmup_rounds'] == experiment['warmup_rounds']
        assert report['bench_secs'] == experiment['seconds']
        assert report['environment']['build_rustflags'] == ''
        assert report['schema_version'] == 14
        assert report['cpu_threads'] == int(path.name.rsplit('-t', 1)[1])
        assert report['config_fingerprint']['cpu_page_mode'] == path.name.rsplit('-t', 1)[0]
        assert report['config_fingerprint']['cpu_autotune_threads'] is False
        assert report['config_fingerprint']['cpu_affinity'] == 'os'
        expected = 'avx512' if experiment['comparison'] == 'avx2-vs-avx512' and row['variant'] == 'candidate' else 'avx2'
        assert report['config_fingerprint']['cpu_kernel'] == expected
        assert report['config_fingerprint']['cpu_kernel_requested'] == expected
        for sample in report['runs']:
            assert sample['actual_elapsed_secs'] > 0
            for backend in sample['backend_runs']:
                for key in ('dropped_events', 'assignment_enqueue_timeouts',
                            'assignment_execution_timeouts', 'control_enqueue_timeouts',
                            'control_execution_timeouts', 'memory_allocation_failures'):
                    assert backend[key] == 0, (path, row, key)
                key = 'memory_explicit_large' if report['config_fingerprint']['cpu_page_mode'] == 'large' else 'memory_regular'
                assert backend[key + '_workers'] == report['cpu_threads']
                assert backend[key + '_bytes'] == report['cpu_threads'] * 2 * 1024**3
        completed_hps = sum(x['hashes'] for x in report['runs']) / sum(x['actual_elapsed_secs'] for x in report['runs'])
        config = dict(report['config_fingerprint'])
        for key in ('cpu_kernel', 'cpu_kernel_requested'):
            config.pop(key)
        # This RAM-derived suggestion is unused with fixed workers and autotune off.
        # Actual worker counts and arena bytes are checked above.
        config.pop('cpu_auto_threads_cap', None)
        pair = pairs.setdefault(int(row['pair']), {})
        pair[row['variant']] = {'counted_hps': report['avg_hps'], 'completed_hps': completed_hps,
                                'config': config, 'pow': report['pow_fingerprint'],
                                'identity': report['environment']['cpu_identity'],
                                'source': report['environment']['source_fingerprint']}
        reports.append(report)
    assert set(pairs) == set(range(1, experiment['pairs'] + 1))
    for pair in pairs.values():
        assert set(pair) == {'baseline', 'candidate'}
        for key in ('config', 'pow', 'identity'):
            assert pair['baseline'][key] == pair['candidate'][key], (path, key)
        if experiment['comparison'] == 'avx2-vs-avx512':
            assert pair['baseline']['source'] == pair['candidate']['source']
        else:
            assert pair['baseline']['source'] != pair['candidate']['source']
    metrics = {}
    for metric in ('counted_hps', 'completed_hps'):
        baseline = [pairs[i]['baseline'][metric] for i in sorted(pairs)]
        candidate = [pairs[i]['candidate'][metric] for i in sorted(pairs)]
        deltas = [(c / b - 1) * 100 for b, c in zip(baseline, candidate)]
        boot = [statistics.mean(sample) for sample in itertools.product(deltas, repeat=len(deltas))]
        metrics[metric] = {'baseline_mean': statistics.mean(baseline),
                           'candidate_mean': statistics.mean(candidate),
                           'ratio_of_means_delta_pct': (statistics.mean(candidate) / statistics.mean(baseline) - 1) * 100,
                           'paired_deltas_pct': deltas,
                           'paired_bootstrap_95_pct': [quantile(boot, .025), quantile(boot, .975)]}
    checks = json.loads((path.parent / (path.name + '-checks.json')).read_text())
    assert all(checks['delta'][key] == 0 for key in ('pswpin', 'pswpout', 'oom_kill'))
    assert checks['steal_pct'] < 2
    return {'trial': path.name, 'threads': reports[0]['cpu_threads'],
            'page_mode': reports[0]['config_fingerprint']['cpu_page_mode'],
            'cpu_brand': reports[0]['environment']['cpu_brand'],
            'cpu_identity': reports[0]['environment']['cpu_identity'],
            'metrics': metrics, 'checks': checks,
            'max_fence_secs': max(run['fence_secs'] for r in reports for run in r['runs'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    root = args.directory
    expected = {Path(k).name: v for k, v in json.loads((root / 'sources.json').read_text())['sha256'].items() if k.startswith('bin/')}
    summaries = []
    for cell in sorted(p for p in root.iterdir() if p.is_dir() and (p / 'state.json').exists()):
        if not (cell / 'results/COMPLETE').exists():
            continue
        state = json.loads((cell / 'state.json').read_text())
        if not state.get('results_verified'):
            continue  # A concurrent collection may have copied COMPLETE first.
        for line in (cell / 'RESULTS-SHA256SUMS').read_text().splitlines():
            digest, name = line.split('  ', 1)
            assert hashlib.sha256((cell / name).read_bytes()).hexdigest() == digest, (cell, name)
        experiment = json.loads((cell / 'results/experiment.json').read_text())
        observed = json.loads((cell / 'results/binary-sha256.json').read_text())
        assert expected == observed, cell
        trials = [summarize_trial(cell / 'results' / label, experiment)
                  for label in experiment.get('configs', ['regular-t1', 'large-t1', 'large-t4'])]
        summaries.append({'instance_type': cell.name, 'comparison': experiment['comparison'],
                          'trials': trials})
        for trial in trials:
            m = trial['metrics']['completed_hps']
            print(f"{cell.name} {trial['cpu_brand']} {trial['trial']}: "
                  f"{m['baseline_mean']:.4f} -> {m['candidate_mean']:.4f} H/s "
                  f"({m['ratio_of_means_delta_pct']:+.2f}%), paired 95% "
                  f"{m['paired_bootstrap_95_pct'][0]:+.2f}..{m['paired_bootstrap_95_pct'][1]:+.2f}%")
    (root / 'comparison.json').write_text(json.dumps(summaries, indent=2) + '\n')
    print(f'{len(summaries)} completed architecture cells')


if __name__ == '__main__':
    main()
