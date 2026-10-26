#!/usr/bin/env python3
"""Export audited automatic-tuning observations for tables and website graphs."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics

from analyze_productive import analyze


def apply_review(analysis, manifest_bytes, review):
    """Bind acceptance/rejection to the complete audited experiment, not a partial pair."""
    assert review['decision'] in ('accept_challenger_order', 'reject_challenger_order')
    assert review['result_manifest_sha256'] == hashlib.sha256(manifest_bytes).hexdigest()
    assert review['binary_provenance'] == analysis['binary_provenance']
    assert review['resource_validation'] == analysis['resource_validation']
    for phase in ('cold', 'warm', 'fixed_streaming_build_control'):
        assert review[phase + '_comparison'] == analysis[phase]['comparison']
    accepted = review['decision'] == 'accept_challenger_order'
    assert not accepted or analysis['numerical_gain_gate_passed']
    analysis['landing_status'] = ('Accepted challenger ordering for AMD family 1Ah/model 02h'
                                  if accepted else 'Rejected challenger-order experiment')


def records(analysis):
    hardware = analysis['hardware']
    assert hardware['CPU family'] == '26' and hardware['Model'] == '2'
    assert hardware['CPU(s)'] == '64' and hardware['Socket(s)'] == '1'
    output = []
    for warm in (False, True):
        phase = 'cached_restart' if warm else 'cold_discovery'
        for role in ('control', 'candidate'):
            runs = sorted((run for run in analysis['runs'].values()
                           if run['binary'] == role and run['warm'] == warm), key=lambda run: run['pair'])
            assert [run['pair'] for run in runs] == [1, 2, 3, 4]
            assert len({run['cpu_profile'] for run in runs}) == 1
            hashes = sum(run['completed_hashes_lower_bound'] for run in runs)
            seconds = sum(run['wall_seconds'] for run in runs)
            rates = [run['completed_hps_lower_bound'] for run in runs]
            hosts = [run['kernel_cache']['host'] for run in runs]
            assert all(host['os'] == hosts[0]['os'] and
                       host['kernel_version'] == hosts[0]['kernel_version'] for host in hosts)
            observations = [{key: run[key] for key in ('pair', 'completed_hashes_lower_bound',
                'wall_seconds', 'completed_hps_lower_bound', 'starting_threads', 'selected_threads',
                'first_streaming_confirmation_observed_seconds', 'log_sha256', 'window_sha256')}
                for run in runs]
            output.append({'id': f'turin-order-{phase}-{role}', 'campaign': 'amd-overnight-20261025',
                'hardware': hardware['Model name'], 'category': 'amd', 'backend': 'cpu',
                'os': hosts[0]['os'], 'os_kernel_release': hosts[0]['kernel_version'],
                'cpu_vendor': 'AuthenticAMD', 'cpu_family': 26, 'cpu_model': 2,
                'sockets': 1, 'physical_cores': 32, 'hardware_threads_per_core': 2, 'numa_nodes': 1,
                'virtualization': 'none', 'installed_memory_gib': 192,
                'memory_channels_populated': 12, 'memory_type': 'DDR5', 'memory_speed_mts': 4800,
                'memory_configuration_source': 'experiments/cherry-epyc-energy-20261025/benchmark-records.json',
                'phase': phase, 'role': role, 'kernel': 'auto', 'workers': None,
                'cpu_profile': runs[0]['cpu_profile'],
                'available_hardware_threads': 64, 'affinity': 'auto', 'page_mode': 'large',
                'hugepage_size_kib': 2048, 'page_setup': 'Explicitly reserved by experiment controller',
                'selection': 'automatic_cpu_count_and_kernel',
                'workload': 'legacy_argon2id_2gib', 'benchmark_kind': 'productive_pool_fixture',
                'metric_scope': 'completed_hash_lower_bound_from_start_request_through_stopped_service',
                'power_scope': 'unmeasured', 'power_cap_w': 280,
                'package_watts': None, 'package_joules_per_hash': None, 'hashes_per_package_joule': None,
                'aggregation': 'ratio_of_totals', 'repetitions': 4,
                'requested_seconds': 180 if warm else 1200,
                **analysis['binary_provenance'][role],
                'completed_hashes_lower_bound': hashes, 'invocation_seconds': seconds,
                'hps': hashes / seconds, 'hps_is_lower_bound': True,
                'hps_sample_cv': statistics.stdev(rates) / statistics.mean(rates),
                'observations': observations,
                'source': 'experiments/amd-overnight-20261025/results.json',
                'candidate_status': analysis['landing_status'],
                'numerical_gain_gate_passed': analysis['numerical_gain_gate_passed']})
    return {'schema': 'seine-hardware-benchmark-records/v1',
        'description': 'Automatic productive-tuning observations; explicitly provisioned HugeTLB pages.',
        'comparison_rule': 'Compare cold with cold and cached with cached. These log-derived lower bounds are not fixed-kernel backend throughput or package-energy measurements.',
        'records': output}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('collected', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--review', type=Path, help='Explicit decision bound to the full evidence and frozen builds')
    parser.add_argument('--resource-supplement', type=Path, help='Verified same-binary resource supplement')
    args = parser.parse_args()
    # The full audit requires all cold/warm pairs, reference checks and completed
    # lifecycle evidence. It cannot export a cherry-picked partial campaign.
    analysis = analyze(args.collected, args.resource_supplement)
    if args.review:
        apply_review(analysis, (args.collected / 'results/manifest.json').read_bytes(),
                     json.loads(args.review.read_text()))
    result = records(analysis)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'benchmark-records.json').write_text(json.dumps(result, indent=2) + '\n')
    columns = ('id', 'hardware', 'phase', 'role', 'selection', 'cpu_profile', 'page_mode', 'metric_scope',
        'source_revision', 'binary_sha256', 'repetitions', 'requested_seconds',
        'completed_hashes_lower_bound', 'invocation_seconds', 'hps', 'hps_is_lower_bound',
        'hps_sample_cv', 'power_scope', 'power_cap_w', 'package_watts', 'candidate_status')
    with (args.output / 'benchmark-records.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction='ignore', lineterminator='\n')
        writer.writeheader()
        writer.writerows(result['records'])
