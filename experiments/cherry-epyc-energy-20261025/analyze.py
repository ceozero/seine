#!/usr/bin/env python3
"""Recompute package-energy results from hashed evidence and export a public summary."""
import argparse
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import statistics
import sys
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import bench_cpu_energy as energy


def read(path):
    return json.loads(path.read_text())


def verify(folder):
    manifest = read(folder / 'manifest.json')
    for name, digest in manifest.items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == digest, name
    return len(manifest)


def analyze(root):
    qualification = read(root / 'qualification/summary.json')
    kernel = read(root / 'qualification/kernel.json')
    assert kernel['exit_code'] == 0 and kernel['stdout'].split()[0] == 'Linux'
    result = {'scope': 'Whole-invocation CPU package energy; excludes separately unmeasured DRAM and wall losses',
        'hardware': qualification, 'binary_sha256': read(root / 'expected-files.json')['seine'],
        'source_revision': (root / 'source-revision.txt').read_text().strip(),
        'os': 'Linux', 'os_kernel_release': kernel['stdout'].split()[2], 'phases': {}}
    parity = (root / 'results/reference-parity.log').read_text().splitlines()
    assert len([line for line in parity if line.startswith('PASS nonce=')]) == 21
    for name in ('results', 'smt-results'):
        folder = root / name
        if not folder.exists():
            continue
        files = verify(folder)
        outcome = read(folder / 'outcome.json')
        assert outcome['status'].startswith('COMPLETE') and not outcome['cleanup_failures'], outcome
        sweep = folder / 'sweep'
        manifest = read(sweep / 'sweep.json')
        assert manifest['status'] == 'complete' and len(manifest['completed']) == len(manifest['plan'])
        summary = energy.summarize_sweep(sweep, manifest['plan'], .95)
        records = []
        for leg in manifest['plan']:
            record, report = energy.load_measurement(sweep / leg['directory'])
            assert record['binary_sha256'] == result['binary_sha256']
            records.append({**leg, 'hashes': record['completed_hashes'],
                'seconds': record['invocation_secs'], 'package_joules': record['total_package_joules'],
                'raw_energy_sha256': hashlib.sha256((sweep / leg['directory'] / 'energy.json').read_bytes()).hexdigest(),
                'benchmark_sha256': record['benchmark_sha256']})
        result['phases'][name] = {'verified_files': files, 'outcome': outcome,
            'points': summary['points'], 'observed_peak_threads': summary['observed_peak_threads'],
            'efficiency_shortlist_threads': summary['efficiency_shortlist_threads'], 'observations': records,
            'paired_metrics': {key: value['metrics'] for key, value in summary['comparisons_to_baseline'].items()}}
    folder = root / 'power-results'
    if folder.exists():
        files = verify(folder)
        outcome = read(folder / 'outcome.json')
        assert outcome['status'] == 'COMPLETE' and outcome['settings_restored'] and not outcome['cleanup_failures']
        protocol = read(folder / 'protocol.json')
        for pair in range(1, 5):
            for role in ('baseline', 'candidate'):
                cap = read(folder / f'pair-{pair:02d}-{role}-cap.json')
                assert cap['before_uw'] == cap['after_uw'] == cap['requested_uw'] == protocol['caps_uw'][role]
        records = []
        for pair in range(1, 5):
            for role in ('baseline', 'candidate'):
                directory = f'pair-{pair:02d}-{role}'
                record, _ = energy.load_measurement(folder / directory)
                assert record['binary_sha256'] == result['binary_sha256']
                records.append({'pair': pair, 'role': role, 'directory': directory,
                    'threads': protocol['workers'], 'hashes': record['completed_hashes'],
                    'seconds': record['invocation_secs'], 'package_joules': record['total_package_joules'],
                    'raw_energy_sha256': hashlib.sha256((folder / directory / 'energy.json').read_bytes()).hexdigest(),
                    'benchmark_sha256': record['benchmark_sha256']})
        comparison = energy.compare([folder / f'pair-{i:02d}-baseline' for i in range(1, 5)],
                                    [folder / f'pair-{i:02d}-candidate' for i in range(1, 5)])
        metrics = comparison['metrics']
        joules = metrics['invocation_joules_per_completed_hash']['comparison']
        rate = metrics['invocation_completed_hashes_per_second']['comparison']
        accepted = (joules['sign_consistency']['candidate_lower_pairs'] == 4
                    and joules['paired_geometric_delta_ci95_pct'][1] < 0
                    and rate['paired_geometric_delta_ci95_pct'][0] >= -5)
        result['power'] = {'verified_files': files, 'protocol': protocol, 'outcome': outcome,
                           'metrics': metrics, 'observations': records,
                           'predeclared_gain_gate_passed': accepted}
    return result


