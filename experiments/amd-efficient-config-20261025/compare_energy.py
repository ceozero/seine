#!/usr/bin/env python3
"""Compare combined page/power operating points with verified package energy."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import bench_cpu_energy as energy
from benchctl import PairedValue, summarize_pairs, DEFAULT_BOOTSTRAP_SAMPLES, DEFAULT_BOOTSTRAP_SEED


PAGE_MODES = {'baseline': 'large', 'candidate': 'large-1g'}
POWER_CAPS_UW = {'baseline': 280_000_000, 'candidate': 240_000_000}


def expected_pool_state(mode):
    return {page: {'total': count, 'free': count, 'reserved': 0, 'surplus': 0}
            for page, count in (('large', 65536 if mode == 'large' else 0),
                                ('large-1g', 128 if mode == 'large-1g' else 0))}


def compare(root, binary_sha256, workers=64):
    if workers != 64 or not isinstance(binary_sha256, str) or len(binary_sha256) != 64:
        raise energy.EnergyError('combined operating-point protocol requires 64 workers and one frozen binary')
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
            if record['binary_sha256'] != binary_sha256:
                raise energy.EnergyError('unexpected binary identity: ' + label)
            cap = json.loads((root / (label + '-cap.json')).read_text())
            expected_cap = POWER_CAPS_UW[role]
            if cap != {'before_uw': expected_cap, 'after_uw': expected_cap, 'requested_uw': expected_cap}:
                raise energy.EnergyError('requested power cap changed: ' + label)
            mode = PAGE_MODES[role]
            pools = json.loads((root / (label + '-pools.json')).read_text())
            if pools != {'mode': mode, 'before': expected_pool_state(mode), 'after': expected_pool_state(mode)}:
                raise energy.EnergyError('page pools differ from protocol: ' + label)
            fp, env = report['config_fingerprint'], report['environment']
            cpu = env['cpu_identity']
            if (cpu.get('vendor'), cpu.get('family'), cpu.get('model')) != ('AuthenticAMD', 26, 2):
                raise energy.EnergyError('unexpected hardware identity: ' + label)
            if (report['cpu_threads'] != workers or report['rounds'] != 1 or report['bench_secs'] != 120
                    or fp['cpu_page_mode'] != mode or fp['cpu_affinity'] != 'auto'
                    or fp['cpu_kernel'] != 'avx512-256-stream'):
                raise energy.EnergyError('combined operating-point protocol differs: ' + label)
            window = report['runs'][0]
            if not (window['configured_secs'] == 120 <= window['actual_elapsed_secs']
                    <= window['elapsed_secs'] <= record['invocation_secs']):
                raise energy.EnergyError('incomplete or inconsistent 120-second window: ' + label)
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
            fixed['config_fingerprint'] = {key: value for key, value in fp.items() if key != 'cpu_page_mode'}
            fixed['hardware'] = {key: env[key] for key in ('cpu_identity', 'cpu_brand',
                'cpu_arch', 'logical_cores', 'physical_cores', 'total_memory_bytes',
                'runtime_environment', 'os', 'kernel_version')}
            # Page mode and independently checked HSMP cap may vary. The executable,
            # source and complete build identity must also agree across roles.
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
                raise energy.EnergyError('settings other than page mode changed: ' + ', '.join(differing))
            measured[role] = record
            observations.append({'pair': pair, 'role': role, 'directory': label,
                'energy_sha256': energy.sha256(folder / 'energy.json'),
                'benchmark_sha256': record['benchmark_sha256'],
                'binary_sha256': record['binary_sha256'], 'page_mode': mode,
                'power_cap_w': expected_cap / 1_000_000,
                'completed_hashes': record['completed_hashes'],
                'invocation_seconds': record['invocation_secs'],
                'package_joules': record['total_package_joules']})
        for metric in metrics:
            pairs[metric].append(PairedValue(str(pair), measured['baseline'][metric],
                                            measured['candidate'][metric], None, None))
    if identities['baseline'] != identities['candidate']:
        raise energy.EnergyError('same binary has inconsistent source/build identities')
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
    return {'schema': 'seine-efficient-config-energy-comparison/v1', 'page_modes': PAGE_MODES, 'power_caps_uw': POWER_CAPS_UW,
        'scope': 'whole_invocation_package_energy', 'binary_sha256': binary_sha256,
        'source_identities': identities, 'workers': workers, 'observations': observations,
        'metrics': summaries,
        'interpretation': 'Same-binary combined configuration comparison at 64 workers: 2 MiB/280 W versus 1 GiB/240 W. Neither factor is isolated. Package energy includes allocation and teardown; excludes unmeasured DRAM and wall losses. Four within-host pairs do not establish architecture-wide gains.'}
