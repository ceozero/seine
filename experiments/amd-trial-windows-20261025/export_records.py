#!/usr/bin/python3
"""Export fully audited short-sample observations, preserving acceptance scope."""
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

from analyze import analyze

BASE = Path(__file__).resolve().parents[1] / 'amd-overnight-20261025'
spec = importlib.util.spec_from_file_location('ordering_records', BASE / 'export_records.py')
ordering_records = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ordering_records)


def apply_review(analysis, manifest_bytes, review):
    assert review['decision'] in ('accept_short_samples', 'reject_short_samples')
    assert review['result_manifest_sha256'] == hashlib.sha256(manifest_bytes).hexdigest()
    for key in ('binary_provenance', 'resource_validation', 'raw_decision_audit', 'evidence'):
        # Reviews are JSON files: tuples become arrays and histogram keys become
        # strings. Compare their persisted representation without dropping fields.
        assert json.loads(json.dumps(review[key])) == json.loads(json.dumps(analysis[key])), key
    for phase in ('cold', 'warm', 'fixed_streaming_build_control'):
        assert review[phase + '_comparison'] == analysis[phase]['comparison'], phase
    assert review['rationale'].strip()
    accepted = review['decision'] == 'accept_short_samples'
    assert not accepted or analysis['numerical_gain_gate_passed']
    analysis['landing_status'] = (
        'Accepted high-count short samples for AMD family 1Ah/model 02h'
        if accepted else 'Rejected high-count short-sample experiment')


def records(analysis):
    assert analysis['experiment'] == 'amd-trial-windows-20261025'
    result = ordering_records.records(analysis)
    for row in result['records']:
        row['id'] = f"turin-short-samples-{row['phase']}-{row['role']}"
        row['campaign'] = analysis['experiment']
        row['source'] = f"experiments/{analysis['experiment']}/results.json"
        row['sample_policy'] = ('turin-10s-256-v1' if row['role'] == 'candidate'
                                else 'original-30s-32')
        row['measurement_instrumentation'] = 'Both builds log exact kernel-trial hashes and durations; not a shipping policy change.'
        row['evidence_archive_sha256'] = analysis['evidence']['archive_sha256']
        for observation in row['observations']:
            prefix = 'joint-warm-' if row['phase'] == 'cached_restart' else 'joint-'
            label = f"{prefix}{row['role']}-{observation['pair']}"
            audit = analysis['raw_decision_audit'][label]
            observation['decision_count'] = audit['decision_count']
            observation['promotion_count'] = audit['promotion_count']
            observation['early_samples'] = audit['early_samples']
            observation['sample_duration_seconds_histogram'] = audit['sample_duration_seconds_histogram']
    result['description'] = 'Automatic productive-tuning observations comparing high-count sample policies; explicitly provisioned HugeTLB pages.'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('collected', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--review', type=Path)
    args = parser.parse_args()
    analysis = analyze(args.collected)
    if args.review:
        apply_review(analysis, (args.collected / 'results/manifest.json').read_bytes(),
                     json.loads(args.review.read_text()))
    result = records(analysis)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'benchmark-records.json').write_text(json.dumps(result, indent=2) + '\n')
    columns = ('id', 'hardware', 'phase', 'role', 'selection', 'cpu_profile', 'sample_policy',
        'page_mode', 'metric_scope', 'source_revision', 'binary_sha256', 'repetitions',
        'requested_seconds', 'completed_hashes_lower_bound', 'invocation_seconds', 'hps',
        'hps_is_lower_bound', 'hps_sample_cv', 'power_scope', 'power_cap_w', 'package_watts',
        'candidate_status', 'evidence_archive_sha256')
    with (args.output / 'benchmark-records.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction='ignore', lineterminator='\n')
        writer.writeheader()
        writer.writerows(result['records'])


if __name__ == '__main__':
    main()
