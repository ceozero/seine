# Shared publishing plan: Seine and bntpool

Updated October 28, 2026 (EDT). Keep this file identical in both repositories:
`seine/site/editorial/` and `blocknet-pool/frontend/blog/editorial/`.
This is the shared prioritization document; each site's keyword map records existing URL ownership.

## Outcome and baseline

Grow relevant organic visits and useful next actions on BOTH domains. Seine should help readers
choose, download and run the miner; bntpool should help them earn BNT, understand the currency's
mining economics, join the pool and follow their rewards. Both can publish substantial general
Blocknet education. Bntpool is not restricted to operational support articles.

After the currency cycle: Seine has 61 English source articles and bntpool has 22, each published in 20
languages. Those counts measure the catalog, not rankings, demand or quality. Recent currency,
wallet and privacy publishing favored Seine. No Search Console performance export was collected
for this pass; proposed search phrases below are intent hypotheses, not measured query volumes.

## Ownership by reader job

| Intent | Primary destination | Supporting coverage and next step |
|---|---|---|
| Download a Blocknet miner; choose supported platforms | seineminer.com `/` and `/#download` | OS guides give the detailed installation procedure and return to the real download section |
| Select mining hardware; improve local performance | Seine hardware/tuning guides and `/#performance` | Pool calculator consumes a reader's measured rate; do not duplicate hardware rankings |
| Join a Blocknet mining pool | bntpool.com `/` and `/start` | Pool setup guide explains workers and account lookup; Seine owns installation |
| Understand rewards, issuance and mining economics | bntpool reward schedule, calculator, fair-launch and pool guides | Seine's existing supply article retains the holder's supply overview; link to the full schedule |
| Understand BNT as an earned, transferable currency | bntpool new coverage where the reader job is distinct | Link to Seine's existing send/receive, timing, fungibility and wallet procedures instead of recreating them |
| Understand privacy mechanisms, wallet use and Faraday | Existing Seine owners | Bntpool may explain implications for earning and receiving BNT, with short context and a link to the mechanism owner |
| Find live network/pool data | bntpool `/stats`, `/blocks`, `/payouts`, `/luck`, `/status` | Articles explain interpretation and link to live tools; dated examples must not pose as live values |
| Understand chain security and mining's role in currency | New bntpool coverage, subject to the overlap check below | Seine keeps its existing software-role, rule-enforcement and general mining introductions |

One reader job gets one primary article across the two sites. Related subjects may appear on both
when the procedure or question is materially different. Use specific, helpful cross-links in the
reader's language. Do not copy articles between domains, add reciprocal links merely to inflate
link counts, or point unique articles' canonicals at the other site. Preserve existing URLs and
self-canonicals; relocation requires a separate, evidence-backed migration decision.

## Completed currency cycle — October 28, 2026

- Expanded bntpool `/blog/blocknet-fair-launch/` with the distinct genesis and block-1 records,
  issuance-to-transfer explanation, and precise limits on what allocation rules establish.
- Expanded `/blog/blocknet-block-reward-schedule/` with issuance, maturity and later transfers;
  retained every table/code block and independently verified the pre-tail total.
- Added `/blog/how-mining-secures-blocknet-payments/` after comparing the existing owners on both
  sites. It owns competing payment histories, cumulative work, confirmation depth and conflicting
  spends. Linked to the existing wallet, privacy, rules and pool-accounting owners in every locale.
- All three changes cover 20 languages. The new block/shield/wallet cover uses the shared renderer.
  Mobile inline hashes now wrap without changing the horizontal scrolling of command examples.
- Evidence and verification: pool `currency-and-security-2026-10-28/research.md`;
  stable visual showcase: `http://localhost:8874/currency-and-security/`.

## Newcomer journey cycle — 2026-10-28

- Seine download rows link directly to the matching Windows, macOS or Linux setup guide.
  Mac browsers no longer select Apple Silicon automatically: the browser does not reliably
  distinguish it from Intel. Both downloads remain available.
- A fourth setup step links to bntpool My Stats in the same language and explains using the
  same wallet identity, accepted shares and the initial hashrate delay.
- bntpool retains its existing homepage Get Started action. `/start` adds localized platform
  guides, Windows double-click instructions, a direct My Stats action, and optional separate
  PowerShell and Unix command examples. `/stats` repeats the wallet-identity guidance beside
  its accessible lookup input. Static search landing HTML follows the same four setup steps.
