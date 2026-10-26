#!/usr/bin/env python3
"""Exercise matrix evidence rejection and completed-hash accounting."""
import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest

import analyze_cpu_architecture as analyzer


class MatrixEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'large-t1'
        self.path.mkdir()
        self.experiment = {'pairs': 4, 'rounds': 2, 'warmup_rounds': 1,
                           'seconds': 12, 'comparison': 'avx2-vs-avx512'}
        backend = {key: 0 for key in ('dropped_events', 'assignment_enqueue_timeouts',
                   'assignment_execution_timeouts', 'control_enqueue_timeouts',
                   'control_execution_timeouts', 'memory_allocation_failures')}
        backend.update(memory_explicit_large_workers=1, memory_explicit_large_bytes=2 * 1024**3)
        base = {'schema_version': 14, 'rounds': 2, 'warmup_rounds': 1, 'bench_secs': 12,
                'cpu_threads': 1, 'avg_hps': 1.5, 'pow_fingerprint': {'m': 2097152},
                'environment': {'build_rustflags': '', 'cpu_identity': {'family': 25},
                                'cpu_brand': 'test CPU', 'source_fingerprint': 'same-source'},
                'config_fingerprint': {'cpu_autotune_threads': False, 'cpu_affinity': 'os',
                                       'cpu_page_mode': 'large', 'cpu_kernel': 'avx2',
                                       'cpu_kernel_requested': 'avx2'},
                'runs': [{'hashes': 24, 'actual_elapsed_secs': 12, 'fence_secs': 0.5,
                          'backend_runs': [backend]} for _ in range(2)]}
        with (self.path / 'results.tsv').open('w') as handle:
            writer = csv.DictWriter(handle, fieldnames=['pair', 'variant', 'report'], delimiter='\t')
            writer.writeheader()
            for pair in range(1, 5):
                for variant in ('baseline', 'candidate'):
                    r = copy.deepcopy(base)
                    if variant == 'candidate':
                        r['config_fingerprint'].update(cpu_kernel='avx512', cpu_kernel_requested='avx512')
                        r['avg_hps'] = 2
                        for sample in r['runs']: sample['hashes'] = 36
                    name = f'{variant}_pair{pair}.json'
                    (self.path / name).write_text(json.dumps(r))
                    writer.writerow({'pair': pair, 'variant': variant, 'report': '/remote/' + name})
        (self.path.parent / 'large-t1-checks.json').write_text(json.dumps({
            'delta': {'pswpin': 0, 'pswpout': 0, 'oom_kill': 0}, 'steal_pct': 0}))

    def change_candidate(self, edit):
        p = self.path / 'candidate_pair1.json'
        r = json.loads(p.read_text())
        edit(r)
        p.write_text(json.dumps(r))

    def test_completed_accounting_includes_late_hashes(self):
        result = analyzer.summarize_trial(self.path, self.experiment)
        m = result['metrics']['completed_hps']
        self.assertEqual(m['baseline_mean'], 2)
        self.assertEqual(m['candidate_mean'], 3)
        self.assertEqual(m['paired_bootstrap_95_pct'], [50, 50])
        self.assertAlmostEqual(result['metrics']['counted_hps']['ratio_of_means_delta_pct'], 100 / 3)

    def test_missing_timeout_telemetry_fails_closed(self):
        self.change_candidate(lambda r: r['runs'][0]['backend_runs'][0].pop('control_execution_timeouts'))
        with self.assertRaises(KeyError): analyzer.summarize_trial(self.path, self.experiment)

    def test_page_fallback_is_rejected(self):
        self.change_candidate(lambda r: r['runs'][0]['backend_runs'][0].update(memory_explicit_large_bytes=0))
        with self.assertRaises(AssertionError): analyzer.summarize_trial(self.path, self.experiment)

    def test_matching_reports_with_wrong_page_mode_are_rejected(self):
        for p in self.path.glob('*_pair*.json'):
            report = json.loads(p.read_text())
            report['config_fingerprint']['cpu_page_mode'] = 'regular'
            for run in report['runs']:
                for backend in run['backend_runs']:
                    backend['memory_regular_workers'] = 1
                    backend['memory_regular_bytes'] = 2 * 1024**3
            p.write_text(json.dumps(report))
        with self.assertRaises(AssertionError): analyzer.summarize_trial(self.path, self.experiment)

    def test_missing_measured_round_is_rejected(self):
        self.change_candidate(lambda r: r['runs'].pop())
        with self.assertRaises(AssertionError): analyzer.summarize_trial(self.path, self.experiment)

    def test_wrong_kernel_is_rejected(self):
        self.change_candidate(lambda r: r['config_fingerprint'].update(cpu_kernel='avx2'))
        with self.assertRaises(AssertionError): analyzer.summarize_trial(self.path, self.experiment)

    def test_cross_binary_isa_comparison_is_rejected(self):
        self.change_candidate(lambda r: r['environment'].update(source_fingerprint='different-source'))
        with self.assertRaises(AssertionError): analyzer.summarize_trial(self.path, self.experiment)

    def test_unused_auto_cap_does_not_change_fixed_worker_comparison(self):
        self.change_candidate(lambda r: r['config_fingerprint'].update(cpu_auto_threads_cap=6))
        self.assertEqual(analyzer.summarize_trial(self.path, self.experiment)['threads'], 1)

    def test_actual_worker_count_mismatch_is_rejected(self):
        self.change_candidate(lambda r: r.update(cpu_threads=4))
        with self.assertRaises(AssertionError): analyzer.summarize_trial(self.path, self.experiment)

    def test_cross_host_comparison_is_rejected(self):
        self.change_candidate(lambda r: r['environment'].update(cpu_identity={'family': 26}))
        with self.assertRaises(AssertionError): analyzer.summarize_trial(self.path, self.experiment)


if __name__ == '__main__':
    unittest.main()
