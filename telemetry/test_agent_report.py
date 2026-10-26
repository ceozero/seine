"""Exercise agent briefing outcomes without production access."""
import contextlib
import io
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import agent_report


class BriefingTests(unittest.TestCase):
    def run_briefing(self, quality, query_failure=False, diagnostic_status='unavailable'):
        results = [
            SimpleNamespace(returncode=0, stdout='service healthy', stderr=''),
            SimpleNamespace(returncode=0, stdout=json.dumps(quality), stderr=''),
            SimpleNamespace(returncode=1 if query_failure else 0,
                            stdout=json.dumps({'performance_candidates': []}),
                            stderr='query failed' if query_failure else ''),
            SimpleNamespace(returncode=0, stdout=json.dumps({'status': diagnostic_status}), stderr=''),
        ]
        output = io.StringIO()
        with patch.object(agent_report, 'remote', side_effect=results), \
             patch('sys.argv', ['agent_report.py']), contextlib.redirect_stdout(output):
            code = agent_report.main()
        return code, json.loads(output.getvalue())

    def test_inventory_only_failure_is_not_reported_as_sparse_data(self):
        code, briefing = self.run_briefing({'status': 'error'})
        self.assertEqual(code, 1)
        self.assertEqual(briefing['health']['status'], 'ok')
        self.assertIn('Investigate the miner sampling path', briefing['assessment'])

    def test_sparse_healthy_data_remains_successful(self):
        code, briefing = self.run_briefing({'status': 'ok'})
        self.assertEqual(code, 0)
        self.assertIn('No qualifying performance cohorts', briefing['assessment'])

    def test_query_failure_keeps_successful_parts(self):
        code, briefing = self.run_briefing({'status': 'ok'}, query_failure=True)
        self.assertEqual(code, 1)
        self.assertEqual(briefing['data_quality']['status'], 'ok')
        self.assertIn('health/query failure', briefing['assessment'])

    def test_missing_diagnostics_are_not_healthy_miners(self):
        code, briefing = self.run_briefing({'status': 'ok'})
        self.assertEqual(code, 0)
        self.assertIn('No diagnostic coverage', briefing['diagnostic_assessment'])

    def test_fleet_failures_trigger_attention_without_losing_performance(self):
        code, briefing = self.run_briefing({'status': 'ok'}, diagnostic_status='attention')
        self.assertEqual(code, 1)
        self.assertIn('issue clusters', briefing['diagnostic_assessment'])
        self.assertEqual(briefing['telemetry']['performance_candidates'], [])


if __name__ == '__main__':
    unittest.main()
