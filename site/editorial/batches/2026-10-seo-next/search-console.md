# Search Console audit — 2026-10-25

Times below are America/New_York (EDT). Account details are intentionally excluded.

## seineminer.com

- Existing verified domain property: `sc-domain:seineminer.com`.
- Performance and indexing overview reports: “Processing data, please check again in a day or so.” No traffic totals or query opportunities inferred from the unavailable reports.
- Existing sitemap: `https://seineminer.com/sitemap.xml`, Success, last read October 25. Its earlier discovery snapshot showed nine pages; a fresh Chrome fetch returned HTTP 200 and 501 URL entries before this batch.
- `robots.txt` allows crawling and advertises the sitemap.
- URL inspection of `/blog/blocknet-mining-hardware-hashrate/`: **URL is on Google; Page is indexed**.
- Live inspection at **4:50 PM EDT**: **URL is available to Google; Page can be indexed**; one valid breadcrumb item. This directly verifies Google's access; a separate nonbrowser request's HTTP 403 was not treated as evidence of Googlebot blocking.
- Production deployment: `7d8bff4`, Cloudflare Pages action `40233157289`, succeeded **4:59 PM EDT**. The final CI build and IndexNow notification passed.
- After deployment: all 40 changed article URLs returned HTTP 200 with current content, correct canonical and 21 language alternates; the screenshot loaded. Live sitemap contains **521 URLs**.
- Resubmitted the expanded sitemap at **5:00 PM EDT**: **Success, 521 discovered pages** (the earlier nine-page snapshot is resolved).
- New Windows guide was initially unknown to Google; requested indexing once at **5:01 PM EDT**, and Google confirmed it entered the priority crawl queue.
- Requested recrawl of the revised benchmark page once; Google accepted it into the priority crawl queue at **5:02 PM EDT**.

## bntpool.com

- No accessible pool property initially. Created and verified the URL-prefix property `https://bntpool.com/` with an HTML verification tag.
- Public verification tag shipped as `blocknet-pool@c7ac958`, built frontend and deployed with `./scripts/deploy_bntpool.sh --api-only --skip-ui-build`.
- API restarted at **4:43:46 PM EDT**. Stratum PID 327118 retained its **3:30:19 PM EDT** start; monitor and recovery service were unchanged. Health checks passed; no ongoing incidents, no unhealthy services, daemon reachable and not syncing.
- Submitted `https://bntpool.com/sitemap.xml` at approximately **4:48 PM EDT**. Search Console reports **Success**, read October 25, **228 discovered pages**.
- Live robots file allows public pages and excludes `/api/`; sitemap contains 220 blog URLs and eight app URLs.
- PPLNS guide inspection: **Discovered — currently not indexed**. Live test at **4:54 PM EDT** passed (**URL is available to Google; Page can be indexed**), with one valid breadcrumb item. Requested indexing once; Google confirmed it entered the priority crawl queue.
- New property reports need processing time. Discovery and indexability are not guarantees that every language URL will be indexed.

## Next measurement

Revisit Search Console when reports populate, then compare queries, pages and countries after 4–8 weeks. Use impressions and positions to improve existing intent owners before adding near-duplicate posts. No automatic reminder or recurring task was created.
