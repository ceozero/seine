import unittest

from analyze import records


class RecordTests(unittest.TestCase):
    def test_unavailable_has_no_zero_hashrate_points(self):
        result = records({'status': 'UNAVAILABLE'})
        self.assertEqual(result['status'], 'UNAVAILABLE')
        self.assertEqual(result['records'], [])

    def test_aggregates_hashes_energy_and_time_over_same_interval(self):
        observations = [{'pair': pair, 'role': role, 'completed_hashes': 100,
            'invocation_seconds': seconds, 'package_joules': 2000}
            for role in ('baseline', 'candidate') for pair, seconds in enumerate((10, 10, 20, 40), 1)]
        result = {'status': 'COMPLETE', 'comparison': {'observations': observations},
            'hardware': {'Model name': 'AMD EPYC 9355P'}, 'source_revision': 'test',
            'runtime_source_base': 'test', 'variant_patch_sha256': 'a' * 64,
            'binary_sha256': 'b' * 64}
        baseline, candidate = records(result)['records']
        self.assertEqual(baseline['hps'], 5)
        self.assertEqual(baseline['package_watts'], 100)
        self.assertEqual(baseline['package_joules_per_hash'], 20)
        self.assertEqual(baseline['hashes_per_package_joule'], .05)
        self.assertEqual(baseline['hugepage_size_kib'], 2048)
        self.assertEqual(candidate['hugepage_size_kib'], 1048576)
        self.assertEqual(baseline['power_cap_w'], 280)
        self.assertEqual(candidate['power_cap_w'], 240)
        self.assertEqual(candidate['selection'], 'manual_fixed_configuration')
        self.assertEqual(candidate['phase'], 'combined_page_and_power_configuration')


if __name__ == '__main__':
    unittest.main()
