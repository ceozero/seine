"""Keep reference workers within available host and cgroup memory."""
from pathlib import Path
import tempfile
import unittest
from build_reference_cache import darwin_available_memory, linux_cgroup_available_memory


class AdmissionTests(unittest.TestCase):
    def test_counts_reclaimable_pages_without_compressed_or_swap_memory(self):
        for size in [4096, 16384]:
            with self.subTest(page_size=size):
                output = f'''Mach Virtual Memory Statistics: (page size of {size} bytes)
Pages free: 100.
Pages active: 900.
Pages inactive: 200.
Pages speculative: 50.
Pages purgeable: 90.
Pages occupied by compressor: 800.
Swapins: 999999.
'''
                self.assertEqual(darwin_available_memory(output), 350 * size)

    def test_missing_or_unrecognized_stats_fail_closed(self):
        with self.assertRaises((TypeError, AttributeError)):
            darwin_available_memory('unknown memory-statistics output')

    def test_cgroup_scope_high_and_ancestor_limits_reserve_existing_usage(self):
        gib = 1024**3
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scope = root / 'agents' / 'worker'
            scope.mkdir(parents=True)
            for path in [root, scope.parent, scope]:
                (path / 'memory.current').write_text(str(gib))
                (path / 'memory.high').write_text('max')
                (path / 'memory.max').write_text('max')
            check = lambda: linux_cgroup_available_memory(50 * gib, '0::/agents/worker\n', root)
            (scope / 'memory.high').write_text(str(4 * gib))
            (scope / 'memory.max').write_text(str(6 * gib))
            self.assertEqual(check(), 3 * gib)
            (scope.parent / 'memory.max').write_text(str(2 * gib))
            self.assertEqual(check(), gib)
            (root / 'memory.high').write_text(str(gib // 2))
            self.assertEqual(check(), 0)

    def test_unlimited_cgroup_keeps_host_headroom(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'memory.current').write_text('100')
            (root / 'memory.high').write_text('max')
            (root / 'memory.max').write_text('max')
            self.assertEqual(linux_cgroup_available_memory(123, '0::/\n', root), 123)

    def test_invalid_or_unreadable_unified_limits_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for membership in ['0::/missing', '0::/../../outside']:
                with self.assertRaises(RuntimeError):
                    linux_cgroup_available_memory(999, membership, root)
            (root / 'memory.current').write_text('1')
            (root / 'memory.high').write_text('unrecognized')
            with self.assertRaises(ValueError):
                linux_cgroup_available_memory(999, '0::/', root)


if __name__ == '__main__':
    unittest.main()
