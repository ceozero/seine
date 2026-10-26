#!/usr/bin/python3
"""Audit collected ring screens and export bounded, fixed-configuration results."""
import argparse
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import statistics

from collect import inspect_collected


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close(left, right):
    assert math.isfinite(left) and math.isfinite(right)
    assert math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-12), (left, right)


def report_rate(report, checks, workers, seconds):
    assert report['schema_version'] == 14 and report['bench_kind'] == 'backend'
    assert report['cpu_threads'] == workers and report['bench_secs'] == seconds
    assert report['rounds'] == 2 and report['warmup_rounds'] == 1
    assert len(report['runs']) == 2
    config = report['config_fingerprint']
    assert config['cpu_kernel'] == config['cpu_kernel_requested'] == 'avx512-256-stream'
    assert config['cpu_page_mode'] == 'large' and config['cpu_affinity'] == 'auto'
    assert config['cpu_autotune_threads'] is False
    assert report['pow_fingerprint'] == {'memory_kb': 2097152, 'iterations': 1,
        'parallelism': 1, 'output_len': 32, 'header_base_len': 92}
    identity = report['environment']['cpu_identity']
    assert (identity['vendor'], identity['family'], identity['model']) == ('AuthenticAMD', 26, 2)
    assert all(checks['delta'][key] == 0 for key in ('pswpin', 'pswpout', 'oom_kill'))
    assert checks['steal_pct'] < 2 and checks['steal_single_cpu_upper_pct'] < 2
    for run in report['runs']:
        assert run['hashes'] > 0 and run['elapsed_secs'] >= seconds
        close(run['elapsed_secs'], run['actual_elapsed_secs'])
        assert run['hashes'] == run['counted_hashes'] + run['late_hashes']
        assert sum(b['hashes'] for b in run['backend_runs']) == run['hashes']
        assert sum(b['memory_explicit_large_workers'] for b in run['backend_runs']) == workers
        assert sum(b['memory_explicit_large_bytes'] for b in run['backend_runs']) == workers * 2 * 1024**3
        for backend in run['backend_runs']:
            for key in ('memory_allocation_failures', 'dropped_events', 'assignment_enqueue_timeouts',
                        'assignment_execution_timeouts', 'control_enqueue_timeouts', 'control_execution_timeouts'):
                assert backend[key] == 0, key
            for backing in ('explicit_large_1g', 'transparent_huge', 'regular', 'heap'):
                assert backend['memory_' + backing + '_workers'] == 0
                assert backend['memory_' + backing + '_bytes'] == 0
    hashes = sum(r['hashes'] for r in report['runs'])
    assert report['total_hashes'] == hashes
    elapsed = sum(r['elapsed_secs'] for r in report['runs'])
    return {'completed_hashes': hashes, 'elapsed_seconds': elapsed, 'hps': hashes / elapsed}


