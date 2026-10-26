import { LOCALES, localizePath } from '../i18n/locales';
import { getPosts } from '../lib/blog';
import { SITE_URL, isoDate } from '../lib/site';

// Every page exists in every locale, so each <url> lists all of its translations as
// hreflang alternates. lastmod comes from post dates only; the home page omits it.
export async function GET() {
    const pages: { path: string; lastmod?: Date }[] = [{ path: '/' }];
    const posts = await getPosts('en');
    pages.push({ path: '/blog/', lastmod: posts.length ? new Date(Math.max(...posts.map((p) => +p.updated))) : undefined });
    for (const p of posts) pages.push({ path: `/blog/${p.slug}/`, lastmod: p.updated });

    const alternates = (path: string) =>
        LOCALES.map((l) => `<xhtml:link rel="alternate" hreflang="${l.htmlLang}" href="${SITE_URL}${localizePath(path, l.code)}"/>`).join('')
        + `<xhtml:link rel="alternate" hreflang="x-default" href="${SITE_URL}${path}"/>`;
    const urls = pages.flatMap(({ path, lastmod }) => LOCALES.map((l) =>
        `<url><loc>${SITE_URL}${localizePath(path, l.code)}</loc>${lastmod ? `<lastmod>${isoDate(lastmod)}</lastmod>` : ''}${alternates(path)}</url>`));
    const xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        + '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + `<url><loc>${SITE_URL}/privacy/</loc></url>\n` + urls.join('\n') + '\n</urlset>\n';
    return new Response(xml, { headers: { 'Content-Type': 'application/xml; charset=utf-8' } });
}
