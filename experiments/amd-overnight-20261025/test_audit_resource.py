import hashlib
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from audit_resource import audit_samples, verify_archive


def fixture():
    def make(phases, start):
        rows, hashes = [], 0
        for phase, seconds, threads in phases:
            for offset in (0, seconds):
                injected = phase in ('no-arena-budget', 'memory-recovery', 'cpu-contention', 'load-recovery')
                rows.append({'phase': phase, 'time': start + offset,
                    'completed_hashes': hashes, 'requested_threads': threads,
                    'memory.events': 'oom 0\noom_kill 0\nhigh ' + str(10 if injected else 0),
                    'memory.pressure': 'some avg10=0.00 total=' + str(10000 if injected else 0),
                    'cpu.pressure': 'some avg10=0.00 total=' + str(offset * 100),
                    'smaps_rollup': {'Anonymous': str(4 * 1024**2) + ' kB'}})
                hashes += 10
            start += seconds + 1
        return rows
    first = make([('initial-stable', 600, 3), ('one-arena-budget', 30, 1),
                  ('no-arena-budget', 30, 0), ('memory-recovery', 90, 1),
                  ('cpu-contention', 48, 1), ('load-recovery', 90, 2)], 0)
    restart = make([('constrained-restart', 35, 1), ('restart-recovery', 210, 2)], 1000)
    optout = make([('explicit-optout', 35, None)], 2000)
    return [first, restart, optout, {'selected_threads': 3}, {'selected_threads': 3},
            {'first': '', 'restart': 'cached starting point', 'optout': 'mining'}]


class ResourceAuditTests(unittest.TestCase):
    def test_full_observed_resource_lifecycle(self):
        result = audit_samples(*fixture())
        self.assertEqual(result['remembered_threads'], 3)
        self.assertEqual(result['maximum_restart_recovery_requested_threads'], 2)
        self.assertEqual(result['memory_high_events_increase'], 10)

    def test_missing_reclaim_events_or_psi_cannot_pass(self):
        for key, value in [('memory.events', 'oom 0\noom_kill 0\nhigh 0'),
                           ('memory.pressure', 'some avg10=0.00 total=0')]:
            data = fixture()
            for row in data[0]:
                row[key] = value
            with self.subTest(key=key), self.assertRaises(AssertionError):
                audit_samples(*data)

    def test_cache_overwrite_or_requested_only_growth_cannot_pass(self):
        data = fixture()
        data[4]['selected_threads'] = 1
        with self.assertRaises(AssertionError):
            audit_samples(*data)
        data = fixture()
        for row in data[1]:
            row['smaps_rollup']['Anonymous'] = '1024 kB'
        with self.assertRaises(AssertionError):
            audit_samples(*data)

    def test_truncated_recovery_cannot_pass(self):
        data = fixture()
        data[1][-1]['time'] = data[1][-2]['time'] + 10
        with self.assertRaises(AssertionError):
            audit_samples(*data)

    def test_archive_and_extracted_files_must_match(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'collected'
            root.mkdir()
            (root / 'results').mkdir()
            (root / 'binary').write_bytes(b'frozen')
            (root / 'expected-files.json').write_text(json.dumps({'binary': hashlib.sha256(b'frozen').hexdigest()}))
            (root / 'results/manifest.json').write_text('{}')
            archive = Path(temporary) / 'archive.tar.gz'
            with tarfile.open(archive, 'w:gz') as handle:
                for name in ('expected-files.json', 'results/manifest.json'):
                    handle.add(root / name, arcname=name)
            self.assertEqual(verify_archive(root, archive), 1)
            (root / 'binary').write_bytes(b'changed')
            with self.assertRaises(AssertionError):
                verify_archive(root, archive)
            (root / 'expected-files.json').write_text(json.dumps({'binary': hashlib.sha256(b'changed').hexdigest()}))
            with self.assertRaises(AssertionError):
                verify_archive(root, archive)