def compare(folder, expected, workers, ring, pairs, seconds):
    assert (folder / 'COMPLETE').is_file()
    protocol, saved = read(folder / 'protocol.json'), read(folder / 'pairs.json')
    assert (protocol['workers'], protocol['pairs'], protocol['seconds'], protocol['rounds'], protocol['warmup']) == (workers, pairs, seconds, 2, 1)
    assert protocol['harness_sha256'] == expected['bench.py']
    assert len(saved) == pairs
    expected_cases = {'baseline': {'binary': 'ring-64', 'kernel': 'avx512-256-stream'},
                      'candidate': {'binary': 'ring-' + str(ring), 'kernel': 'avx512-256-stream'}}
    assert protocol['cases'] == expected_cases
    assert {Path(name).name: sha for name, sha in protocol['sha256'].items()} == {
        case['binary']: expected[case['binary']] for case in expected_cases.values()}
    observations = {role: [] for role in expected_cases}
    context = None
    for pair in range(1, pairs + 1):
        for role in expected_cases:
            name = f'{pair}-{role}'
            report = read(folder / (name + '.json'))
            checks = read(folder / (name + '-checks.json'))
            value = report_rate(report, checks, workers, seconds)
            close(value['hps'], saved[pair - 1][role]['completed_hps'])
            environment = report['environment']
            current = {'config': report['config_fingerprint'], 'pow': report['pow_fingerprint'],
                'environment': {key: environment[key] for key in ('hostname', 'os', 'kernel_version',
                    'cpu_identity', 'logical_cores', 'physical_cores', 'build_profile', 'build_opt_level',
                    'build_rustflags', 'build_features', 'rustc_version', 'target_triple', 'runtime_environment')}}
            if context is None:
                context = current
            assert current == context, 'comparison context changed'
            observations[role].append({'pair': pair, **value,
                'report_sha256': digest(folder / (name + '.json')),
                'checks_sha256': digest(folder / (name + '-checks.json'))})
    ratios = [c['hps'] / b['hps'] for b, c in zip(observations['baseline'], observations['candidate'])]
    geometric = 100 * (math.exp(statistics.mean(map(math.log, ratios))) - 1)
    summary = read(folder / 'summary.json')
    assert len(summary['paired_deltas_pct']) == pairs
    assert len(summary['paired_resampling_interval_pct']) == 2
    close(geometric, summary['paired_geometric_delta_pct'])
    for ratio, saved_delta in zip(ratios, summary['paired_deltas_pct']):
        close(100 * (ratio - 1), saved_delta)
    bootstrap = sorted(100 * (math.exp(statistics.mean(math.log(ratios[i]) for i in picks)) - 1)
        for picks in itertools.product(range(pairs), repeat=pairs))
    def percentile(p):
        index = p * (len(bootstrap) - 1)
        lo, hi = math.floor(index), math.ceil(index)
        return bootstrap[lo] + (index - lo) * (bootstrap[hi] - bootstrap[lo])
    for actual, saved_bound in zip((percentile(.025), percentile(.975)), summary['paired_resampling_interval_pct']):
        close(actual, saved_bound)
    for role in observations:
        close(statistics.mean(v['hps'] for v in observations[role]), summary['completed_hps'][role])
    return {'workers': workers, 'ring': ring, 'pairs': pairs, 'seconds': seconds,
        'summary': summary, 'observations': observations}


def diagnostics(root):
    definitions_path = root / 'results/perf-event-definitions.json'
    definitions = {event['EventName']: event for event in read(definitions_path)}
    encodings = {'l2_cache_req_stat.dc_access_in_l2': 'cpu/event=0x64,umask=0xf8/',
                 'l2_cache_req_stat.ls_rd_blk_c': 'cpu/event=0x64,umask=8/'}
    output = {'scope': 'Separate 30-second whole-invocation diagnostic of ring 64; no uncounted warmup.',
        'limitations': 'Userspace counters aggregate worker threads, including SMT siblings; cycles are not elapsed latency. L2 requests are not DRAM traffic. HSMP integer GB/s readings are non-atomic firmware estimates, not integrated bytes/hash. Samples include startup and shutdown.',
        'event_definitions_sha256': digest(definitions_path), 'observations': []}
    for workers in (32, 64):
        prefix = root / 'results' / ('profile-control-' + str(workers))
        status_path = Path(str(prefix) + '-status.json')
        if not status_path.exists() or read(status_path)['exit_code'] != 0:
            output['observations'].append({'workers': workers, 'status': 'UNAVAILABLE'})
            continue
        assert all(definitions[event]['Encoding'] == encoding for event, encoding in encodings.items())
        report = read(Path(str(prefix) + '-bench.json'))
        hsmp = read(Path(str(prefix) + '-hsmp.json'))
        counters = [json.loads(line) for line in Path(str(prefix) + '-perf.json').read_text().splitlines()]
        assert len(counters) == 4 and all(v['pcnt-running'] == 100 for v in counters)
        assert len({v['event-runtime'] for v in counters}) == 1
        assert report['bench_kind'] == 'end_to_end' and report['bench_secs'] == 30
        assert report['rounds'] == 1 and report['warmup_rounds'] == 0
        assert report['cpu_threads'] == workers and hsmp['exit_code'] == 0
        assert report['config_fingerprint']['cpu_kernel'] == 'avx512-256-stream'
        assert report['config_fingerprint']['cpu_page_mode'] == 'large'
        assert all(sum(b['memory_explicit_large_workers'] for b in run['backend_runs']) == workers
                   for run in report['runs'])
        hashes = sum(run['hashes'] for run in report['runs'])
        raw = {v['event']: float(v['counter-value']) for v in counters}
        assert all(math.isfinite(value) and value > 0 for value in raw.values())
        assert set(raw) == {'cycles:u', 'instructions:u', *(event + ':u' for event in encodings)}
        output['observations'].append({'workers': workers, 'status': 'COMPLETE',
            'completed_hashes': hashes, 'counter_scheduling_percent': 100, 'raw_user_counters': raw,
            'user_counter_per_completed_hash': {key: value / hashes for key, value in raw.items()},
            'hsmp_units': hsmp['units'], 'hsmp_samples': [s['values'] for s in hsmp['samples']],
            'hsmp_read_errors': [s['errors'] for s in hsmp['samples'] if s['errors']],
            'benchmark_sha256': digest(Path(str(prefix) + '-bench.json')),
            'perf_sha256': digest(Path(str(prefix) + '-perf.json')),
            'hsmp_sha256': digest(Path(str(prefix) + '-hsmp.json'))})
    return output


