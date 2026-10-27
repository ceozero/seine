# Desktop wallet walkthrough

Checked October 27, 2026 (EDT). The owner accepted a visual guide to the ordinary desktop-wallet journey, in all 20 languages, with real interface captures. Publication is authorized by the accepted “proceed”; separate translation reviewers are optional. No rented hardware, funded wallet or production daemon is involved.

## Search intent

Help a newcomer operate the desktop wallet through its visible controls: create/open, recovery backup, synchronization, receiving, send review and history. The nearest owners are `blocknet-wallet-for-mining` (initial wallet/payout setup, mostly CLI), `send-receive-blocknet` (payment mechanics and CLI procedure) and `blocknet-wallet-node-miner` (choosing applications). This article adds a versioned visual desktop procedure. Link to existing fee, synchronization, seed and recovery explainers instead of reproducing their deeper procedures. Demand is inferred from this normal user journey; no search-volume claim is made.

## Primary evidence

GUI release [v0.22.0](https://github.com/blocknetprivacy/blocknet-gui/releases/tag/v0.22.0), commit `661fff98e047f395489a0d2eba88f572c2a89935`. Published October 15, 2026 at 10:11 PM EDT. GitHub release API lists Windows x86-64 EXE, Linux x86-64 AppImage/DEB/RPM/Flatpak, Apple-silicon DMG, Intel-macOS app ZIP and SHA256SUMS. The README contains older version/file examples; platform claims here use the actual release assets.

Pinned source root: https://github.com/blocknetprivacy/blocknet-gui/tree/661fff98e047f395489a0d2eba88f572c2a89935

- `main.js:5947–5995`: desktop startup starts/checks the daemon; an already available wallet can open directly, otherwise the existing/new wallet flow appears.
- `main.js:4894–5000,5240–5406`: fresh install choices, create form, existing-wallet unlock, Open Wallet File, Restore from Seed. Creating another wallet does not reopen an old destination.
- `main.js:5407–5599`: creation password validation, new-wallet seed-backup flow, 12-word wording, “I've written it down”, three-word confirmation. No actual phrase was created or displayed for this article.
- `index.html:598–617`, `main.js:4603–4633`, `src-tauri/src/lib.rs:1099–1133`: Settings → Backup Wallet File opens the native destination dialog and copies the active encrypted `.dat` file. The native backup action was source-verified, not executed in the fixture.
- `main.js:1022–1165`: Dashboard shows node sync status, scan progress and spendable/pending/total balances. Node synchronization and wallet scanning are distinct. Existing backup/seed guides source password-versus-recovery-key semantics.
- `main.js:1313–1339,1390–1447`, `index.html:292–333`: Receive address, Copy, QR and optional shortname/payment-request controls. The first-receipt path needs only the address; screenshots leave optional fields empty.
- `main.js:3499–3680,3982–4027`: first Send validates entries and requests a dry-run fee preview; Confirm Send is a separate action; Cancel and expiry disarm it. Fee screenshot is illustrative, never a fixed fee claim. Real confirmation was not attempted.
- `main.js:1515–1610,6026–6118`: History combines received outputs and sent records; selecting an entry shows hash, status, block, confirmations and fee. Public lookup versus wallet-private details are covered by the existing explorer guide.
- Existing mining guide plus seine release docs establish using a public address for pool payouts; no wallet secrets are required for the pool workflow.

## Capture method and artifacts

The released `index.html`, `main.js`, `styles.css`, `loader.js`, `qr.js` and icons were served locally. Application JS/CSS were unchanged. The HTML adds an explicit fixture bridge and demo banner. The fixture provides deterministic local API/native responses, has `connect-src 'none'`, rejects unsupported commands and all real sends, disables sound/notifications on its own local origin, and has no daemon connection or private keys. Native installers, dialogs, seed creation/restoration and broadcast were not exercised. This is a frontend walkthrough, not an end-to-end wallet transaction test.

Shared Windows Chrome via the configured Playwright MCP captured welcome, create form, unlock, dashboard, receive, fee preview, history, syncing, scanning and empty states at 1200×860. The six published images use welcome, create, dashboard, receive, fee preview and history. All are labeled demo data; the QR/address intentionally cannot be used for a payment. Values such as 12.50 BNT, 1 BNT and 0.00010000 BNT are fixture illustrations, not observations or protocol constants. No recovery words appear. Screenshots are JPEG-encoded without altering the interface; the list/social image is a top crop of the dashboard capture, preserving its main controls and demo label.

The stable showcase is http://localhost:8874/desktop-wallet/ and retains screenshots, the fixture, source-license notice, source digests and verification results. Article captures include desktop/mobile and Arabic, Greek and Thai; all locales also receive 320px overflow checks. Translation status remains `draft` for optional linguistic review.

## Checks

English strict check passed after image generation. Wording-overlap report found no shared eight-word phrases. Intent overlap was separately reviewed against the three owners above. Complete build, browser and live results are recorded in the showcase after execution, not assumed from this plan.

The first all-locale 320px check found German long-word overflow in the answer and recovery heading (423px scroll width). Added emergency wrapping to article prose so ordinary word wrapping remains unchanged and an overlong word can wrap inside its container. Repeat the build and all-locale layout checks after this change.
