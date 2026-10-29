import test from 'node:test';
import assert from 'node:assert/strict';
import { startSiteMetrics, trafficSource, linkAction } from '../public/site-metrics.mjs';
function run({ hostname = 'bntpool.com', navigator = {}, throws = false } = {}) {
  const calls = [], handlers = {};
  const root = { contains: link => !link.outside,
    addEventListener: (name, fn) => { handlers[name] = fn; },
    removeEventListener: name => { delete handlers[name]; } };
  const stop = startSiteMetrics(root, 'home', 'en', {
    location: { hostname, protocol: 'https:', href: `https://${hostname}/?wallet=secret` }, navigator,
    document: { referrer: 'https://www.google.com/search?q=secret' },
    fetch: (...args) => { if (throws) throw Error('blocked'); calls.push(args); return Promise.resolve({}); },
  });
  return { calls, stop, click(href, outside = false, type = 'click', button = 0) {
    handlers[type]?.({ type, button, target: { closest: () => ({ href, outside }) } });
  } };
}
test('counts fixed actions once per page, without private input or referring URLs', () => {
  const { calls, click, stop } = run();
  click('https://bntpool.com/start?wallet=secret'); click('https://bntpool.com/start');
  click('https://seineminer.com/es/#download');
  click('https://seineminer.com/blog/mine-blocknet-on-windows/');
  click('https://bntpool.com/stats?address=secret');
  click('https://bntpool.com.evil.test/start');
  assert.deepEqual(calls.map(([, opts]) => JSON.parse(opts.body).action), ['view', 'pool_setup', 'download', 'setup_guide', 'worker_stats']);
  for (const [endpoint, opts] of calls) {
    assert.equal(endpoint, 'https://bntpool.com/api/site-events');
    assert.equal(opts.credentials, 'omit'); assert.equal(opts.referrerPolicy, 'no-referrer');
    assert.deepEqual(Object.keys(JSON.parse(opts.body)).sort(), ['action', 'article', 'locale', 'source']);
    assert.equal(JSON.parse(opts.body).source, 'search');
    assert.ok(!opts.body.includes('secret'));
  }
  stop(); click('https://bntpool.com/start'); assert.equal(calls.length, 5);
});
test('local previews and privacy signals disable collection; blocked collection never throws', () => {
  for (const opts of [{ hostname: 'localhost' }, { navigator: { doNotTrack: '1' } }, { navigator: { globalPrivacyControl: true } }]) {
    assert.equal(run(opts).calls.length, 0);
  }
  assert.doesNotThrow(() => run({ throws: true }).click('https://bntpool.com/start'));
});
test('ignores outside, unsafe and right-click links; middle-click downloads work', () => {
  const { calls, click } = run();
  click('https://bntpool.com/start', true);
  click('http://bntpool.com/start'); click('https://github.com/other/repo/releases');
  click('https://bntpool.com/start', false, 'auxclick', 2);
  assert.equal(calls.length, 1);
  click('https://github.com/zpalmtree/seine/releases/latest', false, 'auxclick', 1);
  assert.equal(JSON.parse(calls[1][1].body).action, 'download');
  assert.equal(linkAction('https://seineminer.com/blog/example/#download'), null);
});
test('source classification is bounded and does not mistake suffix attacks for search', () => {
  for (const [ref, source] of [['', 'direct'], ['bad', 'direct'], ['https://www.google.co.uk/search?q=secret', 'search'], ['https://www.google.com.evil.test/', 'referral'], ['https://bntpool.com/start?wallet=secret', 'internal'], ['https://example.com/', 'referral']]) assert.equal(trafficSource(ref), source);
});