def analyze(root):
    collection = inspect_collected(root)
    assert collection['ready_for_followup']
    assert collection['outcomes']['results']['status'] == 'COMPLETE'
    receipt = read(root.parent / 'collection-verification.json')
    archive = root.parent / 'evidence.tar.gz'
    assert receipt['archive_sha256'] == digest(archive)
    assert all(receipt[key] == value for key, value in collection.items())
    expected = read(root / 'expected-files.json')
    protocol = read(root / 'results/protocol.json')
    assert protocol['expected_files'] == expected and protocol['cap_uw'] == 280000000
    for ring in (64, 32, 16):
        lines = (root / f'results/reference-ring-{ring}.log').read_text().splitlines()
        passes = [line for line in lines if line.startswith('PASS nonce=')]
        assert len(passes) == 21
        assert all('full_size_bytes=2147483648 dirty_reuse=true guards=true' in line for line in passes)
    comparisons = []
    for workers in (32, 64):
        for ring in (32, 16):
            label = f'screen-{workers}-ring-{ring}'
            comparisons.append({'phase': 'screen', 'label': label,
                **compare(root / 'results' / label, expected, workers, ring, 2, 15)})
    selection = read(root / 'results/screen-selection.json')
    largest = max(comparisons, key=lambda value: value['summary']['paired_geometric_delta_pct'])
    if largest['summary']['paired_geometric_delta_pct'] > 0:
        shortlist = selection['shortlist']
        assert (shortlist['workers'], shortlist['ring']) == (largest['workers'], largest['ring'])
        close(shortlist['paired_geometric_delta_pct'], largest['summary']['paired_geometric_delta_pct'])
    else:
        assert selection['shortlist'] is None
    result = {'schema': 'seine-ring-locality-results/v1', 'collection': receipt,
        'screen_manifest_sha256': digest(root / 'results/manifest.json'),
        'hardware': {key: protocol['hardware'][key] for key in ('Model name', 'CPU family', 'Model',
            'Socket(s)', 'CPU(s)', 'Core(s) per socket', 'Thread(s) per core', 'NUMA node(s)')},
        'expected_binary_sha256': {str(ring): expected['ring-' + str(ring)] for ring in (64, 32, 16)},
        'comparisons': comparisons, 'shortlist': selection['shortlist'], 'shipping_change_accepted': False}
    environment = read(root / 'results/screen-32-ring-32/1-baseline.json')['environment']
    result['environment'] = {key: environment[key] for key in ('os', 'kernel_version', 'cpu_arch',
        'runtime_environment', 'target_triple', 'rustc_version', 'build_profile',
        'build_opt_level', 'build_rustflags', 'build_features')}
    result['diagnostics'] = diagnostics(root)
    confirmation = root / 'confirmation-results'
    if confirmation.exists():
        assert selection['shortlist'] is not None
        p = read(confirmation / 'protocol.json')
        assert p['screen_manifest_sha256'] == result['screen_manifest_sha256']
        assert (p['workers'], p['ring']) == (largest['workers'], largest['ring'])
        comparison = compare(confirmation / 'throughput', expected, p['workers'], p['ring'], 4, 30)
        comparisons.append({'phase': 'confirmation', 'label': 'confirmation', **comparison})
        gate = comparison['summary']['paired_resampling_interval_pct'][0] > 1
        assert read(confirmation / 'throughput-gate.json')['passed'] == gate
        result['confirmation_throughput_gate_passed'] = gate
        if gate:
            from compare_energy import compare as energy_compare
            result['energy_comparison'] = energy_compare(confirmation, p['binary_sha256'], p['workers'])
    return result


