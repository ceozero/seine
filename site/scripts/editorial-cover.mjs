// Shared with the sibling site's scripts/editorial-cover.mjs. Keep byte-identical.
// Language-neutral cover art, separate from instructional figures inside articles.
import sharp from 'sharp';
import { createHash } from 'node:crypto';
import { mkdir, writeFile } from 'node:fs/promises';

export const palette = { paper: '#edf2e5', panel: '#fbfcf5', ink: '#123c2a', green: '#237a4e', mid: '#70a980', lime: '#b8ee9d', rule: '#d5dfca' };
const { paper, panel, ink, green, mid, lime, rule } = palette;
const path = (d, color = green, width = 7, extra = '') => `<path d="${d}" fill="none" stroke="${color}" stroke-width="${width}" stroke-linecap="round" stroke-linejoin="round" ${extra}/>`;
const rect = (x,y,w,h,fill=panel,r=18,extra='') => `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}" fill="${fill}" ${extra}/>`;
const circle = (x,y,r,fill=lime,extra='') => `<circle cx="${x}" cy="${y}" r="${r}" fill="${fill}" ${extra}/>`;
const check = path('M-28 0 -7 21 32 -24');
// Every symbol uses a 200x200 coordinate box, centered at the origin.
const symbols = {
  block: `<path d="M0 -85 78 -43 0 0 -78 -43Z" fill="${lime}"/><path d="M-78 -43 0 0V87L-78 43Z" fill="${mid}"/><path d="M0 0 78 -43V43L0 87Z" fill="${green}"/>${path('M0 -85V0M-78 -43 0 0 78 -43',panel,3)}`,
  wallet: `${rect(-90,-59,180,129,ink)}${path('M-78 -59V-80H63V-59',mid)}${rect(23,-13,73,49,lime,10)}${circle(46,11,7,green)}`,
  coin: `${circle(0,0,86,lime)}${circle(0,0,65,'none',`stroke="${green}" stroke-width="5"`)}<text x="0" y="15" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="42" font-weight="600" fill="${ink}">BNT</text>`,
  miner: `${rect(-92,-75,184,131,ink,15)}${path('M-65 26V-11M-32 26V-36M0 26V-21M32 26V-49M64 26V-34',lime,10)}${path('M0 58V82M-45 83H45',green,9)}`,
  chip: `${[-65,-32,0,32,65].map(n=>path(`M${n} -95V-76M${n} 76V95M-95 ${n}H-76M76 ${n}H95`,mid,6)).join('')}${rect(-74,-74,148,148,ink,20)}${rect(-43,-43,86,86,lime,10)}`,
  memory: `${rect(-96,-46,192,92,green,12)}${[-63,-16,31].map(x=>rect(x,-26,32,46,ink,5)).join('')}${[-75,-45,-15,15,45,75].map(x=>rect(x,46,14,19,lime,2)).join('')}`,
  gpu: `${rect(-94,-57,188,114,ink,13)}${[-45,45].map(x=>`${circle(x,0,33,mid)}${circle(x,0,13,lime)}${path(`M${x} -30V-16M${x} 16V30M${x-30} 0H${x-16}M${x+16} 0H${x+30}`,ink,6)}`).join('')}${path('M-72 59V80H73',mid,9)}`,
  server: `${[-70,-15,40].map(y=>`${rect(-72,y,144,42,ink,9)}${circle(-48,y+21,7,lime)}${path(`M-20 ${y+21}H46`,mid,5)}`).join('')}`,
  shield: `<path d="M0 -89 76 -57V1Q76 55 0 91Q-76 55 -76 1V-57Z" fill="${ink}"/>${path('M-31 -3 -8 20 34 -28',lime,10)}`,
  lock: `${path('M-45 -14V-48A45 45 0 0 1 45 -48V-14',green,14)}${rect(-68,-18,136,104,ink,16)}${circle(0,24,13,lime)}${path('M0 36V55',lime,9)}`,
  key: `${circle(-44,-20,37,'none',`stroke="${green}" stroke-width="16"`)}${path('M-12 0 65 70M38 43 59 22M56 61 77 40',green,16)}`,
  document: `${rect(-67,-89,134,178,panel,14,`stroke="${green}" stroke-width="6"`)}${[-45,-12,21,54].map((y,i)=>path(`M-39 ${y}H${i===3?9:39}`,mid,7)).join('')}`,
  message: `${rect(-88,-65,176,118,ink,22)}<path d="M-53 48V88L-9 48Z" fill="${ink}"/>${[-40,0,40].map(x=>circle(x,-5,9,lime)).join('')}`,
  eye: `<path d="M-95 0Q0 -110 95 0Q0 110 -95 0Z" fill="${lime}" stroke="${green}" stroke-width="5"/>${circle(0,0,31,ink)}${circle(9,-8,9,panel)}`,
  ring: `${circle(0,0,65,'none',`stroke="${mid}" stroke-width="4"`)}${Array.from({length:8},(_,i)=>{const a=i*Math.PI/4;return circle(Math.cos(a)*65,Math.sin(a)*65,17,i===2?green:lime,`stroke="${green}" stroke-width="3"`)}).join('')}`,
  network: `${path('M0 0 -66 -58M0 0 70 -52M0 0 -64 62M0 0 70 62',mid,6)}${circle(0,0,30,ink)}${[[-66,-58],[70,-52],[-64,62],[70,62]].map(([x,y])=>circle(x,y,22,lime,`stroke="${green}" stroke-width="4"`)).join('')}`,
  clock: `${circle(0,0,83,panel,`stroke="${green}" stroke-width="7"`)}${path('M0 -52V0L36 22',ink,10)}${circle(0,0,8,ink)}`,
  download: `${path('M0 -82V35M-35 0 0 35 35 0',green,13)}${path('M-79 29V79H79V29',ink,11)}`,
  update: `${path('M-73 -19A77 77 0 0 1 62 -48L77 -20M77 -20V-66M77 -20H31M73 19A77 77 0 0 1 -62 48L-77 20M-77 20V66M-77 20H-31',green,10)}`,
  sliders: `${[-50,0,50].map((x,i)=>`${path(`M${x} -82V82`,mid,8)}${rect(x-16,[-45,25,-5][i]-17,32,34,ink,9)}`).join('')}`,
  chart: `${path('M-85 -75V80H85',mid,5)}${path('M-65 48 -32 15 -6 34 25 -25 51 -8 83 -60',green,9)}${circle(83,-60,9,green)}`,
  power: `${path('M0 -85V-9',green,13)}${path('M-43 -55A76 76 0 1 0 43 -55',ink,13)}`,
  plug: `${path('M-33 -84V-30M33 -84V-30',green,11)}${rect(-56,-30,112,70,ink,15)}${path('M0 40V81',mid,13)}`,
  search: `${circle(-16,-16,56,'none',`stroke="${green}" stroke-width="11"`)}${path('M24 24 82 82',ink,17)}`,
  check: `${circle(0,0,78,lime)}${check}`,
  pause: `${circle(0,0,80,ink)}${rect(-36,-39,23,78,lime,5)}${rect(13,-39,23,78,lime,5)}`,
  balance: `${path('M0 -81V77M-45 80H45M-78 -44H78M-58 -43 -86 18H-30L-58 -43M58 -43 30 18H86L58 -43',green,7)}${circle(0,-44,10,ink)}`,
  leaf: `<path d="M-61 57Q-95 -52 77 -82Q96 70 -61 57Z" fill="${lime}" stroke="${green}" stroke-width="6"/>${path('M-75 85 42 -43M-27 28 -31 -23M-3 5H40',green,7)}`,
  laptop: `${rect(-77,-70,154,116,ink,12)}${rect(-61,-53,122,80,lime,3)}${path('M-92 65H92L77 46H-77Z',green,10)}`,
};

