#!/usr/bin/env python3
"""Audit the frozen Genoa protocol; numerical results still need human review."""
import argparse
import importlib.util
import json
from pathlib import Path


def confirmed_streaming(winner):
    if winner['kernel'] != 'avx512-256-stream' or winner['candidate'] != winner['kernel']:
        return False
    samples = winner['samples']
    if len(samples) != 6 or not all(s['hashes'] > 0 and s['secs'] > 0 for s in samples):
        return False
    for offset in (0, 3):
        a, b, c = samples[offset:offset + 3]
        drift = abs((c['hashes'] / c['secs']) / (a['hashes'] / a['secs']) - 1)
        baseline = (a['hashes'] + c['hashes']) / (a['secs'] + c['secs'])
        margin = sum(1 / s['secs'] for s in (a, b, c))
        if drift > 0.05 or b['hashes'] / b['secs'] <= baseline * 1.02 + margin:
            return False
    return True


def tuning_failures(name, run, confirmed):
    """Report adoption failures separately from corrupted/incomplete evidence."""
    failures = []
    warm = run['cache_mode'] == 'warm'
    if warm and not run['count_cache_restored']:
        failures.append(name + ': count cache was not restored')
    if 'candidate' in name:
        if not confirmed:
            failures.append(name + ': no repeated streaming confirmation')
        if warm:
            if not any('avx512-256-stream' in line
                       for line in run['kernel_cache_restore_messages']):
                failures.append(name + ': streaming cache was not restored')
        elif not any('confirmed faster avx512-256-stream' in line
                     for line in run['trajectory']):
            failures.append(name + ': no cold streaming confirmation message')
    return failures


def assess(root, *, include_rejected=False):
    source = Path(__file__).resolve().parents[1] / 'cpu-followups-20261025/analyze.py'
    spec = importlib.util.spec_from_file_location('native_analysis', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.analyze(root)
    out = root / 'results'
    parity = (out / 'reference-parity.log').read_text().splitlines()
    passes = [line for line in parity if line.startswith('PASS nonce=')]
    assert len(passes) == 21
    assert all('full_size_bytes=2147483648 dirty_reuse=true guards=true' in line for line in passes)
    assert (out / 'lifecycle/COMPLETE').exists()
    assert json.loads((out / 'outcome.json').read_text())['cleanup_failures'] == []
    assert all(json.loads((out / 'vm-checks.json').read_text())[key] == 0
               for key in ('pswpin', 'pswpout', 'oom_kill'))
    expected = json.loads((root / 'expected-binaries.json').read_text())
    findings, failures = {}, []
    for name, run in result['productive'].items():
        binary = 'candidate' if 'candidate' in name else 'control'
        assert run['identity']['binary_sha256'] == expected[binary], name
        observation = json.loads((out / name / 'observation.json').read_text())
        assert observation['initial_capacity_slots_available'][0] == 24
        assert observation['initial_capacity_slots_available'][-1] == 24
        assert all(observation['vm_delta'][key] == 0 for key in ('pswpin', 'pswpout', 'oom_kill'))
        winners = run['caches'].get('tuning.json.kernels.json', {}).get('winners', [])
        confirmed = [w for w in winners if confirmed_streaming(w)]
        findings[name] = {
            'completed_hps_lower_bound': run['window']['completed_hps_lower_bound'],
            'starting_threads': run['starting_threads'],
            'selected_threads': run['caches'].get('tuning.json', {}).get('selected_threads'),
            'confirmed_streaming_contexts': [w['context'] for w in confirmed],
        }
        failures.extend(tuning_failures(name, run, confirmed))
    assert include_rejected or not failures, '; '.join(failures)
    result['protocol_checks'] = {
        'parity_transitions': len(passes),
        'resource_lifecycle_passed': True,
        'candidate_streaming_confirmed_and_restored': not failures,
        'tuning_gate_failures': failures,
        'landing_status': ('Rejected: tuning confirmation/cache gate failed' if failures else
            'Await review of paired productive rates and fixed-kernel build controls'),
        'runs': findings,
    }
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('collected', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--include-rejected', action='store_true',
                        help='Preserve valid measurements with failed tuning gates; never authorize landing')
    args = parser.parse_args()
    report = assess(args.collected, include_rejected=args.include_rejected)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ('cold', 'warm', 'protocol_checks')}, indent=2))
