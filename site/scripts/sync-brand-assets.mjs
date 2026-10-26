// Copy brand assets from the repo's docs/assets/brand into public/assets/brand (gitignored),
// so the site and README always use the same files.
import { copyFileSync, mkdirSync } from 'node:fs';

const FILES = ['icon.svg', 'icon-32.png', 'icon-180.png', 'icon-512.png', 'social-card.jpg'];
const from = new URL('../../docs/assets/brand/', import.meta.url);
const to = new URL('../public/assets/brand/', import.meta.url);
mkdirSync(to, { recursive: true });
for (const f of FILES) copyFileSync(new URL(f, from), new URL(f, to));
console.log(`synced ${FILES.length} brand assets`);