export function scene({ main, left, right, link = 'flow' }) {
  for (const id of [main,left,right].filter(Boolean)) if (!symbols[id]) throw new Error(`Unknown cover symbol: ${id}`);
  const item=(id,x,y,s)=>`<g transform="translate(${x} ${y}) scale(${s})">${symbols[id]}</g>`;
  const connector = link === 'orbit'
    ? path('M285 285Q600 90 915 285M285 395Q600 590 915 395',mid,5,'stroke-dasharray="10 12"')
    : link === 'swap'
      ? path('M360 270H840M810 245 840 270 810 295M840 405H360M390 380 360 405 390 430',mid,7)
      : path('M350 337H420M400 317 420 337 400 357M780 337H850M830 317 850 337 830 357',mid,7);
  return `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="675" viewBox="0 0 1200 675">${rect(0,0,1200,675,paper,0)}${connector}${circle(600,337,171,panel,`stroke="${rule}" stroke-width="3"`)}${item(main,600,337,1.38)}${left?item(left,235,337,.87):''}${right?item(right,965,337,.87):''}</svg>`;
}

/** Common paper, frame and safe area for both illustrations and real captures. */
export async function renderCover(source, { screenshot = false } = {}) {
  const background = Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="675">${rect(0,0,1200,675,paper,0)}${path('M40 100V40H100M1100 40H1160V100M40 575V635H100M1100 635H1160V575',mid,3)}</svg>`);
  // Contain preserves screenshot evidence and chart geometry; never stretch or crop.
  const artwork = await sharp(source).resize(screenshot ? 1032 : 1080, screenshot ? 531 : 567, { fit:'contain', background:paper }).png().toBuffer();
  const width = screenshot ? 1032 : 1080, height = screenshot ? 531 : 567;
  const layers = [];
  if(screenshot) layers.push({input:Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="675">${rect(72,60,1056,555,panel,14,`stroke="${rule}" stroke-width="2"`)}</svg>`)});
  layers.push({input:artwork,left:(1200-width)/2,top:(675-height)/2});
  return sharp(background).composite(layers).png().toBuffer();
}

export async function writeCover(slug, rendered, output, prefix) {
  await mkdir(output,{recursive:true});
  const version=createHash('sha256').update(rendered).digest('hex').slice(0,12);
  const name=`${slug}-${version}`;
  const versions = [[`${name}.webp`,1200,'webp',86],[`${name}-small.webp`,440,'webp',80],[`${name}.jpg`,1200,'jpeg',88]];
  for(const [file,width,format,quality] of versions) await writeFile(new URL(file,output), await sharp(rendered).resize({width}).toFormat(format,{quality}).toBuffer());
  return { src:`${prefix}${name}.webp`, small:`${prefix}${name}-small.webp`, social:`${prefix}${name}.jpg` };
}