def records(result, builds):
    output = []
    for comparison in result['comparisons']:
        for role, ring in (('baseline', 64), ('candidate', comparison['ring'])):
            observations = comparison['observations'][role]
            source = builds['variants'][str(ring)]
            assert source['binary_sha256'] == result['expected_binary_sha256'][str(ring)]
            hashes = sum(v['completed_hashes'] for v in observations)
            elapsed = sum(v['elapsed_seconds'] for v in observations)
            rates = [v['hps'] for v in observations]
            output.append({'id': comparison['label'] + '-' + role, 'campaign': 'amd-ring-locality-20261025',
                'hardware': result['hardware']['Model name'], 'category': 'amd', 'backend': 'cpu',
                'os': result['environment']['os'], 'os_kernel_release': result['environment']['kernel_version'],
                'physical_cores': 32, 'hardware_threads': 64, 'sockets': 1, 'numa_nodes': 1,
                'cpu_vendor': 'AuthenticAMD', 'cpu_family': 26, 'cpu_model': 2, 'virtualization': 'none',
                'installed_memory_gib': 192, 'memory_channels_populated': 12, 'memory_speed_mts': 4800,
                'memory_configuration_source': 'experiments/cherry-epyc-energy-20261025/benchmark-records.json',
                'workers': comparison['workers'], 'ring_blocks': ring, 'ring_bytes_per_worker': ring * 1024,
                'kernel': 'avx512-256-stream', 'selection': 'fixed_experimental_kernel_and_workers',
                'page_mode': 'large', 'hugepage_size_kib': 2048, 'affinity': 'auto', 'cpu_profile': 'balanced',
                'phase': comparison['phase'], 'role': role, 'requested_seconds_per_round': comparison['seconds'],
                'measured_rounds_per_invocation': 2, 'warmup_rounds_per_invocation': 1,
                'repetitions': comparison['pairs'], 'benchmark_kind': 'backend',
                'workload': 'legacy_argon2id_2gib',
                'metric_scope': 'completed_hashes_over_measured_backend_time_including_fence',
                'aggregation': 'ratio_of_totals', 'completed_hashes': hashes, 'elapsed_seconds': elapsed,
                'hps': hashes / elapsed, 'hps_sample_cv': statistics.stdev(rates) / statistics.mean(rates),
                'power_scope': 'unmeasured', 'power_cap_w': 280, 'package_watts': None,
                'source_revision': source['source_revision'], 'runtime_source_base': source['runtime_source_base'],
                'variant_patch_sha256': source['patch_sha256'], 'binary_sha256': source['binary_sha256'],
                'observations': observations, 'candidate_status': 'Experimental; no shipping acceptance from this record',
                'source': 'experiments/amd-ring-locality-20261025/results.json'})
    return {'schema': 'seine-hardware-benchmark-records/v1',
        'comparison_rule': 'Compare roles within a single label, worker count and phase. Screening is not confirmation; backend rates exclude startup/warmup/teardown.',
        'records': output}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('collected', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = analyze(args.collected)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    data = records(result, read(Path(__file__).with_name('frozen-builds.json')))
    (args.output / 'benchmark-records.json').write_text(json.dumps(data, indent=2) + '\n')
    columns = ('id', 'hardware', 'phase', 'role', 'workers', 'ring_blocks', 'selection', 'page_mode',
        'metric_scope', 'source_revision', 'runtime_source_base', 'variant_patch_sha256', 'binary_sha256',
        'repetitions', 'requested_seconds_per_round', 'completed_hashes', 'elapsed_seconds', 'hps',
        'hps_sample_cv', 'power_scope', 'power_cap_w', 'candidate_status')
    with (args.output / 'benchmark-records.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction='ignore', lineterminator='\n')
        writer.writeheader()
        writer.writerows(data['records'])
    print(json.dumps({'comparisons': len(result['comparisons']), 'records': len(data['records']),
        'shortlist': result['shortlist'], 'shipping_change_accepted': False}, indent=2))
