import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from collect import inspect_collected, verify


class CollectionTests(unittest.TestCase):
    def test_corruption_and_escape_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'file').write_bytes(b'evidence')
            digest = hashlib.sha256(b'evidence').hexdigest()
            self.assertEqual(verify(root, {'file': digest}), 1)
            with self.assertRaises(AssertionError):
                verify(root, {'file': '0' * 64})
            with self.assertRaises(AssertionError):
                verify(root, {'../outside': digest})

    def test_rejected_or_unavailable_are_preserved_but_restore_failure_blocks_handoff(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'expected-files.json').write_text('{}')
            folder = root / 'results'
            folder.mkdir()
            for status in ('COMPLETE_THROUGHPUT_REJECTED', 'UNAVAILABLE', 'FAILED'):
                for restored in (False, True):
                    outcome = {'status': status, 'settings_restored': restored, 'cleanup_failures': []}
                    (folder / 'outcome.json').write_text(json.dumps(outcome))
                    digest = hashlib.sha256((folder / 'outcome.json').read_bytes()).hexdigest()
                    (folder / 'manifest.json').write_text(json.dumps({'outcome.json': digest}))
                    report = inspect_collected(root)
                    self.assertEqual(report['ready_for_followup'], restored and status != 'FAILED')
                    self.assertEqual(report['verified_manifest_entries'], 1)


if __name__ == '__main__':
    unittest.main()
