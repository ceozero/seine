import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import run


class ControllerTests(unittest.TestCase):
    def fixture(self):
        deadline = run.PROVIDER_DEADLINE - 600
        authorization = {'server_id': 1043469, 'ledger_extension_recorded': True,
            'controller_deadline_epoch': deadline, 'provider_delete_before_epoch': run.PROVIDER_DEADLINE,
            'funded_until_epoch': run.GOAL_DEADLINE,
            'total_reserved_usd': 16.45}
        handoff = {'experiments_finished': True, 'verified_collections': {
            name: {'archive_sha256': 'a' * 64, 'verified_manifest_entries': 50, 'settings_restored': True}
            for name in ('amd-overnight-20261025', 'amd-ring-locality-20261025',
                         'amd-page-size-20261025', 'amd-trial-windows-20261025')}}
        return authorization, handoff, deadline

    def test_only_owned_outer_controller_can_be_active(self):
        authorization, handoff, deadline = self.fixture()
        run.validate_admission(authorization, handoff,
            'seine-amd-efficient-config.service loaded active running controller', deadline - 3000, deadline)
        for unit in ('seine-amd-productive.service', 'seine-amd-ring-screen.service',
                     'seine-short-windows-joint-control-1.service'):
            with self.subTest(unit=unit), self.assertRaises(AssertionError):
                run.validate_admission(authorization, handoff, unit + ' loaded active running',
                                       deadline - 3000, deadline)

    def test_budget_time_and_collected_evidence_are_required(self):
        authorization, handoff, deadline = self.fixture()
        for changes in ({'total_reserved_usd': 26}, {'ledger_extension_recorded': False},
                        {'funded_until_epoch': deadline},
                        {'provider_delete_before_epoch': run.GOAL_DEADLINE + 1}):
            with self.subTest(changes=changes), self.assertRaises(AssertionError):
                run.validate_admission({**authorization, **changes}, handoff, '', deadline - 3000, deadline)
        with self.assertRaises(AssertionError):
            run.validate_admission(authorization, handoff, '', deadline - 1980, deadline)
        broken = copy.deepcopy(handoff)
        broken['verified_collections']['amd-ring-locality-20261025']['settings_restored'] = False
        with self.assertRaises(AssertionError):
            run.validate_admission(authorization, broken, '', deadline - 3000, deadline)

    def test_pool_writer_uses_exact_newline_and_only_selected_fake_pool(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / 'pool'
            folder.mkdir()
            target = folder / 'nr_hugepages'
            target.write_text('0\n')
            with patch.object(run, 'ROOT', root), patch.object(run, 'OUT', root), \
                 patch.object(run, 'POOLS', {'large-1g': folder}):
                self.assertEqual(run.set_pool('reserve', 'large-1g', 128), 0)
                self.assertEqual(target.read_bytes(), b'128\n')
                self.assertEqual(run.set_pool('restore', 'large-1g', 0), 0)
                self.assertEqual(target.read_bytes(), b'0\n')


if __name__ == '__main__':
    unittest.main()
