# Blog cover system

Both sites use byte-identical `scripts/editorial-cover.mjs` rendering primitives. Update both
copies together. Article assignments live in each site's `scripts/blog-covers.mjs`; the build
fails when a published article has no assigned cover. There is no generic title-card fallback.

## Visual contract

- Canvas: 1200 × 675, paper `#edf2e5`, panel `#fbfcf5`, ink `#123c2a`, green `#237a4e`,
  mid green `#70a980`, lime `#b8ee9d`, rule `#d5dfca`.
- Same corner frame and safe area for illustrations and real screenshots. Preserve geometry:
  contain images, never stretch them or crop out evidence. Avoid tiny labels and repeated titles.
- Illustrations are conceptual, not a protocol specification, measured benchmark or live chart.
  Existing pool charts retain their documented explanatory data. Seine's covers use large simple
  symbols; the precise diagrams and their descriptions remain in the article body.
- Real screenshots retain their real interface and original provenance. A framed screenshot may
  contain interface text; do not synthesize product screens. Covers do not imply current live stats.
- Both lists remain dated rows with images at the inline end. Below 640px the established compact
  text layout remains. Pool article headers continue to display their cover on mobile and desktop.
- List images are decorative beside a linked title and use empty alt text. Pool header covers use
  the localized article title as their short accessible topic description. Instructional in-body
  images keep their existing descriptive, translated alt text.

## Output and compatibility

Generate content-hashed 1200px WebP covers, 440px WebP thumbnails and 1200px JPEG social images.
The social image is also the Article/BlogPosting image. Every language uses the same art.
Thumbnails must be under 40 KB; full covers/social images under 250 KB. New hashes prevent stale
cached covers after an artwork change. Avoid embedding data URLs in public HTML.

Seine generates `public/assets/blog/covers/` and `src/generated/blog-covers.json` in prebuild/predev;
these outputs are ignored by Git. Its legacy `/blog/og/<locale>/<slug>[-card].jpg` routes remain
available and render the new cover. The source front-matter `image` field and original image files
remain for provenance and existing body links; they no longer determine list/social presentation.

Bntpool generates `/blog/covers/` with the embedded frontend build. It keeps article-specific
illustrations and both historical screenshots, now using the shared frame and light background.
Its responsive `srcset` uses the actual 440px and 1200px image widths.

## Source provenance

Seine: the existing desktop-wallet dashboard, transfer-time, first-BNT and wallet-update JPEGs
are released-interface/demo captures documented in their original editorial research. The Seine
dashboard WebP is the existing public, redacted product capture. No new private/account data is used.
Bntpool: see `frontend/blog/images/README.md` for screenshot and chart provenance. The common frame
and Seine's symbolic illustrations are repository-native SVG code, rasterized with Sharp at build.

## Review and safeguards

Run the existing editorial checks and production build, then `node scripts/check-covers.mjs`.
The output check validates all published assignments, dimensions, file budgets, responsive URLs
and social metadata. Inspect a real list and article on desktop/mobile, RTL and a long-title
language. Inspect all covers in the contact-sheet showcase, with real built assets. Do not add
fake loading/error controls to a static blog; image loading/failure and narrow text wrapping are
its relevant edge cases. Reuse the stable review gallery at:
`http://localhost:8874/blog-covers/`.

Start the gallery when needed:
`python3 -m http.server 8874 --directory /home/zp/Code/blocknet/showcases/blog-i18n`
