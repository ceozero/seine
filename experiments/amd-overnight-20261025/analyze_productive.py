#!/usr/bin/env python3
"""Audit raw native comparisons and export paired cold/cached discovery results."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from benchctl import PairedValue, summarize_pairs, DEFAULT_BOOTSTRAP_SAMPLES, DEFAULT_BOOTSTRAP_SEED


def read(path):
    return json.loads(path.read_text())


def paired(values, metric):
    return summarize_pairs(values, metric, DEFAULT_BOOTSTRAP_SAMPLES, DEFAULT_BOOTSTRAP_SEED)


def analyze(root, resource_supplement=None):
    out = root / 'results'
    manifest = read(out / 'manifest.json')
    for name, digest in manifest.items():
        assert hashlib.sha256((out / name).read_bytes()).hexdigest() == digest, name
    outcome = read(out / 'outcome.json')
    if resource_supplement is None:
        assert outcome['status'] == 'COMPLETE' and outcome['settings_restored'] and not outcome['cleanup_failures']
        assert (out / 'lifecycle/COMPLETE').exists()
        resource = {'status': 'COMPLETE_IN_ORIGINAL_CAMPAIGN'}
    else:
        from audit_resource import verify_supplement
        resource = verify_supplement(root, resource_supplement)
    parity = [line for line in (out / 'reference-parity.log').read_text().splitlines()
              if line.startswith('PASS nonce=')]
    assert len(parity) == 21 and all('full_size_bytes=2147483648 dirty_reuse=true guards=true' in line for line in parity)
    protocol = read(out / 'protocol.json')
    assert protocol['cold_seconds'] == 1200 and protocol['warm_seconds'] == 180
    expected_order = [[binary, pair] for pair in range(1, 5)
        for binary in (('control', 'candidate') if pair % 2 else ('candidate', 'control'))]
    assert protocol['order'] == expected_order
    result = {'schema': 'seine-productive-comparison/v1', 'verified_files': len(manifest),
        'scope': 'Completed-hash lower bounds over service start through shutdown, automatic count/kernel selection; explicitly prepared 2 MiB HugeTLB.',
        'binary_provenance': read(root / 'binary-provenance.json'), 'resource_validation': resource, 'runs': {},
        'hardware': {k: protocol['hardware'][k] for k in ('Model name', 'CPU family', 'Model',
            'Socket(s)', 'CPU(s)', 'Core(s) per socket', 'Thread(s) per core', 'NUMA node(s)')}}
    for warm in (False, True):
        prefix = 'joint-warm-' if warm else 'joint-'
        for binary, pair in expected_order:
            label = f'{prefix}{binary}-{pair}'
            folder = out / label
            assert (folder / 'COMPLETE').exists(), label
            assert read(folder / 'cleanup.json') == {'failures': [], 'primary_failure': None}
            identity = read(folder / 'identity.json')
            assert identity['binary_sha256'] == protocol['binary_sha256'][binary]
            assert bool(identity['cache_source']) == warm
            assert identity['seconds'] == (180 if warm else 1200)
            command = read(folder / 'command.json')
            assert not any(flag in command for flag in ('--threads', '--cpu-autotune-min-threads',
                '--cpu-autotune-max-threads', '--bench-cpu-kernel', '--disable-cpu-autotune-threads'))
            observation = read(folder / 'observation.json')
            assert observation['initial_capacity_slots_available'] == [64, 64, 64]
            assert all(observation['vm_delta'][k] == 0 for k in ('pswpin', 'pswpout', 'oom_kill'))
            text = (folder / 'miner.log').read_text()
            hashes = [int(h) for h in re.findall(r'\bhashes=(\d+)', text)]
            assert hashes and hashes == sorted(hashes) and 'quarantined' not in text.lower()
            window = read(folder / 'productive-window.json')
            assert max(hashes) == window['completed_hashes_lower_bound']
            hps = max(hashes) / window['elapsed_start_request_through_stopped_seconds']
            assert math.isclose(hps, window['completed_hps_lower_bound'], rel_tol=1e-12)
            start = re.search(r'starting with (\d+) threads \(([^)]+)\)', text)
            assert start
            caches = {p.name: read(p) for p in folder.glob('tuning.json*') if p.is_file()}
            snapshots = read(folder / 'samples.json')
            confirmations = [s['time'] - window['observation_start_epoch'] for s in snapshots
                             if s['streaming_confirmations_seen'] > 0]
            result['runs'][label] = {'binary': binary, 'pair': pair, 'warm': warm,
                'completed_hps_lower_bound': hps, 'completed_hashes_lower_bound': max(hashes),
                'wall_seconds': window['elapsed_start_request_through_stopped_seconds'],
                'starting_threads': int(start[1]), 'starting_reason': start[2],
                'selected_threads': caches.get('tuning.json', {}).get('selected_threads'),
                'cpu_profile': caches['tuning.json']['profile'],
                'kernel_cache': caches.get('tuning.json.kernels.json'),
                'first_streaming_confirmation_observed_seconds': min(confirmations) if confirmations else None,
                'confirmation_observation_resolution_seconds': 10,
                'trajectory': [line for line in text.splitlines() if 'autotune' in line.lower() or 'cpu-kernel' in line.lower()],
                'log_sha256': manifest[label + '/miner.log'],
                'window_sha256': manifest[label + '/productive-window.json']}
    for binary, pair in expected_order:
        cold = result['runs'][f'joint-{binary}-{pair}']
        warm = result['runs'][f'joint-warm-{binary}-{pair}']
        warm['count_cache_restored'] = (cold['selected_threads'] is not None and
            warm['starting_threads'] == cold['selected_threads'] and warm['starting_reason'] == 'cached starting point')
        warm['kernel_restore_messages'] = [line for line in warm['trajectory'] if 'restoring confirmed' in line]
    for kind, prefix in (('cold', 'joint-'), ('warm', 'joint-warm-')):
        result[kind] = paired([PairedValue(str(pair),
            result['runs'][f'{prefix}control-{pair}']['completed_hps_lower_bound'],
            result['runs'][f'{prefix}candidate-{pair}']['completed_hps_lower_bound'],
            None, None) for pair in range(1, 5)], 'productive_completed_hps_lower_bound')
    fixed = out / 'fixed-streaming-control'
    assert (fixed / 'COMPLETE').exists()
    fixed_pairs = []
    for pair in range(1, 4):
        rates = []
        for role in ('baseline', 'candidate'):
            report = read(fixed / f'{pair}-{role}.json')
            checks = read(fixed / f'{pair}-{role}-checks.json')
            assert all(checks['delta'][k] == 0 for k in ('pswpin', 'pswpout', 'oom_kill'))
            assert report['cpu_threads'] == 32 and report['config_fingerprint']['cpu_kernel'] == 'avx512-256-stream'
            rates.append(sum(r['hashes'] for r in report['runs']) / sum(r['elapsed_secs'] for r in report['runs']))
        fixed_pairs.append(PairedValue(str(pair), *rates, None, None))
    result['fixed_streaming_build_control'] = paired(fixed_pairs, 'backend_completed_hps')
    result['numerical_gain_gate_passed'] = (
        result['cold']['comparison']['paired_geometric_delta_ci95_pct'][0] > 0 and
        result['warm']['comparison']['paired_geometric_delta_ci95_pct'][0] >= -2)
    result['landing_status'] = 'Requires trajectory/cache/reference/resource-lifecycle review; numerical gate alone does not authorize promotion.'
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('collected', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--resource-supplement', type=Path,
                        help='Separately collected resource check bound to the unchanged original failed fixture archive')
    args = parser.parse_args()
    report = analyze(args.collected, args.resource_supplement)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('cold', 'warm', 'numerical_gain_gate_passed')}, indent=2))
