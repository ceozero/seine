#!/usr/bin/python3
import copy
import hashlib
import importlib.util
import json
import unittest

from audit_decisions import audit
from export_records import BASE, apply_review, records

spec = importlib.util.spec_from_file_location('ordering_record_tests', BASE / 'test_export_records.py')
base_tests = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base_tests)


def fixture():
    data = base_tests.fixture()
    data['experiment'] = 'amd-trial-windows-20261025'
    data['evidence'] = {'archive_sha256': 'archive', 'verified_entries': 1}
    data['raw_decision_audit'] = {}
    for run in data['runs'].values():
        prefix = 'joint-warm-' if run['warm'] else 'joint-'
        data['raw_decision_audit'][f"{prefix}{run['binary']}-{run['pair']}"] = {
            'decision_count': 2, 'promotion_count': 1, 'early_samples': 6,
            'sample_duration_seconds_histogram': {10: 6}}
    for phase in ('cold', 'warm', 'fixed_streaming_build_control'):
        data[phase] = {'comparison': {'paired_geometric_delta_pct': 0.5}}
    review = {key: copy.deepcopy(data[key]) for key in
              ('binary_provenance', 'resource_validation', 'raw_decision_audit', 'evidence')}
    review.update(decision='accept_short_samples', rationale='Synthetic test review.',
                  result_manifest_sha256=hashlib.sha256(b'evidence').hexdigest())
    for phase in ('cold', 'warm', 'fixed_streaming_build_control'):
        review[phase + '_comparison'] = copy.deepcopy(data[phase]['comparison'])
    return data, review


class ExportTests(unittest.TestCase):
    def test_saved_raw_review_roundtrips_and_still_rejects_changed_samples(self):
        data, review = fixture()
        data['numerical_gain_gate_passed'] = True
        raw = audit('cpu-autotune | keeping current kernel; no confirmed gain '
                    'raw_hashes_secs=[600/10,500/10,600/10]', short_trials=True)
        data['resource_validation']['raw_kernel_decisions'] = {'first': raw}
        data['raw_decision_audit'] = {'example': raw}
        for key in ('resource_validation', 'raw_decision_audit'):
            review[key] = copy.deepcopy(data[key])
        saved = json.loads(json.dumps(review))
        apply_review(data, b'evidence', saved)
        saved['resource_validation']['raw_kernel_decisions']['first']['decisions'][0][
            'samples_hashes_seconds'][0][0] += 1
        with self.assertRaisesRegex(AssertionError, 'resource_validation'):
            apply_review(data, b'evidence', saved)

    def test_acceptance_requires_gain_and_binds_raw_audit_and_archive(self):
        data, review = fixture()
        with self.assertRaises(AssertionError):
            apply_review(data, b'evidence', review)
        data['numerical_gain_gate_passed'] = True
        apply_review(data, b'evidence', review)
        self.assertTrue(data['landing_status'].startswith('Accepted'))
        for key in ('raw_decision_audit', 'evidence'):
            changed = copy.deepcopy(review)
            changed[key] = {}
            with self.assertRaises(AssertionError):
                apply_review(data, b'evidence', changed)
        with self.assertRaises(AssertionError):
            apply_review(data, b'changed manifest', review)

    def test_rejection_keeps_negative_results_exportable(self):
        data, review = fixture()
        review['decision'] = 'reject_short_samples'
        apply_review(data, b'evidence', review)
        result = records(data)
        self.assertEqual(len(result['records']), 4)
        for row in result['records']:
            self.assertTrue(row['candidate_status'].startswith('Rejected'))
            self.assertEqual(row['hps'], 30)
            self.assertTrue(row['hps_is_lower_bound'])
            self.assertIsNone(row['package_watts'])
            self.assertEqual(row['evidence_archive_sha256'], 'archive')
            self.assertEqual(row['observations'][0]['early_samples'], 6)
            self.assertNotIn('amd-overnight', row['source'])
            self.assertTrue(row['id'].startswith('turin-short-samples-'))

    def test_missing_pair_or_decision_evidence_cannot_export(self):
        data, _ = fixture()
        del data['runs']['False-control-4']
        with self.assertRaises(AssertionError):
            records(data)
        data, _ = fixture()
        data['raw_decision_audit'] = {}
        with self.assertRaises(KeyError):
            records(data)


if __name__ == '__main__':
    unittest.main()
