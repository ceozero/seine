#!/usr/bin/env python3
"""Recompute native rates from verified raw artifacts; never infer promotion."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import statistics


def read(path):
    return json.loads(path.read_text())


def delta(values):
    return 100 * (math.exp(statistics.mean(math.log(x) for x in values)) - 1)


def analyze(root):
    manifest = read(root / 'result-manifest.json')
    for name, digest in manifest.items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
    out = root / 'results'
    assert read(out / 'outcome.json')['status'] == 'COMPLETE'
    result = {'verified_files': len(manifest), 'hardware': read(out / 'hardware.json'),
              'fixed': {}, 'memory': {}, 'productive': {}}
    for protocol_path in sorted(out.glob('*/protocol.json')):
        folder = protocol_path.parent
        assert (folder / 'COMPLETE').exists()
        protocol = read(protocol_path)
        rows = []
        for pair in range(1, protocol['pairs'] + 1):
            row = {}
            for side in ['baseline', 'candidate']:
                report = read(folder / f'{pair}-{side}.json')
                checks = read(folder / f'{pair}-{side}-checks.json')
                assert all(checks['delta'][k] == 0 for k in ['pswpin', 'pswpout', 'oom_kill'])
                assert checks['steal_pct'] < 2 and checks['steal_single_cpu_upper_pct'] < 2
                row[side] = sum(r['hashes'] for r in report['runs']) / sum(r['elapsed_secs'] for r in report['runs'])
                assert math.isclose(row[side], read(folder / 'pairs.json')[pair-1][side]['completed_hps'])
            rows.append(row)
        ratios = [r['candidate'] / r['baseline'] for r in rows]
        result['fixed'][folder.name] = {'protocol': protocol, 'raw_recomputed_hps': rows,
            'paired_deltas_pct': [100*(r-1) for r in ratios], 'geometric_delta_pct': delta(ratios)}
    # The takeover EPYC controller (run_joint_epyc.py) has no memory phase.
    memory = read(out / 'memory-results.json') if (out / 'memory-results.json').exists() else []
    grouped = {}
    for entry in memory:
        wide = 'workers' in entry
        label = ('memory-wide' if wide else 'memory') + f"-r{entry['repeat']}-t{entry['threshold']}"
        rows = [json.loads(line) for line in (out / (label + '.log')).read_text().splitlines()]
        summary = rows[-1]
        assert summary == entry['result']
        assert len(rows) == summary['workers'] + 1
        assert summary['hashes'] == sum(r['hashes'] for r in rows[:-1])
        assert math.isclose(summary['elapsed_secs'], max(r['elapsed_secs'] for r in rows[:-1]))
        assert math.isclose(summary['hps'], summary['hashes']/summary['elapsed_secs'])
        rss = re.search(r'Maximum resident set size \(kbytes\):\s*(\d+)', (out / (label + '-time.txt')).read_text())
        assert rss
        checks = read(out / (label + '-checks.json'))
        assert all(checks[k] == 0 for k in ['pswpin', 'pswpout', 'oom_kill'])
        key = ('wide-' if wide else 'single-') + str(entry['threshold'])
        grouped.setdefault(key, []).append({'repeat': entry['repeat'], 'hps': summary['hps'],
            'max_rss_kib': int(rss[1]), 'summary': summary, 'workers': rows[:-1]})
    for key, rows in grouped.items():
        reference = grouped[key.split('-')[0] + '-0']
        ratios = [r['hps'] / next(b['hps'] for b in reference if b['repeat'] == r['repeat']) for r in rows]
        result['memory'][key] = {'samples': rows, 'mean_hps': statistics.mean(r['hps'] for r in rows),
            'mean_max_rss_kib': statistics.mean(r['max_rss_kib'] for r in rows),
            'paired_deltas_pct': [100*(r-1) for r in ratios], 'geometric_delta_pct': delta(ratios)}
    for folder in sorted(out.glob('joint-*')):
        if not (folder / 'productive-window.json').exists():
            continue
        assert (folder / 'COMPLETE').exists()
        assert read(folder / 'cleanup.json') == {'failures': [], 'primary_failure': None}
        text = (folder / 'miner.log').read_text()
        counts = [int(v) for v in re.findall(r'\bhashes=(\d+)', text)]
        assert counts and counts == sorted(counts), folder.name
        window = read(folder / 'productive-window.json')
        assert max(counts) == window['completed_hashes_lower_bound']
        assert math.isclose(window['completed_hps_lower_bound'], max(counts) / window['elapsed_start_request_through_stopped_seconds'])
        assert 'quarantined' not in text.lower()
        caches = {p.name: read(p) for p in folder.glob('tuning.json*') if p.is_file()}
        start = re.search(r'starting with (\d+) threads \(([^)]+)\)', text)
        assert start
        identity = read(folder / 'identity.json')
        result['productive'][folder.name] = {'window': window, 'caches': caches,
            'cache_mode': 'warm' if identity['cache_source'] else 'cold',
            'scope_note': 'Classify by cache_source and startup log; the early Intel harness used a cold-cache scope string for both modes.',
            'starting_threads': int(start[1]), 'starting_reason': start[2],
            'trajectory': [line for line in text.splitlines() if ('autotune' in line.lower() or 'cpu-kernel' in line.lower())],
            'identity': identity}
    assert len(result['productive']) == 8
    for name, run in result['productive'].items():
        if name.startswith('joint-warm-'):
            cold = result['productive'][name.replace('joint-warm-', 'joint-', 1)]
            expected_count = cold['caches'].get('tuning.json', {}).get('selected_threads')
            run['cold_selected_threads'] = expected_count
            run['count_cache_restored'] = (expected_count is not None and
                run['starting_threads'] == expected_count and run['starting_reason'] == 'cached starting point')
            run['kernel_cache_restore_messages'] = [line for line in run['trajectory'] if 'restoring confirmed' in line]
    for kind, prefix in [('cold', 'joint-'), ('warm', 'joint-warm-')]:
        ratios = [result['productive'][prefix+'candidate-'+suffix]['window']['completed_hps_lower_bound'] /
                  result['productive'][prefix+'control-'+suffix]['window']['completed_hps_lower_bound'] for suffix in ['a', 'b']]
        result[kind] = {'paired_deltas_pct': [100*(r-1) for r in ratios], 'geometric_delta_pct': delta(ratios),
            'scope': 'Two paired finite productive windows on one host; final unlogged hashes omitted. Includes startup and shutdown, with natural tuning interruptions.'}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('collected', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = analyze(args.collected)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ['verified_files', 'cold', 'warm']}, indent=2))


if __name__ == '__main__':
    main()