def export_records(result, destination):
    """Flat graph inputs plus exact per-invocation numerators and denominators."""
    hardware = result['hardware']
    cpu = hardware['cpu']
    dimms = hardware['installed_dimms']
    assert len(dimms) == 12 and len({d['Bank Locator'] for d in dimms}) == 12
    assert all(d['Size'] == '16 GB' and d['Configured Memory Speed'] == '4800 MT/s' for d in dimms)
    common = {'campaign': 'cherry-epyc-energy-20261025',
        'hardware': cpu['Model name'], 'category': 'amd', 'backend': 'cpu',
        'os': result['os'], 'os_kernel_release': result['os_kernel_release'],
        'cpu_vendor': cpu['Vendor ID'], 'cpu_family': int(cpu['CPU family']),
        'cpu_model': int(cpu['Model']), 'sockets': int(cpu['Socket(s)']),
        'physical_cores': int(cpu['Core(s) per socket']) * int(cpu['Socket(s)']),
        'hardware_threads_per_core': int(cpu['Thread(s) per core']),
        'numa_nodes': int(cpu['NUMA node(s)']), 'virtualization': hardware['virtualization'],
        'installed_memory_gib': 192, 'memory_channels_populated': 12,
        'memory_type': 'DDR5', 'memory_speed_mts': 4800,
        'kernel': 'avx512-256-stream', 'affinity': 'auto', 'page_mode': 'large',
        'hugepage_size_kib': 2048, 'selection': 'manual_fixed_configuration',
        'measured_rounds_per_invocation': 1, 'warmup_rounds': 0,
        'measurement_timezone': 'America/New_York',
        'workload': 'legacy_argon2id_2gib', 'benchmark_kind': 'end-to-end',
        'metric_scope': 'whole_invocation', 'power_scope': 'cpu_package',
        'aggregation': 'ratio_of_totals', 'source_revision': result['source_revision'],
        'binary_sha256': result['binary_sha256'], 'reference_parity_transitions': 21,
        'source': 'experiments/cherry-epyc-energy-20261025/results.json'}
    records = []

    def add(phase, label, workers, cap_w, observations, outcome):
        hashes = sum(s['hashes'] for s in observations)
        seconds = sum(s['seconds'] for s in observations)
        joules = sum(s['package_joules'] for s in observations)
        rates = [s['hashes'] / s['seconds'] for s in observations]
        assert hashes > 0 and seconds > 0 and joules > 0 and len(rates) >= 4
        records.append({**common, 'id': f'cherry-9355p-{phase}-{label}',
            'phase': phase, 'workers': workers, 'power_cap_w': cap_w,
            'requested_benchmark_seconds': 120 if phase == 'power-results' else 60,
            'phase_finished_at_local': datetime.fromtimestamp(outcome['finished_at_epoch'],
                ZoneInfo('America/New_York')).isoformat(),
            'phase_finished_at_label': datetime.fromtimestamp(outcome['finished_at_epoch'],
                ZoneInfo('America/New_York')).strftime('%Y-%m-%d %H:%M:%S %Z'),
            'repetitions': len(observations), 'completed_hashes': hashes,
            'invocation_seconds': seconds, 'package_joules': joules,
            'hps': hashes / seconds, 'package_watts': joules / seconds,
            'package_joules_per_hash': joules / hashes, 'hashes_per_package_joule': hashes / joules,
            'hps_sample_cv': statistics.stdev(rates) / statistics.mean(rates),
            'observations': observations})

    for phase, data in result['phases'].items():
        for point in data['points']:
            observations = [s for s in data['observations'] if s['threads'] == point['threads']]
            add(phase, str(point['threads']), point['threads'], 280, observations, data['outcome'])
            assert abs(records[-1]['hps'] - point['completed_hps']) < 1e-9
    if 'power' in result:
        data = result['power']
        for role in ('baseline', 'candidate'):
            add('power-results', role, data['protocol']['workers'],
                data['protocol']['caps_uw'][role] / 1e6,
                [s for s in data['observations'] if s['role'] == role], data['outcome'])
    document = {'schema': 'seine-hardware-benchmark-records/v1',
        'description': 'Reusable measured graph/table inputs; exact settings and metric scope travel with every record.',
        'includes': ['startup', 'allocation', 'reported_work', 'fences', 'teardown'],
        'power_excludes': ['separately_unmeasured_DRAM', 'wall_plug_losses'],
        'comparison_rule': 'Compare only compatible metric scopes. Separate phases have separate controls; do not merge repeated worker counts across phases.',
        'records': records}
    (destination / 'benchmark-records.json').write_text(json.dumps(document, indent=2) + '\n')
    with (destination / 'benchmark-records.csv').open('w', newline='') as file:
        fields = [k for k in records[0] if k != 'observations']
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(records)


