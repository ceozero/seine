import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest

from reclaim_load import inject


class ReclaimLoadTests(unittest.TestCase):
    def test_small_allocation_touches_pages_and_reports_owned_pid(self):
        with tempfile.TemporaryDirectory() as directory:
            group = Path(directory)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                touched = inject(group, 1024 * 1024, .02)
            self.assertEqual(touched, 1024 * 1024)
            self.assertEqual((group / 'cgroup.procs').read_text(), str(os.getpid()) + '\n')
            record = json.loads(output.getvalue())
            self.assertEqual(record['bytes_touched'], touched)
            self.assertLess(record['elapsed_seconds'], 1)

    def test_allocation_and_duration_bounds_precede_cgroup_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            group = Path(directory)
            for size, seconds in ((0, 1), (2 * 1024**3 + 1, 1), (1, 0), (1, 26)):
                with self.subTest(size=size, seconds=seconds), self.assertRaises(AssertionError):
                    inject(group, size, seconds)
                self.assertFalse((group / 'cgroup.procs').exists())
