"""Alert lifecycle, privacy, delivery and threshold tests; no external messages."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import alerts


class AlertsTests(unittest.TestCase):
    def setUp(self):
        self.state = {'incidents': {}}
        self.sent = []
        self.saved = []
        self.item = alerts.issue('diagnostics', 'v1', 'Three installations with errors')

    def tick(self, now, active=None, known=None, sender=None):
        return alerts.advance(self.state, [self.item] if active is None else active,
                              {'diagnostics'} if known is None else known, now,
                              sender or (lambda *args: self.sent.append(args)),
                              lambda state: self.saved.append(copy.deepcopy(state)))

    def test_confirmation_repeat_and_recovery(self):
        self.tick(1000)
        self.tick(1100)
        self.assertEqual(len(self.sent), 0)
        self.tick(1300)
        self.assertEqual(self.sent[-1][0], 'FIRING')
        self.tick(1600)
        self.assertEqual(len(self.sent), 1)
        self.tick(1300 + alerts.REPEAT_SECONDS)
        self.assertEqual(self.sent[-1][0], 'REMINDER')
        self.tick(16000, [])
        self.tick(16300, [])
        self.assertEqual(self.sent[-1][0], 'CLEARED')
        self.assertEqual(self.state['incidents'], {})

    def test_transient_does_not_notify(self):
        self.tick(1000)
        self.tick(1300, [])
        self.assertEqual(self.sent, [])
        self.assertEqual(self.state['incidents'], {})

    def test_monitor_downtime_does_not_confirm_a_pending_incident(self):
        self.tick(1000)
        self.tick(10000)
        self.assertEqual(self.sent, [])
        self.tick(10300)
        self.assertEqual(self.sent[-1][0], 'FIRING')

    def test_failed_delivery_is_not_acknowledged_and_is_retried(self):
        self.tick(1000)
        with self.assertRaises(OSError):
            self.tick(1300, sender=lambda *args: (_ for _ in ()).throw(OSError('offline')))
        self.assertIsNone(self.state['incidents'][self.item['key']]['last_sent'])
        self.tick(1600)
        self.assertEqual(self.sent[-1][0], 'FIRING')
        self.tick(1900, [])
        with self.assertRaises(OSError):
            self.tick(2200, [], sender=lambda *args: (_ for _ in ()).throw(OSError('offline')))
        self.assertIn(self.item['key'], self.state['incidents'])
        self.tick(2500, [])
        self.assertEqual(self.sent[-1][0], 'CLEARED')

    def test_unknown_query_does_not_clear_and_breaks_recovery_confirmation(self):
        self.tick(1000)
        self.tick(1300)
        self.tick(1600, [])
        self.tick(1900, [], known=set())
        self.tick(2200, [])
        self.assertEqual(len(self.sent), 1)
        self.tick(2500, [])
        self.assertEqual(self.sent[-1][0], 'CLEARED')

    def test_restart_preserves_deduplication(self):
        self.tick(1000)
        self.tick(1300)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.json'
            alerts.save(path, self.state)
            self.state = json.loads(path.read_text())
            self.tick(1600)
            self.assertEqual(len(self.sent), 1)

    def test_delivery_budget_eventually_sends_backlog(self):
        items = [alerts.issue('diagnostics', str(i), 'error') for i in range(15)]
        self.tick(1000, items)
        self.tick(1300, items)
        self.assertEqual(len(self.sent), 10)
        self.tick(1600, items)
        self.assertEqual(len(self.sent), 15)

    def test_aggregate_thresholds_and_unknown_categories(self):
        results = {'infrastructure': False, 'quality': {'versions': [
            {'version': 'v1', 'sustained_inventory_only_installations': 4},
            {'version': 'v2', 'sustained_inventory_only_installations': 5}]},
            'diagnostics': {'recent_error_versions': [
                {'version': 'v1', 'affected_installations': 2},
                {'version': 'v2', 'affected_installations': 3}], 'recent_unclean_versions': []},
            'performance': None}
        active, known = alerts.evaluate(results)
        self.assertEqual({i['category'] for i in active}, {'monitor', 'infrastructure', 'quality', 'diagnostics'})
        self.assertNotIn('performance', known)
        self.assertNotIn('ingestion', known)
        results['performance'] = {'minutes_since_last_report': 120, 'performance_cohorts': []}
        active, known = alerts.evaluate(results)
        self.assertIn('ingestion', {i['category'] for i in active})
        results['performance']['minutes_since_last_report'] = None
        self.assertIn('ingestion', {i['category'] for i in alerts.evaluate(results)[0]})

    def test_regression_requires_breadth_not_one_bad_rig(self):
        cohort = dict(version='v2', baseline_version='v1', hardware={'cpu_model': 'CPU'},
                      build=[], settings={'backend': 'cpu'}, installations=5,
                      affected_installations=2, median_ratio=.7)
        results = {'performance': {'minutes_since_last_report': 0, 'performance_cohorts': [cohort]}}
        self.assertEqual(alerts.evaluate(results)[0], [])
        cohort['affected_installations'] = 3
        self.assertEqual(len(alerts.evaluate(results)[0]), 1)
        cohort['median_ratio'] = .81
        self.assertEqual(alerts.evaluate(results)[0], [])

    def test_transport_sends_embed_without_mentions(self):
        class Response:
            status = 200
            def read(self, size): return b'{"id":"test-message"}'
            def __enter__(self): return self
            def __exit__(self, *args): pass
        with patch('urllib.request.build_opener') as opener:
            opener.return_value.open.return_value = Response()
            alerts.deliver('https://discord.com/api/webhooks/fake/test', 'FIRING', self.item, 1000)
            request = opener.return_value.open.call_args.args[0]
            self.assertTrue(request.full_url.endswith('?wait=true'))
            body = json.loads(request.data)
            self.assertEqual(body['allowed_mentions'], {'parse': []})
            self.assertNotIn('content', body)
            self.assertEqual(body, alerts.format_message('FIRING', self.item, 1000))
        self.assertNotIn('@', alerts.label('@everyone **https://private/**'))
        for url in ('http://discord.com/api/webhooks/a/b', 'https://attacker.test/api/webhooks/a/b', 'https://discord.com/other'):
            with self.assertRaises(ValueError): alerts.validate_webhook(url)
        alerts.validate_webhook('https://discord.com/api/webhooks/a/b')

    def test_known_legacy_quality_explains_upgrade_without_hiding_incident(self):
        for version in ('v0.2.24', '0.2.24', 'v0.2.25', '0.2.25', 'v0.2.26', 'v0.2.27', 'custom'):
            with self.subTest(version=version):
                active, _ = alerts.evaluate({'quality': {'versions': [
                    {'version': version, 'sustained_inventory_only_installations': 99}]}})
                self.assertEqual(len(active), 1)
                record = active[0]
                legacy = version.lstrip('v') in ('0.2.24', '0.2.25')
                self.assertEqual(record['severity'], 'info' if legacy else 'warning')
                self.assertEqual('Upgrade to v0.2.26' in record['action'], legacy)
                embed = alerts.format_message('FIRING', record, 1792965060)['embeds'][0]
                fields = {field['name']: field['value'] for field in embed['fields']}
                self.assertEqual(fields['Version'], version)
                self.assertEqual(fields['Affected installations'], '99')
                self.assertIn('do not establish that mining stopped', embed['description'])
                self.assertEqual(embed['color'], 0x3498DB if legacy else 0xF39C12)

    def test_existing_state_refreshes_presentation_without_resending(self):
        self.tick(1000)
        self.tick(1300)
        self.item.update(version='v0.2.26', affected=7, action='Inspect samples', severity='info')
        self.tick(1600)
        record = self.state['incidents'][self.item['key']]
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(record['affected'], 7)
        self.assertEqual(record['last_sent'], 1300)
        self.assertEqual(record['first_seen'], 1000)

    def test_embed_states_bounds_and_legacy_state(self):
        # Existing state has only category/key/summary; clearing still renders.
        for transition in ('FIRING', 'REMINDER', 'CLEARED', 'SETUP TEST'):
            record = alerts.issue('setup' if transition == 'SETUP TEST' else 'infrastructure',
                                  'fixture', 'x' * 10000, action='a' * 10000)
            embed = alerts.format_message(transition, record, 1792965060)['embeds'][0]
            self.assertLessEqual(len(embed['title']), 256)
            self.assertLessEqual(len(embed['description']), 4096)
            self.assertTrue(all(len(f['value']) <= 1024 for f in embed['fields']))
            self.assertLess(len(json.dumps(embed)), 6000)
            self.assertIn('EDT', embed['footer']['text'])
            self.assertIn(record['key'], embed['footer']['text'])
            if transition == 'CLEARED':
                self.assertEqual(embed['color'], 0x2ECC71)
                self.assertIn('does not prove every miner recovered', json.dumps(embed))
                self.assertNotIn('Next step', json.dumps(embed))
            elif transition == 'SETUP TEST':
                self.assertEqual(embed['color'], 0x3498DB)
            else:
                self.assertEqual(embed['color'], 0xE74C3C)
        cleared = alerts.format_message('CLEARED', self.item, 1000)['embeds'][0]
        self.assertIn('EST', cleared['footer']['text'])


if __name__ == '__main__':
    unittest.main()