- New copy covers all 20 languages. Archive verification is not part of the onboarding flow;
  existing security troubleshooting articles remain available through the blog.
- Validation: both frontend builds, pool's 21 tests, separate API release build, 60 mobile
  locale/route checks, desktop/mobile stats fixtures (empty, success, loading, error, zero),
  Arabic RTL, seven platform-detection cases and both command-copy actions.
- Stable visual showcase: `http://localhost:8874/onboarding/`.

## Remaining publishing queue, in order

Give the next cycle more bntpool editorial effort; do not require a permanent article-count quota.

| Priority | Site / action | Reader question and concrete work | Boundary / evidence required |
|---|---|---|---|
| 6 | bntpool: research `blocknet-bnt-atomic-units` | How do wallet decimals, atomic units and rounding represent the same BNT amount? | Check whether fees, supply and payout guides already answer this adequately. Verify precision and rounding in released code. If the answer fits a short section, update an existing owner instead of making a thin article |
| 7 | Both: use actual search results to choose the following cycle | Which useful pages are getting impressions but failing to satisfy the query or attract clicks? | Follow the measurement procedure below; do not infer performance from article count |

The remaining queue is not a claim that its articles or landing-page revisions are published.
The currency cycle above followed the separate cover rollout. Before drafting, check BOTH keyword maps
and record the distinct reader job, nearest owner, primary sources, evidence added, and next action.
All article changes ship in all 20 languages; separate reviewer sign-off is not a publishing gate.

## Measurement and main-site SEO

For each domain, export Search Console **Web** search data for the latest complete 28 days and
preceding 28 days; retain dates, query, landing page, country/device where useful, clicks,
impressions, CTR and average position. Label brand and non-brand queries and compare like-for-like
language groups. New pages may not have enough data for a meaningful comparison. Never promise a
ranking increase from the cover change or a fixed publishing cadence.

Record the export date and source alongside the data; keep account data out of public build assets.
Check indexing and canonical selection for representative home, blog, translated and article pages.
Verify both properties and sitemap submissions when accessing the account; do not assume a domain
is verified because the sibling is. Manual indexing requests are optional, not a release gate.

Measure useful onward actions with existing privacy-respecting metrics where available:
- Seine: visits to download/platform guidance and outbound release-download clicks.
- bntpool: visits to `/start`, connection-help use and account-lookup navigation.
- Both: relevant article-to-product and cross-site navigation.

Do not call a navigation click an installed miner or an active pool worker. Do not add wallet-address
tracking or cross-site identity stitching. If existing metrics cannot answer a question, record the
gap before proposing instrumentation. Review after sufficient data accumulates, typically 4–8 weeks;
there is no new scheduled job or external outreach in this plan.

Maintain the technical foundation on both main sites and blogs: crawlable initial content, descriptive
titles and snippets, correct self-canonicals, reciprocal locale alternates, useful internal links,
fast images, sitemap membership and visible-content-matching structured data. Prioritize observed
errors and user journeys over adding more schema types or pages.

## Cover standard and publishing checks

See `cover-system.md`. Covers are separate from instructional figures. Both sites use the same
paper/green palette, safe area and frame, with unique article-specific artwork or a framed real
capture. Images do not contain duplicate article titles. Keep the dated list layout and compact
mobile text list. Share covers across locales; preserve translated headings and article text.

Before landing: run the site's content checks and production build; verify every published cover,
responsive image candidate, social image and image metadata; inspect real desktop/mobile pages,
RTL and long translated titles. Check the list, screenshot covers, illustrated covers and affected
article headers. Publish Seine via master deployment and pool via `--api-only`; verify live output.

## Source guidance

- [Google: helpful, reliable content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content): prioritize reader purpose, original value and clear site focus.
- [Google: image SEO](https://developers.google.com/search/docs/appearance/google-images): crawlable images, relevant surrounding content, responsive assets and useful alternative text.
- [Google: localized versions](https://developers.google.com/search/docs/specialty/international/localized-versions): preserve language-specific URLs and reciprocal alternates.

These sources support the publishing principles; the site split and queue above are our editorial
judgment, not Google's prescribed domain strategy or evidence of current rankings.
