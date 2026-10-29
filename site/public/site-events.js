import { startSiteMetrics } from './site-metrics.mjs';
const root = document.querySelector('[data-metrics-article]');
if (root) startSiteMetrics(root, root.dataset.metricsArticle, root.dataset.metricsLocale);
