import rss from '@astrojs/rss';
import type { APIContext } from 'astro';
import { localeDef, localeFromParam, localeStaticPaths, localizePath } from '../../../i18n/locales';
import { useTranslations } from '../../../i18n/ui';
import { getPosts } from '../../../lib/blog';
import { SITE_URL } from '../../../lib/site';

export const getStaticPaths = localeStaticPaths;

export async function GET({ params }: APIContext) {
    const locale = localeFromParam(params.lang);
    const t = useTranslations(locale);
    const posts = await getPosts(locale);
    return rss({
        title: t('blogRssTitle'),
        description: t('blogMetaDescription'),
        site: SITE_URL + localizePath('/blog/', locale),
        customData: `<language>${localeDef(locale).htmlLang}</language>`,
        items: posts.map((p) => ({ title: p.title, description: p.description, link: p.url, pubDate: p.date })),
    });
}
