#!/usr/bin/env python3
"""Evidence-rejection checks for the experimental cross-build comparison."""
import copy
import json
from pathlib import Path
import sys
import unittest

import compare_energy

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import bench_cpu_energy as energy
import test_bench_cpu_energy as fixtures


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.EnergyTests(methodName='runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.binaries = {'baseline': 'a' * 64, 'candidate': 'b' * 64}
        for pair in range(1, 5):
            for role in self.binaries:
                label = f'pair-{pair:02d}-{role}'
                folder = self.fixture.measurement(label, 10 if role == 'baseline' else 8)
                report = fixtures.report()
                report.update(cpu_threads=32, bench_secs=120)
                report['config_fingerprint'].update(cpu_page_mode='large',
                    cpu_kernel='avx512-256-stream', cpu_kernel_requested='avx512-256-stream')
                report['runs'][0]['backend_runs'][0].update(memory_regular_workers=0,
                    memory_regular_bytes=0, memory_explicit_large_workers=32,
                    memory_explicit_large_bytes=32 * 2 * energy.GIB)
                report['environment'].update({key: 'fixture' for key in (
                    'cpu_brand', 'cpu_arch', 'runtime_environment', 'os', 'kernel_version',
                    'target_triple', 'build_profile', 'build_opt_level', 'build_rustflags',
                    'build_features', 'rustc_version')})
                report['environment'].update(logical_cores=64, physical_cores=32,
                    total_memory_bytes=192 * energy.GIB, git_commit=role,
                    source_fingerprint=role, build_fingerprint=role)
                (folder / 'bench.json').write_text(json.dumps(report))
                record = json.loads((folder / 'energy.json').read_text())
                record.update(binary_sha256=self.binaries[role],
                    benchmark_sha256=energy.sha256(folder / 'bench.json'),
                    context_after=copy.deepcopy(record['context_before']))
                (folder / 'energy.json').write_text(json.dumps(record))
                (self.root / (label + '-cap.json')).write_text(json.dumps({
                    'before_uw': 280_000_000, 'after_uw': 280_000_000, 'requested_uw': 280_000_000}))

    def change(self, file, transform, *, refresh_report=False):
        path = self.root / file
        original = path.read_text()
        value = json.loads(original)
        transform(value)
        path.write_text(json.dumps(value))
        if refresh_report:
            self.change(str(path.parent.relative_to(self.root) / 'energy.json'),
                lambda value: value.update(benchmark_sha256=energy.sha256(path)))
        self.addCleanup(path.write_text, original)

    def compare(self):
        return compare_energy.compare(self.root, self.binaries, 32)

    def test_distinct_frozen_builds_use_verified_raw_energy(self):
        result = self.compare()
        metric = result['metrics']['invocation_joules_per_completed_hash']['comparison']
        self.assertAlmostEqual(metric['paired_geometric_delta_pct'], -20)
        self.assertEqual(metric['sign_consistency']['candidate_lower_pairs'], 4)
        self.assertEqual(len(result['observations']), 8)
        self.assertEqual(result['binary_sha256'], self.binaries)

    def test_binary_swap_and_duplicate_builds_are_rejected(self):
        with self.assertRaisesRegex(energy.EnergyError, 'distinct'):
            compare_energy.compare(self.root, dict.fromkeys(self.binaries, 'a' * 64), 32)
        self.change('pair-02-candidate/energy.json', lambda r: r.update(binary_sha256='c' * 64))
        with self.assertRaisesRegex(energy.EnergyError, 'binary identity'):
            self.compare()

    def test_fabricated_derived_metric_is_rejected(self):
        self.change('pair-02-candidate/energy.json',
                    lambda r: r.update(invocation_joules_per_completed_hash=.01))
        with self.assertRaisesRegex(energy.EnergyError, 'raw observations'):
            self.compare()

    def test_power_cap_change_is_rejected(self):
        self.change('pair-01-candidate-cap.json', lambda r: r.update(after_uw=240_000_000))
        with self.assertRaisesRegex(energy.EnergyError, 'power cap'):
            self.compare()

    def test_compiler_change_is_rejected_even_with_valid_report_checksum(self):
        self.change('pair-01-candidate/bench.json',
                    lambda r: r['environment'].update(build_rustflags='-Ctarget-cpu=native'),
                    refresh_report=True)
        with self.assertRaisesRegex(energy.EnergyError, 'toolchain'):
            self.compare()

    def test_reboot_between_matched_pairs_is_rejected(self):
        for role in self.binaries:
            self.change(f'pair-02-{role}/energy.json', lambda r: (
                r['context_before'].update(boot_id='other'), r['context_after'].update(boot_id='other')))
        with self.assertRaisesRegex(energy.EnergyError, 'boot_id'):
            self.compare()

    def test_resource_pressure_is_rejected(self):
        self.change('pair-01-candidate/energy.json',
                    lambda r: r['context_after']['vmstat'].update(oom_kill=1))
        with self.assertRaisesRegex(energy.EnergyError, 'OOM'):
            self.compare()

    def test_page_fallback_is_rejected_with_recomputed_checksum(self):
        self.change('pair-01-candidate/bench.json',
                    lambda r: r['runs'][0]['backend_runs'][0].update(memory_explicit_large_workers=31),
                    refresh_report=True)
        with self.assertRaisesRegex(energy.EnergyError, 'backing'):
            self.compare()


if __name__ == '__main__':
    unittest.main()
