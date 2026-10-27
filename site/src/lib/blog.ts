import { getCollection, type CollectionEntry } from 'astro:content';
import { DEFAULT_LOCALE, localizePath, type Locale } from '../i18n/locales';
import { SITE_URL } from './site';

export type Post = {
    slug: string;
    locale: Locale;
    entry: CollectionEntry<'blog'>;
    title: string;
    seoTitle?: string;
    description: string;
    date: Date;
    updated: Date;
    tags: string[];
    faq: { q: string; a: string }[];
    related: string[];
    thumbnail: string;
    image: string;
    path: string;
    url: string;
    readingMinutes: number;
};

const CJK = /[\u3400-\u9fff\uf900-\ufaff\u3040-\u30ff\uac00-\ud7af]/g; // Han, kana, Hangul

/** Social cards can't shape Arabic or Thai, so those locales reuse the English card. */
export const cardLocale = (locale: Locale): Locale => (locale === 'ar' || locale === 'th' ? 'en' : locale);

const THAI = /[\u0e00-\u0e7f]/g;

/** Reading time: ~230 words, ~400 CJK characters or ~1,000 Thai characters a minute. */
export function readingMinutes(body: string): number {
    const text = body.replace(/```[\s\S]*?```/g, ' ').replace(/<[^>]+>/g, ' ');
    const cjk = (text.match(CJK) ?? []).length;
    const thai = (text.match(THAI) ?? []).length;
    const words = (text.replace(CJK, ' ').replace(THAI, ' ').match(/[\p{L}\p{N}][\p{L}\p{N}\p{M}'’.-]*/gu) ?? []).length;
    return Math.max(1, Math.round(words / 230 + cjk / 400 + thai / 1000));
}

/**
 * Published posts in a locale, newest first. A published English post without a translation
 * fails the build; scripts/check-content.mjs explains which file is missing or stale.
 */
export async function getPosts(locale: Locale): Promise<Post[]> {
    const all = await getCollection('blog');
    const byId = new Map(all.map((e) => [e.id, e]));
    const sources = all.filter((e) => e.id.endsWith('/index') && !e.data.draft);
    const posts = sources.map((source) => {
        const slug = source.id.slice(0, -'/index'.length);
        const entry = locale === DEFAULT_LOCALE ? source : byId.get(`${slug}/${locale}`);
        if (!entry) throw new Error(`${slug}: missing ${locale} translation (src/content/blog/${slug}/${locale}.mdx)`);
        const date = source.data.date;
        if (!date) throw new Error(`${slug}: front matter needs a date`);
        const path = localizePath(`/blog/${slug}/`, locale);
        const image = source.data.image;
        return {
            slug,
            locale,
            entry,
            title: entry.data.title,
            seoTitle: entry.data.seoTitle,
            description: entry.data.description,
            date,
            updated: source.data.updated ?? date,
            tags: entry.data.tags,
            faq: entry.data.faq,
            related: source.data.related,
            thumbnail: image ?? `/blog/og/${cardLocale(locale)}/${slug}-card.jpg`,
            image: image ? new URL(image, SITE_URL).href : `${SITE_URL}/blog/og/${cardLocale(locale)}/${slug}.jpg`,
            path,
            url: SITE_URL + path,
            readingMinutes: readingMinutes(entry.body ?? ''),
        } satisfies Post;
    });
    return posts.sort((a, b) => b.date.getTime() - a.date.getTime());
}
