// Social cards for posts: /blog/og/<locale>/<slug>.jpg (1200x630) and <slug>-card.jpg (600x315).
// Paper ground with the title on the left and the hero render beside it (never under text).
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import type { APIContext } from 'astro';
import satori from 'satori';
import sharp from 'sharp';
import { LOCALES, type Locale } from '../../../../i18n/locales';
import { cardLocale, getPosts, type Post } from '../../../../lib/blog';

const W = 1200;
const H = 630;
// Paths are relative to site/, where every build runs (bundling breaks import.meta.url paths).
const fontFile = (pkg: string, file: string) => readFile(resolve('node_modules/@fontsource', pkg, 'files', file));
const heroFile = resolve('src/assets/hero-square.webp');
// Fallback face for glyphs Instrument Sans lacks (CJK, Cyrillic, Greek, Vietnamese, accented Latin),
// subset to the title's characters. Arabic and Thai reuse the English card (see cardLocale).
const FALLBACK_FAMILY: Partial<Record<Locale, string>> = { 'zh-Hans': 'Noto Sans SC', 'zh-Hant': 'Noto Sans TC', ja: 'Noto Sans JP', ko: 'Noto Sans KR' };
const CJK_LOCALES: Locale[] = ['zh-Hans', 'zh-Hant', 'ja', 'ko'];

export async function getStaticPaths() {
    const paths = [];
    for (const l of LOCALES) {
        if (cardLocale(l.code) !== l.code) continue;
        for (const post of await getPosts(l.code)) {
            for (const name of [post.slug, `${post.slug}-card`]) paths.push({ params: { locale: l.code, name }, props: { post } });
        }
    }
    return paths;
}

let shared: Promise<{ fonts: Parameters<typeof satori>[1]['fonts']; hero: string }> | undefined;
function loadShared() {
    shared ??= (async () => {
        const hero = await sharp(await readFile(heroFile)).resize(H, H).jpeg({ quality: 86 }).toBuffer();
        return {
            hero: `data:image/jpeg;base64,${hero.toString('base64')}`,
            fonts: [
                { name: 'Instrument Sans', data: await fontFile('instrument-sans', 'instrument-sans-latin-600-normal.woff'), weight: 600, style: 'normal' },
                { name: 'Instrument Sans', data: await fontFile('instrument-sans', 'instrument-sans-latin-700-normal.woff'), weight: 700, style: 'normal' },
                { name: 'IBM Plex Mono', data: await fontFile('ibm-plex-mono', 'ibm-plex-mono-latin-500-normal.woff'), weight: 500, style: 'normal' },
            ],
        };
    })();
    return shared;
}

/** A subset of `family` covering just `text`, from the Google Fonts text API (build time only). */
async function fallbackFont(family: string, text: string) {
    const css = await (await fetch(`https://fonts.googleapis.com/css2?family=${family.replace(/ /g, '+')}:wght@600&text=${encodeURIComponent(text)}`)).text();
    const url = css.match(/src: url\(([^)]+)\)/)?.[1];
    if (!url) throw new Error(`no ${family} subset for OG card: ${css.slice(0, 200)}`);
    return { name: family, data: await (await fetch(url)).arrayBuffer(), weight: 600 as const, style: 'normal' as const };
}

const el = (type: string, style: Record<string, unknown>, children?: unknown) => ({ type, props: { style, children } });

async function card(post: Post) {
    const { fonts, hero } = await loadShared();
    const family = post.locale === 'en' ? undefined : FALLBACK_FAMILY[post.locale] ?? 'Noto Sans';
    const allFonts = family ? [...fonts, await fallbackFont(family, post.title)] : fonts;
    const titleSize = post.title.length > (CJK_LOCALES.includes(post.locale) ? 22 : 48) ? 50 : 60;
    const svg = await satori(
        el('div', { width: W, height: H, display: 'flex', background: '#F4F6F5', fontFamily: `Instrument Sans${family ? `, ${family}` : ''}` }, [
            el('div', { flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', padding: '64px 56px 56px 64px', borderRight: '1px solid #D7DDDC' }, [
                el('div', { display: 'flex', alignItems: 'baseline', fontSize: 34, fontWeight: 700, color: '#101314', letterSpacing: '-0.02em' },
                    ['seine', el('span', { color: '#4E9A00' }, '.')]),
                el('div', { display: 'flex', fontSize: titleSize, fontWeight: 600, lineHeight: 1.08, letterSpacing: '-0.03em', color: '#101314' }, post.title),
                el('div', { display: 'flex', fontFamily: 'IBM Plex Mono', fontSize: 20, color: '#5B6366' }, 'seineminer.com'),
            ]),
            { type: 'img', props: { src: hero, width: H, height: H, style: { width: H, height: H } } },
        ]),
        { width: W, height: H, fonts: allFonts },
    );
    return sharp(Buffer.from(svg));
}

export async function GET({ params, props }: APIContext<{ post: Post }>) {
    const image = await card(props.post);
    const sized = params.name!.endsWith('-card') ? image.resize(W / 2, H / 2) : image;
    const jpg = await sized.jpeg({ quality: 84, mozjpeg: true }).toBuffer();
    return new Response(new Uint8Array(jpg), { headers: { 'Content-Type': 'image/jpeg' } });
}
