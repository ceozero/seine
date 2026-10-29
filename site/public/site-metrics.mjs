// Aggregate intent only. Never send URLs, queries, wallet input or visitor IDs.
export function trafficSource(referrer) {
  if (!referrer) return 'direct';
  try {
    const host = new URL(referrer).hostname.toLowerCase();
    if (['seineminer.com', 'bntpool.com'].includes(host)) return 'internal';
    if (/^(www\.)?google\.(com|[a-z]{2}|co\.[a-z]{2}|com\.[a-z]{2})$/.test(host)
      || ['bing.com', 'www.bing.com', 'duckduckgo.com', 'search.yahoo.com', 'search.brave.com', 'www.baidu.com', 'yandex.com', 'yandex.ru'].includes(host)) return 'search';
    return 'referral';
  } catch { return 'direct'; }
}

export function linkAction(href, base) {
  try {
    const url = new URL(href, base);
    if (url.protocol !== 'https:') return null;
    if (url.hostname === 'bntpool.com') {
      if (/^\/start\/?$/.test(url.pathname)) return 'pool_setup';
      if (/^\/stats\/?$/.test(url.pathname)) return 'worker_stats';
    }
    if (url.hostname === 'seineminer.com') {
      if (/^\/(?:[a-z]{2}(?:-[a-z]+)?\/)?$/.test(url.pathname) && url.hash === '#download') return 'download';
      if (/\/blog\/mine-blocknet-on-(windows|mac|linux)\/$/.test(url.pathname)) return 'setup_guide';
    }
    if (url.hostname === 'github.com' && /^\/zpalmtree\/seine\/releases(?:\/|$)/.test(url.pathname)) return 'download';
  } catch { /* Malformed links must not interfere with navigation. */ }
  return null;
}

export function startSiteMetrics(root, article, locale, env = globalThis) {
  const { location, navigator, document } = env;
  if (!root || !['seineminer.com', 'bntpool.com'].includes(location.hostname)
    || location.protocol !== 'https:' || navigator.doNotTrack === '1'
    || navigator.globalPrivacyControl === true) return () => {};
  const sent = new Set();
  const source = trafficSource(document.referrer);
  function send(action) {
    if (sent.has(action)) return;
    sent.add(action);
    try {
      void env.fetch('https://bntpool.com/api/site-events', {
        method: 'POST', credentials: 'omit', referrerPolicy: 'no-referrer', keepalive: true,
        headers: { 'Content-Type': 'text/plain;charset=UTF-8' },
        body: JSON.stringify({ article, locale, action, source }),
      }).catch(() => {});
    } catch { /* Analytics failure must never affect the page. */ }
  }
  function clicked(event) {
    if (event.type === 'auxclick' && event.button !== 1) return;
    const link = event.target.closest?.('a[href]');
    if (!link || !root.contains(link)) return;
    const action = linkAction(link.href, location.href);
    if (action) send(action);
  }
  send('view');
  root.addEventListener('click', clicked);
  root.addEventListener('auxclick', clicked);
  return () => {
    root.removeEventListener('click', clicked);
    root.removeEventListener('auxclick', clicked);
  };
}
