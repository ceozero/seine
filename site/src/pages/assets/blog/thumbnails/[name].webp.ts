// Blog cards render at 220 CSS pixels. Keep a 2x copy instead of downloading
// the full article screenshot; the original remains available inside the post.
import { readdir } from 'node:fs/promises';
import { resolve } from 'node:path';
import type { APIContext } from 'astro';
import sharp from 'sharp';

const sourceDir = resolve('public/assets/blog');

export async function getStaticPaths() {
    return (await readdir(sourceDir))
        .filter((name) => /\.(png|jpe?g|webp)$/i.test(name))
        .map((name) => ({ params: { name } }));
}

export async function GET({ params }: APIContext) {
    const image = await sharp(resolve(sourceDir, params.name!))
        .resize({ width: 440, withoutEnlargement: true })
        .webp({ quality: 80 }).toBuffer();
    return new Response(new Uint8Array(image), { headers: { 'Content-Type': 'image/webp' } });
}
