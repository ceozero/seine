#!/usr/bin/env python3
import unittest
import hashlib

from export_records import apply_review, records


def fixture():
    hardware = {'Vendor ID': 'AuthenticAMD', 'CPU family': '25', 'Model': '17',
        'CPU(s)': '32', 'Hypervisor vendor': 'KVM', 'Model name': 'AMD EPYC 9R14',
        'Thread(s) per core': '1', 'NUMA node(s)': '1'}
    data = {'hardware': {'lscpu': [{'field': key + ':', 'data': value} for key, value in hardware.items()]},
            'productive': {}, 'protocol_checks': {'landing_status': 'Await review'}}
    provenance = {'control_commit': 'control', 'candidate_commit': 'candidate',
                  'sha256': {'control': 'a' * 64, 'candidate': 'b' * 64}}
    manifest = {}
    for warm in (False, True):
        for role in ('control', 'candidate'):
            for pair, suffix in enumerate(('a', 'b'), 1):
                label = ('joint-warm-' if warm else 'joint-') + role + '-' + suffix
                seconds, hashes = pair * 10, pair * pair * 100
                data['productive'][label] = {
                    'cache_mode': 'warm' if warm else 'cold', 'starting_threads': 12,
                    'identity': {'binary_sha256': provenance['sha256'][role],
                                 'meminfo_before': {'MemTotal': 64 * 1024**2}},
                    'window': {'completed_hashes_lower_bound': hashes,
                        'elapsed_start_request_through_stopped_seconds': seconds,
                        'completed_hps_lower_bound': hashes / seconds},
                    'caches': {'tuning.json': {'selected_threads': 24, 'profile': 'balanced'},
                        'tuning.json.kernels.json': {'host': {'os': 'linux', 'kernel_version': 'fixture'}}}}
                for name in ('miner.log', 'productive-window.json'):
                    manifest['results/' + label + '/' + name] = 'digest'
    return data, provenance, manifest


class RecordTests(unittest.TestCase):
    def test_adoption_review_requires_exact_evidence_and_builds(self):
        data, provenance, _ = fixture()
        data.update(cold={'paired_deltas_pct': [3, 2]}, warm={'paired_deltas_pct': [7, 8]},
                    fixed={'fixed-avx2-control': {'geometric_delta_pct': -0.5}})
        data['protocol_checks']['tuning_gate_failures'] = []
        review = {'decision': 'accept_automatic_trial_eligibility',
                  'result_manifest_sha256': hashlib.sha256(b'fixture').hexdigest(),
                  'binary_sha256': provenance['sha256'], 'cold_paired_deltas_pct': [3, 2],
                  'warm_paired_deltas_pct': [7, 8], 'fixed_control_delta_pct': -0.5}
        apply_review(data, provenance, b'fixture', review)
        self.assertTrue(data['protocol_checks']['landing_status'].startswith('Accepted'))
        with self.assertRaises(AssertionError):
            apply_review(data, provenance, b'different evidence', review)
        data['protocol_checks']['tuning_gate_failures'] = ['missing restoration']
        with self.assertRaises(AssertionError):
            apply_review(data, provenance, b'fixture', review)

    def test_vm_scope_unknown_physical_memory_and_ratio_of_totals(self):
        result = records(*fixture())
        self.assertEqual(len(result['records']), 4)
        for record in result['records']:
            self.assertEqual(record['hps'], 500 / 30)
            self.assertEqual(record['repetitions'], 2)
            self.assertEqual(record['guest_vcpus'], 32)
            self.assertEqual(record['autotune_worker_maximum'], 24)
            self.assertEqual(record['cpu_profile'], 'balanced')
            self.assertEqual(record['virtualization'], 'KVM')
            for key in ('physical_cores', 'installed_memory_gib', 'memory_channels_populated',
                        'memory_speed_mts', 'power_cap_w', 'package_watts', 'hashes_per_package_joule'):
                self.assertIsNone(record[key], key)

    def test_provenance_mismatch_is_rejected(self):
        data, provenance, manifest = fixture()
        provenance['sha256']['candidate'] = 'unexpected'
        with self.assertRaises(AssertionError):
            records(data, provenance, manifest)

    def test_missing_pair_cannot_be_exported(self):
        data, provenance, manifest = fixture()
        del data['productive']['joint-control-b']
        with self.assertRaises(KeyError):
            records(data, provenance, manifest)


if __name__ == '__main__':
    unittest.main()
