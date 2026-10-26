#!/usr/bin/python3
"""Export verified page-size energy results or an explicit unavailable outcome."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics
import sys

from compare_energy import compare, expected_pool_state, PAGE_MODES
sys.path.append(str(Path(__file__).resolve().parents[1] / 'amd-ring-locality-20261025'))
from collect import inspect_collected


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def analyze(root):
    collection = inspect_collected(root)
    assert collection['ready_for_followup']
    receipt = read(root.parent / 'collection-verification.json')
    assert all(receipt[key] == value for key, value in collection.items())
    assert receipt['archive_sha256'] == digest(root.parent / 'evidence.tar.gz')
    out = root / 'results'
    protocol = read(out / 'protocol.json')
    expected = read(root / 'expected-files.json')
    assert protocol['binary_sha256'] == expected['miner']
    assert protocol['verifier_sha256'] == expected['verify_streaming_1g']
    assert protocol['workers'] == 64 and protocol['cap_uw'] == 280000000
    assert protocol['pairs'] == 4 and protocol['seconds'] == 120
    assert protocol['page_modes'] == PAGE_MODES
    assert read(out / 'vm-checks.json') == {'pswpin': 0, 'pswpout': 0, 'oom_kill': 0}
    outcome = collection['outcomes']['results']
    assert outcome['status'] in ('UNAVAILABLE', 'COMPLETE')
    source = read(root / 'miner-provenance.json')
    assert source['artifact_sha256']['seine'] == expected['miner']
    result = {'schema': 'seine-page-size-results/v1', 'status': outcome['status'],
        'collection': receipt, 'result_manifest_sha256': digest(out / 'manifest.json'),
        'hardware': {key: protocol['hardware'][key] for key in ('Model name', 'CPU family', 'Model',
            'Socket(s)', 'CPU(s)', 'Core(s) per socket', 'Thread(s) per core', 'NUMA node(s)')},
        'binary_sha256': expected['miner'], 'source_revision': source['source_commit'],
        'runtime_source_base': source['kernel_source_base'],
        'variant_patch_sha256': source['artifact_sha256']['candidate.patch'],
        'verifier_sha256': expected['verify_streaming_1g'],
        'allocation_feasibility': read(out / 'allocation-feasibility.json'),
        'default_policy_changed': False}
    allocation = result['allocation_feasibility']
    if outcome['status'] == 'UNAVAILABLE':
        assert allocation['returncode'] != 0 or allocation['observed'] != expected_pool_state('large-1g')
        result['reason'] = 'Could not reserve all 128 free 1 GiB pages under the frozen 64-worker protocol. No performance or efficiency result.'
        return result
    assert allocation['returncode'] == 0 and allocation['observed'] == expected_pool_state('large-1g')
    lines = (out / 'one-gib-reference-parity.log').read_text().splitlines()
    assert any('kernel_page_size_kib=1048576' in line for line in lines)
    passes = [line for line in lines if line.startswith('PASS nonce=')]
    assert len(passes) == 21 and all('backing=large-1g full_size_bytes=2147483648 dirty_reuse=true guards=true' in line for line in passes)
    comparison = compare(out, expected['miner'])
    result['comparison'] = comparison
    metrics = comparison['metrics']
    jph = metrics['invocation_joules_per_completed_hash']['comparison']['paired_geometric_delta_ci95_pct']
    hps = metrics['invocation_completed_hashes_per_second']['comparison']['paired_geometric_delta_ci95_pct']
    result['efficiency_gate_passed'] = jph[1] < 0 and hps[0] >= -2
    result['throughput_gate_passed'] = hps[0] > 0
    return result


def records(result):
    values = []
    if result['status'] == 'COMPLETE':
        for role, mode in PAGE_MODES.items():
            observations = [v for v in result['comparison']['observations'] if v['role'] == role]
            assert [v['pair'] for v in observations] == [1, 2, 3, 4]
            hashes = sum(v['completed_hashes'] for v in observations)
            seconds = sum(v['invocation_seconds'] for v in observations)
            joules = sum(v['package_joules'] for v in observations)
            rates = [v['completed_hashes'] / v['invocation_seconds'] for v in observations]
            values.append({'id': 'turin-page-size-' + role, 'campaign': 'amd-page-size-20261025',
                'hardware': result['hardware']['Model name'], 'category': 'amd', 'backend': 'cpu',
                'cpu_vendor': 'AuthenticAMD', 'cpu_family': 26, 'cpu_model': 2, 'sockets': 1,
                'physical_cores': 32, 'hardware_threads_per_core': 2, 'numa_nodes': 1, 'virtualization': 'none',
                'installed_memory_gib': 192, 'memory_channels_populated': 12, 'memory_type': 'DDR5',
                'memory_speed_mts': 4800, 'workers': 64, 'kernel': 'avx512-256-stream',
                'ring_blocks': 64, 'affinity': 'auto', 'page_mode': mode,
                'hugepage_size_kib': 2048 if role == 'baseline' else 1048576,
                'selection': 'manual_fixed_configuration', 'phase': 'page_size', 'role': role,
                'workload': 'legacy_argon2id_2gib', 'benchmark_kind': 'end-to-end',
                'metric_scope': 'whole_invocation', 'power_scope': 'cpu_package', 'power_cap_w': 280,
                'aggregation': 'ratio_of_totals', 'requested_benchmark_seconds': 120,
                'repetitions': 4, 'measured_rounds_per_invocation': 1, 'warmup_rounds': 0,
                'completed_hashes': hashes, 'invocation_seconds': seconds, 'package_joules': joules,
                'hps': hashes / seconds, 'package_watts': joules / seconds,
                'package_joules_per_hash': joules / hashes, 'hashes_per_package_joule': hashes / joules,
                'hps_sample_cv': statistics.stdev(rates) / statistics.mean(rates),
                'source_revision': result['source_revision'], 'runtime_source_base': result['runtime_source_base'],
                'variant_patch_sha256': result['variant_patch_sha256'], 'binary_sha256': result['binary_sha256'],
                'observations': observations, 'source': 'experiments/amd-page-size-20261025/results.json'})
    return {'schema': 'seine-hardware-benchmark-records/v1', 'status': result['status'],
        'comparison_rule': 'Same executable and 64 workers; only explicit page size differs. Includes startup/work/fences/teardown; excludes page-pool setup, unmeasured DRAM and wall losses. An unavailable outcome has no numeric graph points.',
        'records': values}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('collected', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = analyze(args.collected)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    data = records(result)
    (args.output / 'benchmark-records.json').write_text(json.dumps(data, indent=2) + '\n')
    columns = ('id', 'hardware', 'role', 'workers', 'page_mode', 'selection', 'metric_scope',
        'power_scope', 'power_cap_w', 'source_revision', 'binary_sha256', 'repetitions',
        'completed_hashes', 'invocation_seconds', 'package_joules', 'hps', 'package_watts',
        'package_joules_per_hash', 'hashes_per_package_joule', 'hps_sample_cv')
    with (args.output / 'benchmark-records.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction='ignore', lineterminator='\n')
        writer.writeheader()
        writer.writerows(data['records'])
    print(json.dumps({'status': result['status'], 'records': len(data['records']),
        'efficiency_gate_passed': result.get('efficiency_gate_passed'),
        'throughput_gate_passed': result.get('throughput_gate_passed')}, indent=2))
