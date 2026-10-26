"""Reject damaged benchmark evidence even when its cached hash is correct."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HEADER = '4e7d09682e0f5a4ebf111e22e0abfa80f6abeb070de3504ff2af2afd4ba71e8273f25c2c8b5d7fb6a09e1fa258e6cadce51e2cc79674b869faafd5283f6d1f55612c4c152d957d313de763848c01703a5f9164453245bd5330ac42a7'
# Full 2 GiB libargon2 reference, t=1, p=1, v19, nonce zero (little-endian).
HASH = '98ce9ad38671b77a33e370347f5eaf3b1170b66e367e1d4e41e0a7dfbfddaa24'


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        (self.path / 'cache.json').write_text(json.dumps({HEADER+':0': HASH}))
        self.work = {'header_base': HEADER, 'termination_reason': 'measurement_complete',
                     'measurement_start_seconds': 0, 'measurement_end_seconds': 1,
                     'measurement_duration_seconds': 1, 'protocol_errors': [],
                     'shares': [{'elapsed': 0.5, 'header_base': HEADER, 'user_work': True,
                                 'params': {'nonce': 0, 'claimed_hash': HASH, 'job_id': 'fixture'},
                                 'job': {'job_id': 'fixture', 'header_base': HEADER,
                                         'nonce_start': 0, 'nonce_end': 10}}]}

    def run_verifier(self, *arguments):
        work = self.path / 'work.json'
        work.write_text(json.dumps(self.work))
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('verify_pool_work.py')),
                                 str(work), '--cache', str(self.path / 'cache.json'), *arguments], capture_output=True, text=True)
        report = self.path / 'verification.json'
        return result.returncode, json.loads(report.read_text()) if report.exists() else None

    def test_reference_receipt_is_counted(self):
        code, report = self.run_verifier()
        self.assertEqual(code, 0)
        self.assertEqual(report['verified_unique_hps'], 1)
        self.assertEqual(report['verified_user_hps'], 1)

    def test_cache_only_needs_no_library_and_keeps_correctness_checks(self):
        arguments = ['--cache-only', '--reference-library', str(self.path / 'absent-library')]
        code, report = self.run_verifier(*arguments)
        self.assertEqual(code, 0)
        self.assertTrue(report['cache_only'])
        self.assertEqual(len(report['initial_cache_sha256']), 64)
        self.work['shares'][0]['params']['claimed_hash'] = '00'*32
        code, report = self.run_verifier(*arguments)
        self.assertEqual(code, 1)
        self.assertEqual(report['invalid'], 1)

    def test_cache_only_refuses_missing_values_without_writing_cache_or_receipt(self):
        cache = self.path / 'cache.json'
        cache.write_text('{}')
        code, report = self.run_verifier('--cache-only')
        self.assertEqual(code, 2)
        self.assertIsNone(report)
        self.assertEqual(cache.read_text(), '{}')

    def test_duplicate_never_inflates_throughput_or_passes(self):
        self.work['shares'].append(copy.deepcopy(self.work['shares'][0]))
        code, report = self.run_verifier()
        self.assertEqual(code, 1)
        self.assertEqual(report['verified_unique_hps'], 1)
        self.assertEqual(report['duplicates'], 1)

    def test_wrong_hash_fails(self):
        self.work['shares'][0]['params']['claimed_hash'] = '00'*32
        code, report = self.run_verifier()
        self.assertEqual(code, 1)
        self.assertEqual(report['verified_unique_hps'], 0)

    def test_wrong_job_or_header_or_nonce_window_fails(self):
        original = copy.deepcopy(self.work)
        for change in [{'job_id': 'other'}, {'header_base': '00'*92}, {'nonce_start': 1}]:
            with self.subTest(change=change):
                self.work = copy.deepcopy(original)
                self.work['shares'][0]['job'].update(change)
                self.assertEqual(self.run_verifier()[0], 1)

    def test_incomplete_measurement_fails_even_with_valid_hash(self):
        self.work['termination_reason'] = 'miner_exited'
        self.assertEqual(self.run_verifier()[0], 1)

    def test_protocol_error_fails(self):
        self.work['protocol_errors'] = [{'error': 'fixture connection failed'}]
        self.assertEqual(self.run_verifier()[0], 1)

    def test_boolean_nonce_is_not_an_integer_nonce(self):
        self.work['shares'][0]['params']['nonce'] = False
        self.assertNotEqual(self.run_verifier()[0], 0)

    def test_invalid_measurement_bounds_fail(self):
        self.work['measurement_end_seconds'] = 2
        self.assertNotEqual(self.run_verifier()[0], 0)

    def test_late_receipts_and_fee_work_do_not_count_as_user_work(self):
        self.work['shares'][0]['user_work'] = False
        self.assertEqual(self.run_verifier()[1]['verified_user_hps'], 0)
        self.work['shares'][0]['elapsed'] = 1
        self.assertEqual(self.run_verifier()[1]['verified_unique_hps'], 0)

    def test_valid_hash_on_superseded_job_is_not_useful(self):
        self.work['shares'][0].update(stale=True, eligible=False, job_retired_elapsed=0.4)
        code, report = self.run_verifier()
        self.assertEqual(code, 0)
        self.assertEqual(report['verified_unique_hps'], 1)
        self.assertEqual(report['verified_user_hps'], 0)
        self.assertEqual(report['verified_rejected_in_window'], 1)

    def test_superseded_work_counts_only_within_explicit_grace(self):
        self.work['stale_grace_seconds'] = 0.2
        self.work['shares'][0].update(stale=True, eligible=True, job_retired_elapsed=0.4)
        self.assertEqual(self.run_verifier()[1]['verified_user_hps'], 1)
        self.work['shares'][0]['elapsed'] = 0.7
        self.assertEqual(self.run_verifier()[0], 1, 'Receiver cannot count work beyond its stated grace')

    def test_unknown_job_never_passes_with_correct_hash(self):
        self.work['shares'][0].update(job=None, eligible=False)
        self.assertEqual(self.run_verifier()[0], 1)


if __name__ == '__main__':
    unittest.main()
