# Getting the first Blocknet receipt

Verified October 27, 2026 (EDT). The owner approved the proposed article, screenshots and all 20 languages with “proceed”. A separate translation review remains optional; all translations retain draft status. One translation agent handles 13 locales; the parent handles English and six translations. No rented hardware or new mining measurements.

## Intent and overlap

Choose receiving a transfer or mining with an existing computer, then identify the first wallet receipt and spendable funds. This is a starting-point decision and completion checklist. The desktop-wallet guide owns interface setup; sending/receiving owns the payment procedure; mining owns installation and accepted shares; bntpool owns reward eligibility and payout accounting. The new guide routes to those owners rather than duplicating commands or payout arithmetic. Its single-payment screenshot sequence adds a concrete completion check. Demand is inferred from the user journey, not Search Console volume. The overlap report found 0.4% shared eight-word phrases with the desktop guide; intent boundaries were separately checked.

## Sources and factual boundaries

- Desktop wallet release v0.22.0 remains latest on October 27: https://github.com/blocknetprivacy/blocknet-gui/releases/tag/v0.22.0. Source commit `661fff98e047f395489a0d2eba88f572c2a89935`.
- Released GUI `main.js:1313–1447` and `index.html:292–333`: Receive, Your Address, Copy, public receiving destination. `main.js:4894–5599`: create/open and recovery backup. `main.js:1022–1165`: node synchronization, wallet scan, spendable/pending/total readings.
- Same GUI `main.js:1515–1610` and `6023–6118`: History received entries and transaction detail, hash, status, block, confirmations, received amount. The detail requests `/api/tx/<hash>` and block timestamp separately.
- The wallet/node/miner research already establishes offline receipt and subsequent chain scanning from CLI v1.2.0 (`948af4de8b7a3e3cddc86a329c7d2d003cb3fd6b`), `docs/reference-core.md:588–616`, and separation of receiving wallet from pool miner. See `../2026-10-wallet-node-miner/research.md` and fact-sheet “Wallet, node and miner roles”.
- seine v0.2.39 (`8a822f767bdc6a8b2effd7565751f47ba2c6846d`), released docs/config, plus existing mining and RAM guides: pool mode takes public payout address, accepted shares show work accepted, wallet secrets are unnecessary on the mining computer. No performance numbers or new hardware claims are introduced.
- https://bntpool.com/api/info checked October 27: minimum payout 0.1 BNT, 60 blocks before payout, six-hour PPLNS window. The article deliberately links the existing payout owner instead of duplicating changing numeric settings. https://bntpool.com/blog/how-pplns-payouts-work/ confirms allocation, maturation, threshold and sent-payment stages. No exact first-payout time is promised.
- Existing wallet fee and sending guides own payment preview, fee reserve and spendable-balance checks. No exchange, purchase, price, return or support-demand claims. Receiving a personal transfer or payment describes ordinary recipient use, not a financial recommendation.

## Screenshots

Actual released GUI frontend, rendered through configured shared Windows Chrome MCP with deterministic local responses. The unchanged `main.js`, `styles.css`, `loader.js`, `qr.js` and icons are from the version above. An explicit fixture bridge, CSP blocking network connections and visible demo banner surround it. No real wallet, seed, funds, mining, signing, native backup or broadcast. Sound and notifications are disabled on the fixture origin. The first receipt is an illustrative 1.25 BNT, not a required payment or mining estimate; transaction hash, block, peers and fee are also demo values.

The Receive asset is reused from the previous desktop guide, which already labels its non-payment address. Two new captures show the received transaction detail reached from History, and the same amount as spendable on Dashboard. The hero/list image is the top 1200×630 region of the real Dashboard capture, preserving the demo banner. Original captures and the runnable fixture are retained at `http://localhost:8874/first-blocknet/`.

Source checks validate fixture responses against the GUI; this is a visual frontend walkthrough, not an end-to-end native transaction test. Internal links are localized, with bntpool blog links using `/blog/<locale>/`. The external My Stats link stays its canonical English URL; readers can choose their language there.

## Incoming links

The new guide is linked from the blog index and related-reading blocks on `what-is-blocknet`, `blocknet-desktop-wallet` and `blocknet-wallet-node-miner` in every language. Replaced related entries retain links in the existing article bodies. Their only source changes are related arrays; translation body text is unchanged and hashes are refreshed to match.

## Pre-publication verification

- Strict content check: 51 posts, no errors or warnings. New source: 50-word Answer, three FAQ answers of 44/52/50 words; prose within the house length range.
- All 20 locales pass schema, protected labels/tokens, paragraph and image positions, source hash and description budgets. Existing incoming-link articles changed only related arrays and corresponding translation hashes.
- Release facts verified live against seine v0.2.39; five release-facts tests pass; full build generated 1,062 pages.
- All 20 local article pages pass canonical, 21 hreflang tags, language/direction, FAQ/BlogPosting schema, local destination/fragment and image checks. All 20 RSS feeds include the guide; 42 distinct external destinations return HTTP 200.
- Shared Windows Chrome: desktop 1440×1000, mobile 390×1100, and all 20 locales in a 320px frame (305px content width) pass overflow/image checks. Eighteen article/list/menu captures and four desktop-wallet demo states were reviewed. Zero console errors.
- Blog-list navigation, full-size image navigation and language-menu outside-click dismissal pass on desktop and mobile. No application layout or behavior change was needed.
- A mobile-list capture initially waited on lazy images that were hidden/offscreen; the disposable evaluation was stopped, the owned tab reused, and the bounded visible-image check passed. This was a capture-script issue, not a site defect.
