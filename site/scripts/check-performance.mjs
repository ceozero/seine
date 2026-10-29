// Check the built pages, so bundling/config changes cannot silently undo first-load savings.
import assert from 'node:assert/strict';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { resolve } from 'node:path';
import { gzipSync } from 'node:zlib';
import sharp from 'sharp';

const dist = resolve('dist');
const home = readFileSync(resolve(dist, 'index.html'), 'utf8');
const blog = readFileSync(resolve(dist, 'blog/index.html'), 'utf8');
const article = readFileSync(resolve(dist, 'blog/how-to-mine-blocknet/index.html'), 'utf8');
for (const html of [home, blog, article]) {
    assert(!/<link\b[^>]*rel="stylesheet"/.test(html), 'First paint must not wait for external CSS');
    assert(!html.includes('/assets/brand/icon.svg'), 'Use a display-sized logo');
    assert.match(html, /rel="preload"[^>]+as="font"[^>]+crossorigin/);
}
assert(gzipSync(home).length < 15_000, 'Keep the inlined homepage below 15 KB gzip');

const fonts = [...new Set([...home.matchAll(/\/_astro\/[^"\s()]+\.woff2/g)].map(m => m[0]))]
    .filter(path => /-latin-(?:wght|400|500)-normal\./.test(path));
assert.equal(fonts.length, 3, 'English pages need one variable sans and two mono weights');
const fontBytes = fonts.reduce((sum, path) => sum + statSync(resolve(dist, `.${path}`)).size, 0);
assert(fontBytes < 61_000, `Latin font budget exceeded: ${fontBytes}`);

const thumbnails = readdirSync(resolve(dist, 'assets/blog/thumbnails'));
assert(thumbnails.length > 0);
for (const name of thumbnails) {
    const file = resolve(dist, 'assets/blog/thumbnails', name);
    const { width } = await sharp(file).metadata();
    assert(width <= 440, `${name}: thumbnail exceeds 2x display width`);
    assert(statSync(file).size < 40_000, `${name}: thumbnail exceeds 40 KB`);
}
assert.match(blog, /\/assets\/blog\/covers\/[^" ]+-small\.webp/);
console.log(`Performance budgets passed: ${gzipSync(home).length} B homepage gzip, ${fontBytes} B Latin fonts, ${thumbnails.length} optimized thumbnails`);
