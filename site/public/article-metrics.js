// Aggregate article events only. No storage, cookies, identifiers, queries or referrers.
(() => {
  if (!['seineminer.com', 'bntpool.com'].includes(location.hostname)
      || location.protocol !== 'https:' || navigator.doNotTrack === '1'
      || navigator.globalPrivacyControl === true) return;
  const article = document.querySelector('article[data-metrics-article]');
  if (!article) return;
  const sent = new Set();
  function send(action) {
    if (sent.has(action)) return;
    sent.add(action);
    void fetch('https://bntpool.com/api/site-events', {
      method: 'POST', credentials: 'omit', referrerPolicy: 'no-referrer', keepalive: true,
      headers: { 'Content-Type': 'text/plain;charset=UTF-8' },
      body: JSON.stringify({ article: article.dataset.metricsArticle, locale: article.dataset.metricsLocale, action }),
    }).catch(() => {}); // Measurement must never interrupt reading or navigation.
  }
  send('view');
  function clicked(event) {
    if (event.type === 'auxclick' && event.button !== 1) return;
    const link = event.target.closest?.('a[href]');
    if (!link || !article.contains(link)) return;
    const url = new URL(link.href, location.href);
    if (url.protocol !== 'https:') return;
    if (url.hostname === 'bntpool.com' && /^\/start\/?$/.test(url.pathname)) send('pool_setup');
    else if ((url.hostname === 'seineminer.com' && url.hash === '#download')
      || (url.hostname === 'github.com' && /^\/zpalmtree\/seine\/releases(?:\/|$)/.test(url.pathname))) send('download');
  }
  article.addEventListener('click', clicked);
  article.addEventListener('auxclick', clicked);
})();
