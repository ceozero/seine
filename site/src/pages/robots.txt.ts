import { SITE_URL } from '../lib/site';

export const GET = () => new Response(`User-agent: *\nAllow: /\n\nSitemap: ${SITE_URL}/sitemap.xml\n`);
