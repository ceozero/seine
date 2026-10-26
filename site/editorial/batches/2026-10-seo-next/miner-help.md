# Miner help and website measurement — shipped

Completed 2026-10-25. No subagents or separate linguistic reviewers were used.

- Pool code: `0ce8027`; API-only deploy at **5:23:31 PM EDT**. Stratum stayed on
  PID 355652, started 4:46:42 PM EDT; monitor stayed on PID 319472.
- Seine code: `2ca4d1d`; Cloudflare workflow 40235377353 succeeded at
  **5:27:43 PM EDT**. Both canonical branches were fast-forwarded and pushed.
- Expanded the existing pool tracking guide with `#zero-hashrate`: address and
  pool mismatches, accepted-share timing, four real miner messages and PPLNS
  context. All 20 versions updated; translations remain honestly marked draft.
  This topic now belongs to that guide instead of a competing Seine post.
- Added localized help links from pool setup, My Stats, Seine downloads, and both
  GitHub READMEs. Kept the existing blog list and article-specific images.
- Both blogs now count aggregate article views and clicks toward downloads and
  pool setup. No cookies, wallet identifiers, raw events or full URLs in counters.
  DNT/GPC respected. Private report: `/api/admin/site-metrics`; pool helper:
  `scripts/site_metrics_report.py`. Retention and limitations are described in
  the website section of `/privacy/` and the pool editorial implementation notes.

## Verification

Pool strict editorial/i18n checks, frontend build and 11 JS tests passed.
111 API tests and strict Clippy passed. Existing database-dependent API tests
can skip without PostgreSQL test configuration; the new collector HTTP tests do
not require a DB. Production persistence was separately verified by reading the
`website_counts_v1` meta value directly from PostgreSQL.

Seine built 522 pages after rebasing the latest canonical branch; three new
script tests passed. Structural checks covered 520 localized Seine pages and
220 pool pages, including canonical/hreflang and 33,500 local links/assets.
Live checks verified the updated guide in all 20 pool languages and help links
plus measurement metadata in all 20 Seine languages. Python's default HTTP
client hit a Cloudflare 403 on Seine; all 40 corresponding page fetches through
the configured Chrome session returned 200. Website privacy is live.

Collector checks: unauthenticated report 401, untrusted Origin 403, malformed
payload 400, same-origin and cross-origin test events 202. Both were saved in
PostgreSQL. The initial October 25 counts include two deliberate QA events:
`track-your-miner-on-bntpool/en/pool_setup` and
`mine-blocknet-on-windows/en/download`, one each. Exclude these two when assessing
first-day click totals. The shared browser has DNT=1: normal page loads sent no
events, as intended. No shared browser settings were changed.

Real desktop/mobile app fixtures covered zero, empty/disabled, loading, error and
success states. English, Arabic and Thai guide content, Greek setup links, Thai
download links and privacy were visually inspected. Browser extension errors
about competing wallet injections were unrelated to the sites.

Stable showcase: http://localhost:8874/miner-help.html (22 inspected captures).
Start it with:

```sh
python3 -m http.server 8874 --directory /home/zp/Code/blocknet/showcases/blog-i18n
```

## Next

Let Search Console and aggregate click counts accumulate, then prioritize queries
with impressions and weak click-through or setup/download engagement. No reminder
was scheduled. The NVIDIA article still needs real measurements before writing;
no miner benchmarks or GPU workloads were launched for this task.
