#!/usr/bin/env python3
"""Export audited Genoa VM observations without implying full-socket or power data."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics

from assess import assess


def apply_review(analysis, provenance, manifest_bytes, review):
    """Bind an explicit adoption decision to the exact audited evidence/builds."""
    assert not analysis['protocol_checks']['tuning_gate_failures']
    assert review['decision'] == 'accept_automatic_trial_eligibility'
    assert review['result_manifest_sha256'] == hashlib.sha256(manifest_bytes).hexdigest()
    assert review['binary_sha256'] == provenance['sha256']
    for phase in ('cold', 'warm'):
        assert review[phase + '_paired_deltas_pct'] == analysis[phase]['paired_deltas_pct']
    assert review['fixed_control_delta_pct'] == analysis['fixed']['fixed-avx2-control']['geometric_delta_pct']
    analysis['protocol_checks']['landing_status'] = 'Accepted for automatic trials on AMD family 19h/model 11h'


def records(analysis, provenance, manifest):
    fields = {entry['field'].rstrip(':'): entry['data'] for entry in analysis['hardware']['lscpu']}
    assert fields['Vendor ID'] == 'AuthenticAMD'
    assert int(fields['CPU family']) == 25 and int(fields['Model']) == 17
    assert int(fields['CPU(s)']) == 32 and fields.get('Hypervisor vendor') in ('KVM', 'AWS')
    output = []
    for warm in (False, True):
        phase, prefix = ('cached_restart', 'joint-warm-') if warm else ('cold_discovery', 'joint-')
        for role in ('control', 'candidate'):
            observations, hosts, memories, profiles = [], [], [], []
            for suffix in ('a', 'b'):
                label = prefix + role + '-' + suffix
                run = analysis['productive'][label]
                assert run['cache_mode'] == ('warm' if warm else 'cold')
                assert run['identity']['binary_sha256'] == provenance['sha256'][role]
                window = run['window']
                observations.append({'pair': suffix,
                    'completed_hashes_lower_bound': window['completed_hashes_lower_bound'],
                    'wall_seconds': window['elapsed_start_request_through_stopped_seconds'],
                    'completed_hps_lower_bound': window['completed_hps_lower_bound'],
                    'starting_threads': run['starting_threads'],
                    'selected_threads': run['caches'].get('tuning.json', {}).get('selected_threads'),
                    'log_sha256': manifest['results/' + label + '/miner.log'],
                    'window_sha256': manifest['results/' + label + '/productive-window.json']})
                hosts.append(run['caches']['tuning.json.kernels.json']['host'])
                memories.append(run['identity']['meminfo_before']['MemTotal'] * 1024)
                profiles.append(run['caches']['tuning.json']['profile'])
            assert len(set(memories)) == 1
            assert len(set(profiles)) == 1
            assert all(host['os'] == hosts[0]['os'] and
                       host['kernel_version'] == hosts[0]['kernel_version'] for host in hosts)
            hashes = sum(run['completed_hashes_lower_bound'] for run in observations)
            seconds = sum(run['wall_seconds'] for run in observations)
            rates = [run['completed_hps_lower_bound'] for run in observations]
            output.append({'id': f'genoa-c7a8xlarge-{phase}-{role}',
                'campaign': 'genoa-streaming-20261025', 'hardware': fields['Model name'],
                'category': 'amd', 'backend': 'cpu', 'os': hosts[0]['os'],
                'os_kernel_release': hosts[0]['kernel_version'], 'cpu_vendor': 'AuthenticAMD',
                'cpu_family': 25, 'cpu_model': 17, 'virtualization': fields['Hypervisor vendor'],
                'provider': 'AWS', 'instance_type': 'c7a.8xlarge', 'region': 'us-east-1',
                'hardware_scope': 'Guest-visible resources; not a full bare-metal EPYC socket',
                'guest_vcpus': 32, 'guest_threads_per_exposed_core': int(fields['Thread(s) per core']),
                'guest_numa_nodes': int(fields['NUMA node(s)']), 'physical_cores': None,
                'guest_memory_total_bytes': memories[0], 'allocated_memory_gib': 64,
                'installed_memory_gib': None, 'memory_channels_populated': None,
                'memory_type': None, 'memory_speed_mts': None,
                'phase': phase, 'role': role, 'kernel': 'auto', 'workers': None,
                'cpu_profile': profiles[0],
                'autotune_worker_maximum': 24, 'affinity': 'auto', 'page_mode': 'large',
                'hugepage_size_kib': 2048, 'page_setup': 'Explicitly reserved by experiment controller',
                'selection': 'automatic_cpu_count_and_kernel_with_24_worker_ceiling',
                'workload': 'legacy_argon2id_2gib', 'benchmark_kind': 'productive_pool_fixture',
                'metric_scope': 'completed_hash_lower_bound_from_start_request_through_stopped_service',
                'power_scope': 'unmeasured', 'power_cap_w': None, 'package_watts': None,
                'package_joules_per_hash': None, 'hashes_per_package_joule': None,
                'aggregation': 'ratio_of_totals', 'repetitions': 2,
                'requested_seconds': 180 if warm else 900,
                'source_revision': provenance[role + '_commit'],
                'binary_sha256': provenance['sha256'][role],
                'completed_hashes_lower_bound': hashes, 'invocation_seconds': seconds,
                'hps': hashes / seconds, 'hps_is_lower_bound': True,
                'hps_sample_cv': statistics.stdev(rates) / statistics.mean(rates),
                'observations': observations,
                'source': 'experiments/genoa-streaming-20261025/results.json',
                'candidate_status': analysis['protocol_checks']['landing_status']})
    return {'schema': 'seine-hardware-benchmark-records/v1',
        'description': 'Automatic productive-tuning observations in a 32-vCPU Genoa VM with a 24-worker ceiling.',
        'comparison_rule': 'Compare cold with cold and cached with cached. Two pairs describe one VM/session only. No power or full-socket performance claim.',
        'records': output}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('collected', type=Path)
    parser.add_argument('provenance', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--review', type=Path, help='Explicit adoption decision bound to the measured evidence')
    parser.add_argument('--include-rejected', action='store_true',
                        help='Export rejected tuning outcomes with explicit rejection labels')
    args = parser.parse_args()
    analysis = assess(args.collected, include_rejected=args.include_rejected)
    provenance = json.loads(args.provenance.read_text())
    manifest_bytes = (args.collected / 'result-manifest.json').read_bytes()
    if args.review:
        apply_review(analysis, provenance, manifest_bytes, json.loads(args.review.read_text()))
    result = records(analysis, provenance, json.loads(manifest_bytes))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'benchmark-records.json').write_text(json.dumps(result, indent=2) + '\n')
    columns = ('id', 'hardware', 'instance_type', 'hardware_scope', 'phase', 'role', 'selection', 'cpu_profile',
        'page_mode', 'metric_scope', 'source_revision', 'binary_sha256', 'repetitions',
        'requested_seconds', 'completed_hashes_lower_bound', 'invocation_seconds', 'hps',
        'hps_is_lower_bound', 'hps_sample_cv', 'power_scope', 'package_watts', 'candidate_status')
    with (args.output / 'benchmark-records.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction='ignore', lineterminator='\n')
        writer.writeheader()
        writer.writerows(result['records'])
