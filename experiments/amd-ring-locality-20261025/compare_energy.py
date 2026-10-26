#!/usr/bin/env python3
"""Compare frozen ring binaries without weakening the normal power comparator."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import bench_cpu_energy as energy
from benchctl import PairedValue, summarize_pairs, DEFAULT_BOOTSTRAP_SAMPLES, DEFAULT_BOOTSTRAP_SEED


def compare(root, binary_sha256, workers):
    if workers not in (32, 64) or set(binary_sha256) != {'baseline', 'candidate'}:
        raise energy.EnergyError('invalid frozen comparison identities')
    if len(set(binary_sha256.values())) != 2:
        raise energy.EnergyError('cross-build experiment requires two distinct binaries')
    metrics = ('invocation_joules_per_completed_hash',
               'invocation_completed_hashes_per_second', 'average_package_watts')
    pairs = {metric: [] for metric in metrics}
    common_context, identities, observations = None, {}, []
    for pair in range(1, 5):
        measured = {}
        for role in ('baseline', 'candidate'):
            label = f'pair-{pair:02d}-{role}'
            folder = root / label
            record, report = energy.load_measurement(folder)
            if record['binary_sha256'] != binary_sha256[role]:
                raise energy.EnergyError('unexpected binary identity: ' + label)
            cap = json.loads((root / (label + '-cap.json')).read_text())
            if cap != {'before_uw': 280_000_000, 'after_uw': 280_000_000, 'requested_uw': 280_000_000}:
                raise energy.EnergyError('stock power cap changed: ' + label)
            fp, env = report['config_fingerprint'], report['environment']
            if (report['cpu_threads'] != workers or report['rounds'] != 1 or report['bench_secs'] != 120
                    or fp['cpu_page_mode'] != 'large' or fp['cpu_affinity'] != 'auto'
                    or fp['cpu_kernel'] != 'avx512-256-stream'):
                raise energy.EnergyError('ring protocol differs: ' + label)
            pre, post = record['context_before'], record['context_after']
            fixed = {key: record[key] for key in ('domains', 'max_domain_watts_assumption')}
            for key in ('boot_id', 'allowed_cpus', 'frequency_policies', 'power_constraints'):
                if pre[key] != post[key]:
                    raise energy.EnergyError('context changed during invocation: ' + key)
                fixed[key] = pre[key]
            if any(pre['vmstat'][key] != post['vmstat'][key]
                   for key in ('pswpin', 'pswpout', 'oom_kill')):
                raise energy.EnergyError('swap or OOM activity: ' + label)
            fixed.update({key: report[key] for key in ('schema_version', 'bench_kind',
                'pow_fingerprint', 'config_fingerprint', 'cpu_threads', 'rounds', 'bench_secs')})
            fixed['hardware'] = {key: env[key] for key in ('cpu_identity', 'cpu_brand',
                'cpu_arch', 'logical_cores', 'physical_cores', 'total_memory_bytes',
                'runtime_environment', 'os', 'kernel_version')}
            # Only source/build fingerprints and timestamps may differ. Compiler,
            # features and optimization flags remain controlled across variants.
            fixed['toolchain'] = {key: env[key] for key in ('target_triple', 'build_profile',
                'build_opt_level', 'build_rustflags', 'build_features', 'rustc_version')}
            identity = {key: env[key] for key in ('git_commit', 'source_fingerprint', 'build_fingerprint')}
            if role in identities and identities[role] != identity:
                raise energy.EnergyError('source identity changed within one build')
            identities[role] = identity
            if common_context is None:
                common_context = fixed
            if fixed != common_context:
                differing = [key for key in fixed if fixed[key] != common_context[key]]
                raise energy.EnergyError('cross-build settings changed: ' + ', '.join(differing))
            measured[role] = record
            observations.append({'pair': pair, 'role': role, 'directory': label,
                'energy_sha256': energy.sha256(folder / 'energy.json'),
                'benchmark_sha256': record['benchmark_sha256'],
                'binary_sha256': record['binary_sha256'],
                'completed_hashes': record['completed_hashes'],
                'invocation_seconds': record['invocation_secs'],
                'package_joules': record['total_package_joules']})
        for metric in metrics:
            pairs[metric].append(PairedValue(str(pair), measured['baseline'][metric],
                                            measured['candidate'][metric], None, None))
    summaries = {}
    for metric, values in pairs.items():
        summary = summarize_pairs(values, metric, DEFAULT_BOOTSTRAP_SAMPLES, DEFAULT_BOOTSTRAP_SEED)
        signs = summary['comparison']['sign_consistency']
        signs['candidate_higher_pairs'] = signs.pop('candidate_faster_pairs')
        signs['candidate_lower_pairs'] = signs.pop('candidate_slower_pairs')
        signs['candidate_higher_fraction'] = signs.pop('candidate_faster_fraction')
        signs['dominant_sign'] = {'candidate_faster': 'candidate_higher',
            'candidate_slower': 'candidate_lower', 'mixed': 'mixed'}[signs['dominant_sign']]
        summaries[metric] = summary
    return {'schema': 'seine-ring-energy-comparison/v1',
        'scope': 'whole_invocation_package_energy', 'binary_sha256': binary_sha256,
        'source_identities': identities, 'workers': workers, 'observations': observations,
        'metrics': summaries,
        'interpretation': 'Cross-build fixed-count comparison. Package energy includes allocation and teardown; excludes unmeasured DRAM and wall losses. Four within-host pairs do not establish architecture-wide gains.'}
