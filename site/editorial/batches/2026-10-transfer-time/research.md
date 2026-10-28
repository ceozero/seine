# Blocknet ordinary transfer timing

Checked October 27, 2026 (EDT). The owner approved this guide and publication with “proceed”. One translation agent handles 13 locales; the parent handles English and six locales. Translations remain draft for optional linguistic review. No rented hardware or real funds.

## Reader job and boundaries

Explain the ordinary transfer path: submitted, in a block, then spendable. Sending/receiving already owns composing and approving payments; explorer owns lookup; wallet sync owns stale local balances; pool confirmations owns coinbase maturity and pool accounting. This guide links those existing procedures and focuses on the ten-block ordinary-output depth rule and the distinction between confirmation counters. Search demand is inferred from the ordinary user journey, not analytics.

## Primary evidence

- Official release pages checked: https://github.com/blocknetprivacy/core/releases/tag/v0.22.0 and https://github.com/blocknetprivacy/blocknet-gui/releases/tag/v0.22.0. Core commit `5a0a5b510c1dce46f4eeb12c33a291052e44e7b3`; GUI commit `661fff98e047f395489a0d2eba88f572c2a89935`. Use `git show v0.22.0:<path>` in the local core checkout to inspect the released code without modifying production work.
- Core wallet/wallet.go:713–738: CoinbaseMaturity=60, SafeConfirmations=10, EstimatedBlockInterval=5*time.Minute. IsOutputMature rejects spent outputs, computes currentHeight minus BlockHeight, then compares to 60 for coinbase or 10 for ordinary outputs. This is described as released wallet behavior, not a newly proven consensus requirement.
- wallet/wallet.go:749–780: SpendableBalance sums mature outputs; PendingBalance sums unspent outputs not yet mature. wallet/input_reservation_test.go:176–199 checks the ordinary output depth requirement; no implementation change requires rerunning the daemon build.
- Core block.go:48–52: 300-second target interval. Ten later blocks therefore imply about 50 minutes after inclusion at the target interval; prior mempool wait comes before that. No measured timing distribution or guaranteed inclusion/delivery time is claimed.
- api_handlers.go:880–925: wallet outputs API computes height difference and returns ordinary type, pending/unspent status and depth. api_handlers.go:134 and 3117,3150–3175: transaction/block detail and outgoing records use chainHeight minus containingHeight plus one. At containing height 100,000 and tip 100,004: wallet depth4, details5, remaining6. At tip100,010: wallet depth10, details11, mature.
- api_handlers.go:479–520: balance separates pending_unconfirmed; incoming unconfirmed ETA uses (SafeConfirmations+1)*EstimatedBlockInterval. The confirmed total excludes unconfirmed incoming mempool funds. The API can report scanning while sufficiently behind.
- GUI main.js:544–558: incoming mempool funds come from balance.pending_unconfirmed, not wallet history. main.js:1065–1092: pending regular outputs need 10 minus output.confirmations; remaining blocks are rendered as approximate time. main.js:1137–1155: incoming unconfirmed notice and estimate. main.js:6030–6035: transaction detail says Pending for mempool/no containing height, otherwise Confirmed. main.js:1022–1165 and 1515–1610: dashboard, synchronization/scanning and history.
- Wallet closure does not prevent chain inclusion of a transfer to its address; the local node and wallet must catch up to display the result. This is the same source-backed distinction used in existing wallet/node/miner and synchronization guides.

## Three-stage fixture

Actual released GUI frontend files main.js, styles.css, loader.js and qr.js remain byte-identical. Local deterministic API responses substitute for the daemon; a visible DEMO DATA banner labels every capture. CSP blocks network connections, sound and notifications are disabled, and no private keys, real funds, broadcast or signing are used.

- Unconfirmed: chain tip99,999; incoming mempool amount125000000 atomic units (1.25BNT), pending_unconfirmed_eta3300; spendable/pending/total0; empty confirmed history; one mempool item. The genuine interface says incoming, confirms in ~55min. Article explains estimates are guidance and includes the separate inclusion wait.
- Pending: containing block100,000; tip100,004; regular output depth4/statuspending; detail5; pending/total1.25BNT; spendable0; dashboard about6blocks/~30min.
- Spendable: same containing block; tip100,010; output depth10/statusunspent; detail11; spendable/total1.25BNT; pending0.

These screenshots illustrate state, not elapsed time measurements. Stable showcase: http://localhost:8874/transfer-time/. Article desktop/mobile views include list discovery, language menu and dismissal, images, FAQ and representative RTL/Greek/Thai/long-text layouts. Static article introduces no loading/error/disabled product states.

## Links and publication

Incoming related-reading links from send/receive, explorer and first-BNT guides in all 20 languages, plus every blog index. Replaced related links remain in existing article bodies. Only related arrays and matching source hashes change in those articles. New article includes three FAQs, canonical and 20-language alternates, BlogPosting/BreadcrumbList/FAQPage, OG graphic, RSS and sitemap entries.

## Checks before publication

Strict article validation passes with no warnings. All 53 posts pass content checks; 20 translation structures, protected code/links, paragraph boundaries and metadata lengths pass. The 60 existing locale files contain only related-reading or matching source-hash changes. Overlap report finds at most 0.1% shared eight-word phrases with existing articles. Five release-fact tests pass; v0.2.42 verified live. All 42 external source and localized pool-guide destinations return HTTP200.

The pool release metadata refresh is committed as `7ea431f`; all 20 calculator outputs remain byte-identical and all 21 pool blog posts validate. No pool service was deployed or restarted for that metadata-only change.

Build completed with 1,102 pages. All 20 built articles pass canonical, language/RTL, 21 alternate-link, three-FAQ/schema, image, internal-link and fragment checks; all 20 RSS feeds include the guide. Shared Windows Chrome checks pass at desktop and mobile widths, with no horizontal overflow across all 20 locales at 305 CSS pixels of content width and all images loaded. Language selector closes on outside click on both widths; list navigation and full-size screenshot opening pass. Captures reviewed for English, Arabic, Greek, Thai and German.
