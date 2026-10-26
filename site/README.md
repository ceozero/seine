# seineminer.com

Static Astro site for seineminer.com, in 20 languages (English at `/`, translations at
`/<locale>/`), hosted on Cloudflare Pages (project `seineminer`). The locale list lives in
`src/i18n/locales.ts`.

```sh
cd site
npm ci
npm run dev        # http://localhost:8791
npm run build      # syncs brand assets, runs content checks, writes dist/
npm run check      # editorial and translation checks only
```

- `src/pages/[...lang]/`: every page, once per locale (`index.astro` is the landing page,
  `blog/` the blog and RSS).
- `src/i18n/`: locales and interface strings. All catalogs are checked against English.
- `src/content/blog/<slug>/`: a post's English source (`index.mdx`) and its translations
  (`<locale>.mdx`, including `zh-Hans.mdx` and `pt-BR.mdx`). How to write, translate and publish posts is in
  [`editorial/README.md`](editorial/README.md).
- `src/pages/blog/og/`: generated 1200x630 social cards per post and locale.
- `src/styles/site.css`: design tokens and landing styles; `blog.css`: blog pages.
- Brand files (icon, social card) are copied from `docs/assets/brand` at build time, so the
  site and README stay in sync.
- Fonts are self-hosted from `@fontsource` packages; Google Fonts is blocked in mainland China.

After a deploy, `npm run indexnow` tells Bing and the other IndexNow engines about every URL in
the sitemap (CI does this automatically). The key file is `public/<key>.txt`.

Pushes to `master` that touch the site or brand assets deploy through
`.github/workflows/site.yml`, which needs the `CLOUDFLARE_API_TOKEN` (Pages: Edit) and
`CLOUDFLARE_ACCOUNT_ID` secrets. Manual deploy from `site/`:
`npm run build && npx wrangler@3 pages deploy dist --project-name seineminer --branch main`.
