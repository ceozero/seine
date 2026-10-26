# Main sites and blogs: SEO audit, October 25, 2026

Scope: seineminer.com and bntpool.com, including
homepages, downloads, the eight public pool tools and all 20 blog languages.
No rentals, benchmark jobs, competitor comparison or outreach.

## Observations

- Read-only production crawl: 561 Seine sitemap URLs and 228 pool sitemap URLs.
  All 789 returned HTTP 200, with a nonempty title and description, self-canonical
  URL, and no noindex response/header. No broken fragments among links to crawled
  pages; no page lacked an inbound link in the crawled graph.
- Blog and Seine language alternates resolve within the sitemap and reciprocate
  the source language. All descriptions are unique within each site. Six title
  pairs match between Simplified and Traditional Chinese because those titles
  legitimately use the same characters; retain their separate language URLs.
- Both robots files advertise the sitemap. Pool API URLs are disallowed; public
  pages are crawlable. Arbitrary missing paths return real HTTP 404 responses.
- Eight pool app routes send an empty root div in the initial HTML. Their title,
  description and canonical already exist server-side, but no body headings or
  navigation links are available until JavaScript runs.
- Reproduced in shared Windows Chrome: loading `/`, then using Get Started changes
  the URL to `/start` while canonical and description remain those of `/` even
  after the route finishes rendering. App navigation only updated document.title.
- Search Console at approximately 7:42 PM EDT: both properties still show
  "Processing data, please check again in a day or so" for performance/indexing.
  This is unavailable evidence, not zero traffic. No current query cannibalization,
  CTR opportunity or ranking improvement can be established.

## Changes

- Pool route metadata has one JSON source shared by the Rust response and browser.
  Canonical, robots, descriptions and social cards follow app navigation and
  Back/Forward. English titles use the shared route title; translated titles keep
  the existing catalogs. Query parameters remain excluded from canonical URLs.
- Public pool pages include real initial HTML: a route heading, description,
  relevant existing guides, navigation to every public tool, and setup steps on
  `/start`. This content is available to all visitors and replaced by React when
  ready. There is no crawler-specific response, fake live metric or hidden copy.
  The text explains that charts and miner lookups need JavaScript.
- Seine's existing download, setup and performance sections link directly to
  seven relevant guides in all 20 languages. Link text reuses each published
  translation's title. Existing operating-system downloads and GitHub links remain.
- Keyword maps now distinguish the main sites' download/dashboard/tool jobs from
  detailed article jobs. No article was retargeted based on unavailable reports.

## Sources and limits

- Google: https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics
  (server/pre-rendering, crawlable links, page-specific metadata, canonical consistency).
- Google: https://developers.google.com/search/docs/appearance/title-link
  (descriptive distinct titles; no hard character-count ranking rule).
- Repo sources: pool `apps/blocknet-pool-api/src/ui.rs`, `frontend/src/App.tsx`,
  `frontend/src/lib/routes.ts`, `frontend/src/pages/StartPage.tsx`; Seine
  `site/src/pages/[...lang]/index.astro`, `site/src/layouts/Base.astro` and both
  editorial keyword maps. Production crawl JSON retained in the local showcase.
- This verifies technical access and page signals, not that Google indexed every
  URL or that rankings improved. Existing Search Console requests need time;
  no repeated indexing requests or new property settings were submitted.

## Validation

- Seine strict content check: 26 English posts and 494 translations; production
  build: 562 pages. All 140 new homepage links resolve to the matching locale.
- Pool: 13 frontend tests; 114 API tests; strict Clippy; production frontend and
  220-page blog build. The ignored visual-export test was run explicitly and passed.
- Browser: desktop 1440 × 1000, mobile 390 × 844. Reviewed 34 captures: Seine's
  three changed sections, Arabic/Thai download links, all eight server-rendered
  pool pages, and real app success/empty/loading/error states with fixture data.
  No document-width overflow. Existing table content scrolls horizontally on mobile;
  the existing pending-request state uses the same placeholder as an empty response.
- Pool SPA route transitions update canonical, robots, descriptions, Open Graph and
  Twitter metadata; admin/missing routes remain noindex and public recovery restores
  index/follow. Back/Forward is checked. Canonicals exclude language and lookup queries.
- Stable gallery: http://localhost:8874/site-seo.html
  Start with `python3 -m http.server 8874 --directory /home/zp/Code/blocknet/showcases/blog-i18n`.
- Raw production crawl, local-check counts and browser evidence live alongside
  the gallery. Captures use actual built HTML/CSS/JS, with no production wallet data.
