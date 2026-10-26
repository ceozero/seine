#!/usr/bin/python3
"""Audit full productive windows, exact tuning decisions and real reclaim evidence."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

from audit_decisions import audit
sys.path.append(str(Path(__file__).resolve().parents[1] / 'amd-overnight-20261025'))
from analyze_productive import analyze as productive_analysis
from audit_resource import audit_samples, verify_archive


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_windows(root, runs):
    """Enforce actual durations, own-cache paths and observed interleaving."""
    order = [(role, pair) for pair in range(1, 5)
             for role in (('control', 'candidate') if pair % 2 else ('candidate', 'control'))]
    labels = [f'joint-{role}-{pair}' for role, pair in order]
    labels += [f'joint-warm-{role}-{pair}' for role, pair in reversed(order)]
    assert set(runs) == set(labels), 'all sixteen original windows are required'
    previous_end = None
    for label in labels:
        run = runs[label]
        folder = root / 'results' / label
        identity = read(folder / 'identity.json')
        window = read(folder / 'productive-window.json')
        warm = run['warm']
        seconds = 180 if warm else 1200
        elapsed = window['elapsed_start_request_through_stopped_seconds']
        start = window['observation_start_epoch']
        assert math.isfinite(elapsed) and elapsed >= seconds, 'shortened window: ' + label
        assert math.isfinite(start) and start > 0
        assert previous_end is None or start >= previous_end, 'overlap or wrong execution order: ' + label
        previous_end = start + elapsed
        remote = Path(identity['binary']).parent
        assert Path(identity['binary']).name == run['binary']
        expected_cache = str(remote / 'results' / f"joint-{run['binary']}-{run['pair']}") if warm else None
        assert identity['cache_source'] == expected_cache, 'foreign cache source: ' + label
        assert not warm or run['count_cache_restored'], 'own count cache not restored: ' + label
        assert run['cpu_profile'] == 'balanced'
        command = read(folder / 'command.json')
        for flag, value in (('--backend', 'cpu'), ('--cpu-page-mode', 'large'),
                            ('--cpu-affinity', 'auto'),
                            ('--cpu-autotune-config', str(remote / 'results' / label / 'tuning.json')),
                            ('--data-dir', str(remote / 'results' / label / 'config'))):
            assert command.count(flag) == 1 and command[command.index(flag) + 1] == value, label
        prohibited = ('--threads', '--cpu-autotune-min-threads', '--cpu-autotune-max-threads',
                      '--bench-cpu-kernel', '--disable-cpu-autotune-threads', '--cpu-profile')
        assert not any(argument.split('=', 1)[0] in prohibited for argument in command), label


def analyze(root):
    archive = root.parent / 'productive-evidence.tar.gz'
    verified = verify_archive(root, archive)
    receipt = read(root.parent / 'collection-verification.json')
    assert receipt['ready_for_followup'] and receipt['verified_manifest_entries'] == verified
    assert receipt['archive_sha256'] == digest(archive)
    result = productive_analysis(root)
    frozen = read(Path(__file__).resolve().parent / 'frozen-builds.json')
    protocol = read(root / 'results/protocol.json')
    assert protocol['binary_sha256'] == {
        role: frozen[role]['binary_sha256'] for role in ('control', 'candidate')}
    validate_windows(root, result['runs'])
    result['experiment'] = 'amd-trial-windows-20261025'
    decisions = {}
    for label, run in result['runs'].items():
        is_candidate = run['binary'] == 'candidate'
        text = (root / 'results' / label / 'miner.log').read_text()
        decision = audit(text, short_trials=is_candidate)
        configuration = run['kernel_cache']['configuration']
        assert (';sample_policy=turin-10s-256-v1' in configuration) == is_candidate
        if not run['warm']:
            assert decision['decision_count'] > 0, label
            if is_candidate:
                assert decision['early_samples'] > 0, 'candidate did not exercise short sampling: ' + label
        decisions[label] = decision
    result['raw_decision_audit'] = decisions
    folder = root / 'results/lifecycle'
    prefix = 'seine-short-windows-lifecycle-'
    samples = {role: read(folder / (prefix + role + '.service-samples.json'))
               for role in ('first', 'restart', 'optout')}
    logs = {role: (folder / (prefix + role + '.service.log')).read_text() for role in samples}
    resource = audit_samples(samples['first'], samples['restart'], samples['optout'],
        read(folder / 'seed-before-restart.json'), read(folder / 'seed-during-constrained-restart.json'), logs)
    resource['raw_kernel_decisions'] = {
        role: audit(text, short_trials=True) for role, text in logs.items()}
    resource['reclaim_helper_exit'] = read(folder / 'reclaim-load-exit.json')
    assert resource['reclaim_helper_exit']['exit_code'] is not None
    helpers = read(root / 'helper-provenance.json')
    assert helpers['lifecycle.py']['prepared_sha256'] == digest(root / 'lifecycle.py')
    assert helpers['reclaim_load.py']['prepared_sha256'] == digest(root / 'reclaim_load.py')
    resource['status'] = 'COMPLETE_WITH_MEASURED_RECLAIM'
    result['resource_validation'] = resource
    vm = read(root / 'results/vm-checks.json')
    assert all(vm[key] == 0 for key in ('pswpin', 'pswpout', 'oom_kill'))
    result['numerical_gain_gate_passed'] = (
        result['cold']['comparison']['paired_geometric_delta_ci95_pct'][0] > 1 and
        result['warm']['comparison']['paired_geometric_delta_ci95_pct'][0] >= -2)
    result['landing_status'] = 'Pending manual review of full native evidence; no automatic acceptance.'
    result['evidence'] = {'archive_sha256': receipt['archive_sha256'], 'verified_entries': verified,
        'manifest_sha256': digest(root / 'results/manifest.json'),
        'expected_files_sha256': digest(root / 'expected-files.json'), 'raw_evidence_private': True}
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('collected', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = analyze(args.collected)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key]['comparison'] for key in ('cold', 'warm', 'fixed_streaming_build_control')}, indent=2))
