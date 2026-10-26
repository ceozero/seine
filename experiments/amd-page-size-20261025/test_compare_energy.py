import copy
import json
from pathlib import Path
import sys
import unittest

import compare_energy

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import bench_cpu_energy as energy
import test_bench_cpu_energy as fixtures


class PageComparisonTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.EnergyTests(methodName='runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.binary = 'a' * 64
        for pair in range(1, 5):
            for role, mode in compare_energy.PAGE_MODES.items():
                label = f'pair-{pair:02d}-{role}'
                joules = 10 if role == 'baseline' else 8
                folder = self.fixture.measurement(label, joules)
                report = fixtures.report()
                report.update(cpu_threads=64, bench_secs=120)
                report['config_fingerprint'].update(cpu_page_mode=mode,
                    cpu_kernel='avx512-256-stream', cpu_kernel_requested='avx512-256-stream')
                report['runs'][0].update(configured_secs=120, actual_elapsed_secs=120.1, elapsed_secs=120.25)
                backend = report['runs'][0]['backend_runs'][0]
                backend.update(memory_regular_workers=0, memory_regular_bytes=0,
                    memory_explicit_large_workers=64 if role == 'baseline' else 0,
                    memory_explicit_large_bytes=128 * energy.GIB if role == 'baseline' else 0,
                    memory_explicit_large_1g_workers=64 if role == 'candidate' else 0,
                    memory_explicit_large_1g_bytes=128 * energy.GIB if role == 'candidate' else 0)
                report['environment'].update({key: 'fixture' for key in (
                    'cpu_brand', 'cpu_arch', 'runtime_environment', 'os', 'kernel_version',
                    'target_triple', 'build_profile', 'build_opt_level', 'build_rustflags',
                    'build_features', 'rustc_version', 'git_commit', 'source_fingerprint', 'build_fingerprint')})
                report['environment'].update(logical_cores=64, physical_cores=32,
                    total_memory_bytes=192 * energy.GIB,
                    cpu_identity={'vendor': 'AuthenticAMD', 'family': 26, 'model': 2})
                (folder / 'bench.json').write_text(json.dumps(report))
                record = json.loads((folder / 'energy.json').read_text())
                record.update(binary_sha256=self.binary, benchmark_sha256=energy.sha256(folder / 'bench.json'),
                    context_after=copy.deepcopy(record['context_before']), invocation_secs=120.5,
                    invocation_completed_hashes_per_second=12 / 120.5, average_package_watts=joules / 120.5,
                    samples=[self.fixture.sample(i * .5, int(joules * 1e6 * i / 241)) for i in range(242)])
                (folder / 'energy.json').write_text(json.dumps(record))
                (self.root / (label + '-cap.json')).write_text(json.dumps({
                    'before_uw': 280_000_000, 'after_uw': 280_000_000, 'requested_uw': 280_000_000}))
                (self.root / (label + '-pools.json')).write_text(json.dumps({'mode': mode,
                    'before': compare_energy.expected_pool_state(mode),
                    'after': compare_energy.expected_pool_state(mode)}))

    def edit(self, relative, change, *, report=False):
        path = self.root / relative
        data = json.loads(path.read_text())
        change(data)
        path.write_text(json.dumps(data))
        if report:
            self.edit(str(path.parent.relative_to(self.root) / 'energy.json'),
                lambda r: r.update(benchmark_sha256=energy.sha256(path)))

    def compare(self):
        return compare_energy.compare(self.root, self.binary)

    def test_same_binary_page_change_uses_raw_energy(self):
        result = self.compare()
        self.assertAlmostEqual(result['metrics']['invocation_joules_per_completed_hash']
                               ['comparison']['paired_geometric_delta_pct'], -20)
        self.assertEqual(len(result['observations']), 8)

    def test_different_binary_is_not_a_page_comparison(self):
        self.edit('pair-01-candidate/energy.json', lambda r: r.update(binary_sha256='b' * 64))
        with self.assertRaisesRegex(energy.EnergyError, 'binary identity'):
            self.compare()

    def test_actual_backing_must_match_requested_page_size(self):
        self.edit('pair-01-candidate/bench.json',
            lambda r: r['runs'][0]['backend_runs'][0].update(memory_explicit_large_1g_workers=0), report=True)
        with self.assertRaisesRegex(energy.EnergyError, 'backing'):
            self.compare()

    def test_pool_leak_or_incomplete_reservation_is_rejected(self):
        self.edit('pair-01-candidate-pools.json', lambda r: r['after']['large-1g'].update(free=126))
        with self.assertRaisesRegex(energy.EnergyError, 'page pools'):
            self.compare()

    def test_declared_120_seconds_does_not_cover_short_actual_run(self):
        self.edit('pair-01-candidate/bench.json',
            lambda r: r['runs'][0].update(actual_elapsed_secs=30), report=True)
        with self.assertRaisesRegex(energy.EnergyError, '120-second window'):
            self.compare()

    def test_changed_affinity_is_not_hidden_by_page_exception(self):
        self.edit('pair-01-candidate/bench.json',
            lambda r: r['config_fingerprint'].update(cpu_affinity='off'), report=True)
        with self.assertRaisesRegex(energy.EnergyError, 'protocol differs'):
            self.compare()

    def test_fabricated_energy_fails(self):
        self.edit('pair-01-candidate/energy.json', lambda r: r.update(total_package_joules=1))
        with self.assertRaisesRegex(energy.EnergyError, 'derived energy'):
            self.compare()

    def test_same_binary_cannot_have_different_source_identity(self):
        for pair in range(1, 5):
            self.edit(f'pair-{pair:02d}-candidate/bench.json',
                lambda r: r['environment'].update(source_fingerprint='different'), report=True)
        with self.assertRaisesRegex(energy.EnergyError, 'inconsistent source/build'):
            self.compare()

    def test_power_cap_change_is_not_a_page_size_effect(self):
        self.edit('pair-01-candidate-cap.json', lambda r: r.update(after_uw=240_000_000))
        with self.assertRaisesRegex(energy.EnergyError, 'power cap'):
            self.compare()


if __name__ == '__main__':
    unittest.main()
