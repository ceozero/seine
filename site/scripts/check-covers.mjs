// Validate actual production outputs: every article/locale points to its own usable cover.
import assert from 'node:assert/strict';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { resolve } from 'node:path';
import { parse } from 'yaml';
import sharp from 'sharp';
const seine=JSON.parse(readFileSync('package.json','utf8')).name==='seineminer-site';
const source=seine?'src/content/blog':'blog/content';
const ext=seine?'mdx':'md';
const locales=['en','id','es','de','fr','pt-BR','ru','it','pl','tr','vi','ar','nl','uk','el','ja','ko','th','zh-Hans','zh-Hant'];
const slugs=readdirSync(source).filter(slug=>!parse(readFileSync(`${source}/${slug}/index.${ext}`,'utf8').split('---')[1]).draft);
const base=seine?'https://seineminer.com':'https://bntpool.com';
const prefix=seine?'/assets/blog/covers/':'/blog/covers/';
const seen=new Set(), images=new Set();
for(const lang of locales){
 const locale=lang==='en'?'':lang.toLowerCase()+'/';
 const path=seine?`${locale}blog/`:`blog/${locale}`;
 const index=readFileSync(`dist/${path}index.html`,'utf8');
 const smalls=[...index.matchAll(/<img\b[^>]*src="([^"]+)"/g)].map(m=>m[1]).filter(p=>p.startsWith(prefix));
 assert.equal(smalls.length,slugs.length,`${lang}: every list row needs one cover`);
 assert(smalls.every(p=>p.endsWith('-small.webp')),`${lang}: list src should be the small image`);
 assert.equal(new Set(smalls).size,slugs.length,`${lang}: each article needs its own cover`);
 for(const slug of slugs){
  const html=readFileSync(`dist/${path}${slug}/index.html`,'utf8');
  const social=html.match(/<meta[^>]+property="og:image"[^>]+content="([^"]+)"/)?.[1];
  assert(social?.startsWith(base+prefix+slug+'-'),`${lang}/${slug}: wrong social image`);
  assert(html.includes(`"image":"${social}"`),`${lang}/${slug}: schema image disagrees with social image`);
  assert(smalls.includes(social.replace(base,'').replace(/\.jpg$/,'-small.webp')),`${lang}/${slug}: list and article disagree`);
  const canonical=html.match(/<link[^>]+rel="canonical"[^>]+href="([^"]+)"/)?.[1];
  assert.equal(canonical,`${base}/${path}${slug}/`);
  const alternates=[...html.matchAll(/hreflang="([^"]+)"/g)].map(m=>m[1]);
  assert.equal(new Set(alternates).size,21,`${lang}/${slug}: language alternates changed`);
  if(!seine) assert(html.includes(' 440w,'),`${lang}/${slug}: responsive width descriptor mismatch`);
  if(lang==='en') {
   const local=social.replace(base,'');
   for(const suffix of ['.jpg','.webp','-small.webp']) images.add(local.replace(/\.jpg$/,suffix));
   seen.add(local);
  }
 }
}
let maxSmall=0,maxLarge=0;
for(const path of images){
 const file=resolve('dist','.'+path),{width,height}=await sharp(file).metadata();
 const small=path.endsWith('-small.webp');
 assert.equal(width,small?440:1200,path);
 assert.equal(height,small?248:675,path);
 const size=statSync(file).size;
 assert(size<(small?40_000:250_000),`${path}: byte budget exceeded (${size})`);
 if(small) maxSmall=Math.max(maxSmall,size);else maxLarge=Math.max(maxLarge,size);
}
console.log(JSON.stringify({site:base,articles:slugs.length,locales:locales.length,articlePages:slugs.length*locales.length,images:images.size,maxThumbnailBytes:maxSmall,maxCoverBytes:maxLarge,passed:true},null,2));