def plot(result, destination):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(12, 4), layout='constrained')
    panels = [('completed_hps', 'Completed hashes / second'),
              ('package_watts', 'Measured CPU package watts'),
              ('joules_per_hash', 'Package joules / hash (lower is better)')]
    for name, phase in result['phases'].items():
        points = phase['points']
        for ax, (metric, title) in zip(axes, panels):
            ax.plot([p['threads'] for p in points], [p[metric] for p in points], 'o-',
                    label='Physical-core sweep' if name == 'results' else 'SMT sweep')
            ax.set(xlabel='Workers (2 GiB each)', title=title)
            ax.grid(alpha=.2)
    axes[0].legend(fontsize=8)
    fig.suptitle('EPYC 9355P · 12 × DDR5-4800 · streaming kernel · stock 280 W cap\n'
                 'Whole-invocation measurements; package energy is not wall-plug energy', fontsize=11)
    fig.savefig(destination / 'efficiency.png', dpi=180)
    fig.savefig(destination / 'efficiency.svg')
    plt.close(fig)
    if 'power' in result:
        metrics = result['power']['metrics']
        fig, axes = plt.subplots(1, 3, figsize=(11, 4), layout='constrained')
        panels = [('invocation_completed_hashes_per_second', 'Completed hashes / second'),
                  ('average_package_watts', 'Measured CPU package watts'),
                  ('invocation_joules_per_completed_hash', 'Package joules / hash')]
        for ax, (metric, title) in zip(axes, panels):
            values = [metrics[metric][role]['arithmetic_mean'] for role in ('baseline', 'candidate')]
            bars = ax.bar(['Stock 280 W cap', '240 W cap'], values, color=['#377eb8', '#ff7f00'])
            ax.bar_label(bars, fmt='%.2f', padding=4)
            ax.set(title=title, ylim=(0, max(values) * 1.15))
            ax.grid(axis='y', alpha=.2)
            ax.set_axisbelow(True)
        fig.suptitle('EPYC 9355P · 64 workers · streaming kernel · 12 × DDR5-4800\n'
            'Four alternating pairs, 120-second windows · whole-invocation CPU package energy', fontsize=11)
        fig.savefig(destination / 'power-cap.png', dpi=180)
        fig.savefig(destination / 'power-cap.svg')
        plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('collected', type=Path)
    parser.add_argument('output_dir', type=Path)
    parser.add_argument('--plot', action='store_true')
    args = parser.parse_args()
    report = analyze(args.collected)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    export_records(report, args.output_dir)
    if args.plot:
        plot(report, args.output_dir)
    print(json.dumps({key: value['points'] for key, value in report['phases'].items()}, indent=2))
