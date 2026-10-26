import copy
import json
from pathlib import Path
import tempfile
import unittest

from analyze import validate_windows


class WindowScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.runs = {}
        order = [(role, pair) for pair in range(1, 5)
                 for role in (('control', 'candidate') if pair % 2 else ('candidate', 'control'))]
        start = 1000.0
        for warm, pairs in ((False, order), (True, reversed(order))):
            for role, pair in pairs:
                label = f"joint-{'warm-' if warm else ''}{role}-{pair}"
                folder = self.root / 'results' / label
                folder.mkdir(parents=True)
                remote = Path('/root/frozen')
                identity = {'binary': str(remote / role), 'cache_source':
                    str(remote / 'results' / f'joint-{role}-{pair}') if warm else None}
                elapsed = (180 if warm else 1200) + .7
                window = {'observation_start_epoch': start,
                    'elapsed_start_request_through_stopped_seconds': elapsed}
                command = ['seine', '--backend', 'cpu', '--cpu-page-mode', 'large',
                    '--cpu-affinity', 'auto', '--cpu-autotune-config',
                    str(remote / 'results' / label / 'tuning.json'), '--data-dir',
                    str(remote / 'results' / label / 'config')]
                for name, value in (('identity.json', identity), ('productive-window.json', window),
                                    ('command.json', command)):
                    (folder / name).write_text(json.dumps(value))
                self.runs[label] = {'binary': role, 'pair': pair, 'warm': warm,
                    'count_cache_restored': warm, 'cpu_profile': 'balanced'}
                start += elapsed + 5

    def change(self, label, filename, change):
        path = self.root / 'results' / label / filename
        value = json.loads(path.read_text())
        change(value)
        path.write_text(json.dumps(value))

    def test_full_interleaved_own_cache_campaign_passes(self):
        validate_windows(self.root, self.runs)

    def test_truncated_window_fails_even_with_original_requested_duration(self):
        self.change('joint-candidate-1', 'productive-window.json',
            lambda value: value.update(elapsed_start_request_through_stopped_seconds=1199.9))
        with self.assertRaisesRegex(AssertionError, 'shortened window'):
            validate_windows(self.root, self.runs)

    def test_foreign_cache_and_failed_restoration_are_rejected(self):
        self.change('joint-warm-candidate-1', 'identity.json',
            lambda value: value.update(cache_source='/root/frozen/results/joint-control-1'))
        with self.assertRaisesRegex(AssertionError, 'foreign cache source'):
            validate_windows(self.root, self.runs)
        self.change('joint-warm-candidate-1', 'identity.json',
            lambda value: value.update(cache_source='/root/frozen/results/joint-candidate-1'))
        self.runs['joint-warm-candidate-1']['count_cache_restored'] = False
        with self.assertRaisesRegex(AssertionError, 'not restored'):
            validate_windows(self.root, self.runs)

    def test_overlap_or_wrong_order_is_rejected(self):
        self.change('joint-candidate-1', 'productive-window.json',
            lambda value: value.update(observation_start_epoch=1001))
        with self.assertRaisesRegex(AssertionError, 'execution order'):
            validate_windows(self.root, self.runs)

    def test_hidden_equals_override_is_rejected(self):
        self.change('joint-control-1', 'command.json', lambda value: value.append('--threads=32'))
        with self.assertRaises(AssertionError):
            validate_windows(self.root, self.runs)

    def test_missing_window_is_rejected(self):
        runs = copy.deepcopy(self.runs)
        del runs['joint-warm-control-4']
        with self.assertRaisesRegex(AssertionError, 'sixteen'):
            validate_windows(self.root, runs)


if __name__ == '__main__':
    unittest.main()
