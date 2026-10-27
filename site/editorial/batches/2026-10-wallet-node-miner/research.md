# Wallet, node and miner roles

Checked October 27, 2026 (EDT). User authorized a return to normal newcomer questions and broader Blocknet fundamentals. No rented hardware, mining sessions, wallet operations or competitor comparisons are needed.

## Intent and evidence

Distinct reader job: decide which application is needed for receiving funds, pool mining or direct mining, and which process must stay running. The nearest owners cover wallet creation, node operation and mining setup; this page connects their roles without duplicating their procedures. No search-volume claim is made.

## Reviewed public sources

- CLI v1.2.0, commit `948af4de8b7a3e3cddc86a329c7d2d003cb3fd6b`: [wallet management](https://github.com/blocknetprivacy/blocknet/blob/948af4de8b7a3e3cddc86a329c7d2d003cb3fd6b/docs/reference-wallet.md), lines 25–31 (keys/state/password), 35–94 (loading, one wallet, remembered path), 110–114 (conditional backup). The old wallet setup paragraph incorrectly implied automatic loading on restart and unconditional backup; replace it in all 20 languages.
- Same CLI pin: [core reference](https://github.com/blocknetprivacy/blocknet/blob/948af4de8b7a3e3cddc86a329c7d2d003cb3fd6b/docs/reference-core.md), lines 21–23 and 962–969 (core versus attached shell), 588 onwards (wallet rescan works on downloaded blocks), 700–735 (mining separately controlled).
- Public core v0.22.0, commit `5a0a5b510c1dce46f4eeb12c33a291052e44e7b3`. `api_handlers.go:2237–2257,2844–2890` and `wallet/scanner.go:23–44,90–100` show catch-up scanning of stored chain data. Wallet scanner and consensus state are separate; receiving does not require the recipient wallet to be online. Offline-receipt wording is a derived explanation of persisted chain outputs plus subsequent wallet scanning, not a claim of an executed payment test.
- seine v0.2.39, commit `8a822f767bdc6a8b2effd7565751f47ba2c6846d`: [solo-mining guide](https://github.com/zpalmtree/seine/blob/8a822f767bdc6a8b2effd7565751f47ba2c6846d/docs/guides/solo-mining.md), default pool mode and authenticated direct core connection; `src/config.rs` default pool and payout identity. Pool-mode identity does not require wallet secrets. Direct mode may use wallet credentials; do not generalize the pool-mode statement.
- Pool source `1d5c3e2a314917bd967f0f217cd5d410b5a8cd50`, `crates/pool-runtime/src/node.rs:490,891`, `stratum.rs`, `payout.rs` and the existing pool tracking guide explain accepted shares, worker records, pool accounting and on-chain payouts. A share is not a wallet payment.

## Artwork and localization

Original SVG shows numbered wallet, node and processor icons, mapped to a localized role table. A 1200×630 JPEG export supplies the list and social image; the inline diagram remains SVG. It is explanatory artwork, not a dashboard screenshot or benchmark. Preserve the existing article/list design. All translations remain `translation: draft`; no independent linguistic review is claimed or required.

## Verification plan

Strict content and protected-token checks, overlap review, release facts, site build, all-locale metadata/links/schema checks, desktop/mobile Chrome captures including Arabic/Greek/Thai, 320px width checks for every locale, production CI/deploy, live links/sitemap/assets checks. Store actual results in the stable showcase; do not treat this plan as completed verification.

English strict checks pass. The wording-overlap report found no shared eight-word phrases; intent boundaries were separately checked against wallet setup, run-node and mining setup guides.
