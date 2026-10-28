import { readFileSync, readdirSync } from 'node:fs';
const root = new URL('../', import.meta.url);
const best = JSON.parse(readFileSync(new URL('src/data/benchmarks.json', root))).best[0];
for (const slug of ['cpu-mining-2026', 'how-to-mine-blocknet', 'how-crypto-mining-works', 'blocknet-mining-hardware-hashrate']) {
  const folder = new URL(`src/content/blog/${slug}/`, root);
  for (const file of readdirSync(folder).filter(x => x.endsWith('.mdx'))) {
    const source = readFileSync(new URL(file, folder), 'utf8').replace(/,/g, '.').replace(/\u00a0/g, ' ');
    if (!source.includes(best.chip) || !source.includes(`${best.hps} H/s`) || !source.includes(String(best.threads))) throw new Error(`Best measured result drift: ${slug}/${file}; review against benchmarks.json`);
    if (!source.split('\n\n').some(paragraph => paragraph.includes(best.chip) && paragraph.includes(String(best.memoryGiB)) && /1[\s-]*GiB/.test(paragraph))) throw new Error(`Manual benchmark conditions missing: ${slug}/${file}`);
    if (slug === 'how-to-mine-blocknet' && !source.split('\n').some(line => line.includes('seine-linux-x86_64.tar.gz') && line.includes('NVRTC') && line.includes('2.39'))) throw new Error(`Linux runtime requirements missing: ${file}`);
  }
}
console.log('Introductory benchmark and Linux requirement facts agree across all languages');
