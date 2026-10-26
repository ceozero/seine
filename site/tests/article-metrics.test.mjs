import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import assert from 'node:assert/strict';
const script = readFileSync(new URL('../public/article-metrics.js', import.meta.url), 'utf8');
function run({ hostname = 'bntpool.com', navigator = {} } = {}) {
  const calls = [], handlers = {};
  const article = { dataset: { metricsArticle: 'track-your-miner-on-bntpool', metricsLocale: 'en' }, contains: link => !link.outside,
    addEventListener: (name, callback) => { handlers[name] = callback; } };
  vm.runInNewContext(script, { location: { hostname, protocol: 'https:', href: `https://${hostname}/blog/example/?private=secret` }, navigator,
    document: { querySelector: () => article }, URL, fetch: (...args) => { calls.push(args); return Promise.resolve({}); } });
  return { calls, click(href, outside = false, type = 'click', button = 0) {
    handlers[type]?.({type, button, target: {closest: () => ({href, outside})}});
  } };
}
test('records only fixed payload and meaningful article actions, once per page', () => {
  const {calls, click} = run();
  click('https://bntpool.com/start?wallet=secret');
  click('https://bntpool.com/start');
  click('https://seineminer.com/es/#download');
  click('https://seineminer.com/#download', false, 'auxclick', 1);
  click('https://bntpool.com/blog/other/');
  click('https://bntpool.com.evil.test/start');
  assert.deepEqual(calls.map(([, opts]) => JSON.parse(opts.body).action), ['view','pool_setup','download']);
  for (const [endpoint, opts] of calls) {
    assert.equal(endpoint, 'https://bntpool.com/api/site-events');
    assert.equal(opts.credentials, 'omit'); assert.equal(opts.referrerPolicy, 'no-referrer');
    assert.deepEqual(Object.keys(JSON.parse(opts.body)).sort(), ['action','article','locale']);
    assert.ok(!opts.body.includes('secret'));
  }
});
test('local previews and browser privacy signals disable collection', () => {
  for (const opts of [{hostname:'localhost'}, {navigator:{doNotTrack:'1'}}, {navigator:{globalPrivacyControl:true}}]) {
    assert.equal(run(opts).calls.length, 0);
  }
});
test('ignores unrelated and unsafe links; tracks direct Seine release intent', () => {
  const {calls, click} = run();
  click('https://bntpool.com/start', true);
  click('http://bntpool.com/start');
  click('https://github.com/other/repo/releases');
  click('https://bntpool.com/start', false, 'auxclick', 2);
  assert.equal(calls.length, 1);
  click('https://github.com/zpalmtree/seine/releases/latest');
  assert.equal(JSON.parse(calls[1][1].body).action, 'download');
});
