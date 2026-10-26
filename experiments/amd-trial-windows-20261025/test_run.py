import copy
import unittest

from run import GOAL_DEADLINE, OWN_UNIT, validate_active_units, validate_authorization, validate_handoff


class AdmissionTests(unittest.TestCase):
    def test_running_measurement_blocks_even_if_old_files_claim_completion(self):
        validate_active_units(OWN_UNIT + ' loaded active running controller\n')
        validate_active_units('')
        for unit in ('seine-amd-productive.service', 'seine-amd-ring-screen.service',
                     'seine-overnight-joint-control-1.service', 'seine-cherry-power.service'):
            with self.subTest(unit=unit), self.assertRaises(AssertionError):
                validate_active_units(unit + ' loaded active running test\n')

    def test_all_prior_collections_and_restoration_are_required(self):
        data = {'experiments_finished': True, 'verified_collections': {
            name: {'archive_sha256': 'a' * 64, 'verified_manifest_entries': 50,
                   'settings_restored': True}
            for name in ('amd-overnight-20261025', 'amd-ring-locality-20261025',
                         'amd-page-size-20261025')}}
        validate_handoff(data)
        missing_page = copy.deepcopy(data)
        del missing_page['verified_collections']['amd-page-size-20261025']
        with self.assertRaises(KeyError):
            validate_handoff(missing_page)
        for field, value in (('archive_sha256', 'not-a-checksum'),
                             ('verified_manifest_entries', 0), ('settings_restored', False)):
            broken = copy.deepcopy(data)
            broken['verified_collections']['amd-ring-locality-20261025'][field] = value
            with self.subTest(field=field), self.assertRaises(AssertionError):
                validate_handoff(broken)

    def test_budget_and_full_protocol_time_cannot_be_shortened_or_extended(self):
        deadline = GOAL_DEADLINE - 900
        now = deadline - 15000
        record = {'server_id': 1043469, 'ledger_extension_recorded': True,
            'controller_deadline_epoch': deadline, 'provider_delete_before_epoch': GOAL_DEADLINE,
            'funded_until_epoch': GOAL_DEADLINE,
            'cherry_total_reserved_usd': 13.20, 'aws_reserved_usd': 3.25,
            'total_reserved_usd': 16.45}
        validate_authorization(record, deadline, now)
        for change in ({'provider_delete_before_epoch': GOAL_DEADLINE + 1},
                       {'funded_until_epoch': deadline},
                       {'provider_delete_before_epoch': deadline + 599},
                       {'ledger_extension_recorded': False},
                       {'total_reserved_usd': 26}, {'cherry_total_reserved_usd': 14.4}):
            with self.subTest(change=change), self.assertRaises(AssertionError):
                validate_authorization({**record, **change}, deadline, now)
        with self.assertRaises(AssertionError):
            validate_authorization(record, deadline, deadline - 14400)


if __name__ == '__main__':
    unittest.main()
