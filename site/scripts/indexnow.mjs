// Tell IndexNow search engines (Bing, Yandex, Seznam, Naver) about every URL in the built
// sitemap. Run after a deploy: `npm run indexnow`. The key file lives in public/<key>.txt.
import { readdirSync, readFileSync } from 'node:fs';

const HOST = 'seineminer.com';
const keyFile = readdirSync(new URL('../public/', import.meta.url)).find((f) => /^[0-9a-f]{32}\.txt$/.test(f));
if (!keyFile) throw new Error('no IndexNow key file in public/');
const key = keyFile.slice(0, -4);
const sitemap = readFileSync(new URL('../dist/sitemap.xml', import.meta.url), 'utf8');
const urlList = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1]);

const res = await fetch('https://api.indexnow.org/indexnow', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
    body: JSON.stringify({ host: HOST, key, keyLocation: `https://${HOST}/${keyFile}`, urlList }),
});
console.log(`IndexNow: ${res.status} ${res.statusText} for ${urlList.length} URLs`);
// 200 and 202 mean accepted; anything else is worth a look but shouldn't fail a deploy.
if (![200, 202].includes(res.status)) console.log(await res.text());
