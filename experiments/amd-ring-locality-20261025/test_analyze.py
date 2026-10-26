import copy
import unittest

from analyze import report_rate


def fixture():
    backend = {'hashes': 1000, 'memory_explicit_large_workers': 32,
        'memory_explicit_large_bytes': 32 * 2 * 1024**3}
    for field in ('memory_allocation_failures', 'dropped_events', 'assignment_enqueue_timeouts',
                  'assignment_execution_timeouts', 'control_enqueue_timeouts', 'control_execution_timeouts'):
        backend[field] = 0
    for backing in ('explicit_large_1g', 'transparent_huge', 'regular', 'heap'):
        backend['memory_' + backing + '_workers'] = 0
        backend['memory_' + backing + '_bytes'] = 0
    run = {'hashes': 1000, 'counted_hashes': 970, 'late_hashes': 30,
        'elapsed_secs': 15.5, 'actual_elapsed_secs': 15.5, 'backend_runs': [backend]}
    report = {'schema_version': 14, 'bench_kind': 'backend', 'cpu_threads': 32,
        'bench_secs': 15, 'rounds': 2, 'warmup_rounds': 1, 'runs': [run, copy.deepcopy(run)],
        'total_hashes': 2000,
        'config_fingerprint': {'cpu_kernel': 'avx512-256-stream', 'cpu_kernel_requested': 'avx512-256-stream',
            'cpu_page_mode': 'large', 'cpu_affinity': 'auto', 'cpu_autotune_threads': False},
        'pow_fingerprint': {'memory_kb': 2097152, 'iterations': 1, 'parallelism': 1,
            'output_len': 32, 'header_base_len': 92},
        'environment': {'cpu_identity': {'vendor': 'AuthenticAMD', 'family': 26, 'model': 2}}}
    checks = {'delta': {'pswpin': 0, 'pswpout': 0, 'oom_kill': 0}, 'steal_pct': 0,
              'steal_single_cpu_upper_pct': 0}
    return report, checks


class RawReportTests(unittest.TestCase):
    def test_includes_completed_fence_hashes_and_time(self):
        report, checks = fixture()
        result = report_rate(report, checks, 32, 15)
        self.assertEqual(result['completed_hashes'], 2000)
        self.assertEqual(result['elapsed_seconds'], 31)
        self.assertEqual(result['hps'], 2000 / 31)

    def test_rejects_inconsistent_hash_totals(self):
        report, checks = fixture()
        report['runs'][0]['hashes'] += 1
        with self.assertRaises(AssertionError):
            report_rate(report, checks, 32, 15)

    def test_rejects_page_fallback(self):
        report, checks = fixture()
        report['runs'][0]['backend_runs'][0]['memory_explicit_large_workers'] -= 1
        with self.assertRaises(AssertionError):
            report_rate(report, checks, 32, 15)

    def test_rejects_short_denominator(self):
        report, checks = fixture()
        report['runs'][0]['elapsed_secs'] = 15
        with self.assertRaises(AssertionError):
            report_rate(report, checks, 32, 15)

    def test_rejects_resource_failure(self):
        report, checks = fixture()
        checks['delta']['oom_kill'] = 1
        with self.assertRaises(AssertionError):
            report_rate(report, checks, 32, 15)


if __name__ == '__main__':
    unittest.main()
