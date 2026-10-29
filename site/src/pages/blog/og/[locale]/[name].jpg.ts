// Preserve existing social-image URLs with the same language-neutral cover system.
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import type { APIContext } from 'astro';
import sharp from 'sharp';
import { LOCALES } from '../../../../i18n/locales';
import { cardLocale, getPosts, type Post } from '../../../../lib/blog';

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
const cache = new Map<string, Promise<Buffer>>();
export async function GET({ params, props }: APIContext<{ post: Post }>) {
    const small = params.name!.endsWith('-card');
    const path = new URL(props.post.image).pathname;
    const key = `${path}:${small}`;
    if (!cache.has(key)) cache.set(key, (async () => {
        const source = await readFile(resolve('public', `.${path}`));
        return small ? sharp(source).resize(600, 338).jpeg({ quality: 84 }).toBuffer() : source;
    })());
    return new Response(new Uint8Array(await cache.get(key)!), { headers: { 'Content-Type': 'image/jpeg' } });
}
