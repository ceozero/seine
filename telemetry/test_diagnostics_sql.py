"""Exercise diagnostic grouping against disposable PostgreSQL, including legacy reports."""
import copy
import json
import uuid
from pathlib import Path
import unittest
import test_alerts_sql


@unittest.skipUnless((test_alerts_sql.PG / 'initdb').exists(), 'PostgreSQL 16 binaries required')
class DiagnosticSQLTests(unittest.TestCase):
    # Reuse the existing disposable database setup, without inheriting its test cases.
    setUpClass = classmethod(test_alerts_sql.AlertSQLTests.setUpClass.__func__)
    cleanup = classmethod(test_alerts_sql.AlertSQLTests.cleanup.__func__)
    query = classmethod(test_alerts_sql.AlertSQLTests.query.__func__)
    setUp = test_alerts_sql.AlertSQLTests.setUp
    def insert_diagnostic(self, payload, identity=None):
        text = json.dumps(payload).replace("'", "''")
        self.query("INSERT INTO telemetry_reports VALUES "
                   f"('{uuid.uuid4().hex}','{identity or uuid.uuid4().hex}',now(),'{text}'::jsonb)")

    def diagnostics(self):
        return json.loads(self.query((Path(__file__).parent / 'diagnostics.sql').read_text()))

    def test_typed_causes_phases_and_legacy_fields_remain_distinct(self):
        fixture = json.loads((Path(__file__).parent / 'diagnostics-fixture.json').read_text())
        fixture['diagnostics']['events'][0]['count'] = 100
        identity = uuid.uuid4().hex
        self.insert_diagnostic(fixture, identity)
        self.insert_diagnostic(fixture, identity)
        other = copy.deepcopy(fixture)
        other['diagnostics']['events'][0]['detail']['os_error'] = 13
        self.insert_diagnostic(other)
        legacy = copy.deepcopy(fixture)
        legacy['schema_version'] = 3
        legacy['diagnostics'].pop('phase')
        legacy['diagnostics'].pop('previous_run')
        legacy['diagnostics']['events'][0].pop('detail')
        legacy['diagnostics']['events'][0].pop('phase')
        legacy['backends'] = []
        self.insert_diagnostic(legacy)
        report = self.diagnostics()
        self.assertEqual(report['status'], 'attention')
        self.assertEqual(len(report['issue_clusters']), 3)
        causes = {c['detail']['os_error']: c for c in report['issue_clusters'] if c['detail']}
        self.assertEqual(causes[12]['affected_installations'], 1)
        self.assertEqual(causes[12]['occurrences'], 200)
        self.assertEqual(causes[12]['detail']['requested_bytes'], 2147483648)
        self.assertEqual(causes[12]['phase'], 'initializing_backends')
        self.assertEqual(report['recent_unclean_versions'][0]['affected_installations'], 3)
        observed = next(c for c in report['unclean_run_clusters'] if c['last_observed_phase'])
        self.assertEqual(observed['affected_installations'], 2)
        self.assertEqual(observed['installations_hashing_in_restart_report'], 2)
        self.assertEqual(observed['minimum_previous_uptime_secs'], 19)
        unknown = next(c for c in report['unclean_run_clusters'] if not c['last_observed_phase'])
        self.assertIsNone(unknown['previous_build_commit'])
        self.assertEqual(unknown['installations_hashing_in_restart_report'], 0)
        self.assertNotIn(identity, json.dumps(report))
        self.assertNotIn('installation_id', json.dumps(report))

    def test_unique_failure_is_not_hidden_by_common_warning_limit(self):
        fixture = json.loads((Path(__file__).parent / 'diagnostics-fixture.json').read_text())
        for line in range(40):
            value = copy.deepcopy(fixture)
            value['diagnostics']['events'][0].update(line=line, count=1000)
            value['diagnostics']['events'][0].pop('detail')
            self.insert_diagnostic(value)
        fixture['diagnostics']['events'][0]['code'] = 'run_failed'
        self.insert_diagnostic(fixture)
        report = self.diagnostics()
        self.assertEqual(len(report['issue_clusters']), 30)
        self.assertEqual(report['issue_clusters'][0]['code'], 'run_failed')


if __name__ == '__main__':
    unittest.main()
