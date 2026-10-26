#!/usr/bin/env python3
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from assess import assess, confirmed_streaming


def winner():
    return {'kernel': 'avx512-256-stream', 'candidate': 'avx512-256-stream',
            'context': 'fixture', 'samples': [
                {'hashes': hashes, 'secs': 10} for hashes in (100, 120, 100, 100, 120, 100)]}


class AssessmentTests(unittest.TestCase):
    def test_both_confirmation_cycles_must_pass(self):
        value = winner()
        self.assertTrue(confirmed_streaming(value))
        value['samples'][4]['hashes'] = 100
        self.assertFalse(confirmed_streaming(value))

    def test_drift_and_missing_samples_fail(self):
        value = winner()
        value['samples'][2]['hashes'] = 110
        self.assertFalse(confirmed_streaming(value))
        self.assertFalse(confirmed_streaming({**winner(), 'samples': winner()['samples'][:3]}))

    def fixture(self, root, *, confirmed=True, restored=True):
        out = root / 'results'
        out.mkdir()
        (out / 'reference-parity.log').write_text(
            '\n'.join(f'PASS nonce={i} full_size_bytes=2147483648 dirty_reuse=true guards=true'
                      for i in range(21)))
        (out / 'lifecycle').mkdir()
        (out / 'lifecycle/COMPLETE').touch()
        (out / 'outcome.json').write_text(json.dumps({'cleanup_failures': []}))
        (out / 'vm-checks.json').write_text(json.dumps({'pswpin': 0, 'pswpout': 0, 'oom_kill': 0}))
        (root / 'expected-binaries.json').write_text(json.dumps({'candidate': 'candidate-sha'}))
        name = 'joint-warm-candidate-a'
        (out / name).mkdir()
        (out / name / 'observation.json').write_text(json.dumps({
            'initial_capacity_slots_available': [24, 24, 24],
            'vm_delta': {'pswpin': 0, 'pswpout': 0, 'oom_kill': 0}}))
        return {'productive': {name: {
            'identity': {'binary_sha256': 'candidate-sha'}, 'cache_mode': 'warm',
            'window': {'completed_hps_lower_bound': 30}, 'starting_threads': 24,
            'caches': {'tuning.json': {'selected_threads': 24},
                       'tuning.json.kernels.json': {'winners': [winner()] if confirmed else []}},
            'count_cache_restored': restored,
            'kernel_cache_restore_messages': ['restoring confirmed avx512-256-stream'] if restored else [],
            'trajectory': []}}}

    def audit(self, root, result, **kwargs):
        # Only replace the shared raw-file auditor. The Genoa-specific parity,
        # resource, provenance and adoption checks execute against real files.
        module = SimpleNamespace(analyze=lambda _: copy.deepcopy(result))
        loader = SimpleNamespace(exec_module=lambda _: None)
        with patch('assess.importlib.util.spec_from_file_location', return_value=SimpleNamespace(loader=loader)), \
             patch('assess.importlib.util.module_from_spec', return_value=module):
            return assess(root, **kwargs)

    def test_failed_tuning_stays_rejected_when_export_is_requested(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self.fixture(root, confirmed=False, restored=False)
            with self.assertRaises(AssertionError):
                self.audit(root, result)
            checks = self.audit(root, result, include_rejected=True)['protocol_checks']
            self.assertFalse(checks['candidate_streaming_confirmed_and_restored'])
            self.assertEqual(len(checks['tuning_gate_failures']), 3)
            self.assertTrue(checks['landing_status'].startswith('Rejected:'))

    def test_rejection_export_does_not_bypass_parity_or_resource_failures(self):
        for failure in ('parity', 'resource', 'provenance'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                result = self.fixture(root)
                if failure == 'parity':
                    (root / 'results/reference-parity.log').write_text('')
                elif failure == 'resource':
                    (root / 'results/vm-checks.json').write_text(json.dumps(
                        {'pswpin': 0, 'pswpout': 0, 'oom_kill': 1}))
                else:
                    (root / 'expected-binaries.json').write_text(json.dumps({'candidate': 'wrong'}))
                with self.assertRaises(AssertionError):
                    self.audit(root, result, include_rejected=True)

    def test_passed_tuning_still_requires_performance_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self.fixture(root)
            checks = self.audit(root, result)['protocol_checks']
            self.assertEqual(checks['tuning_gate_failures'], [])
            self.assertTrue(checks['landing_status'].startswith('Await review'))


if __name__ == '__main__':
    unittest.main()
