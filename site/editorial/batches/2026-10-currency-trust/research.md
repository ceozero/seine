# Currency trust and rule enforcement

Checked October 28, 2026 EDT. The user approved the proposed new “Who controls Blocknet?” article and expansion of the existing Bulletproofs owner. Publication in the established 20-language pipeline is authorized. One agent writes/translates the scoped Bulletproofs refresh; the parent writes/translates the control guide, checks source evidence, integrates graphics and publishes. No independent linguistic review is claimed; changed article translations are draft. No hardware rentals, mining workloads or daemon/pool restarts.

## Intent and boundaries

`who-controls-blocknet` owns enforcement and authority: software implementation, candidate block production, validation and spending authorization. The existing wallet/node/miner guide owns application choice and which processes stay running. The node guide owns operation. The supply guide owns issuance quantities, and Faraday guides own future transition details. This article is not a distribution study, assertion of formal governance structure or vote, or ranking of decentralization.

`bulletproofs-explained` retains its original mechanism intent and URL. It gains the practical explanation of separate authorization, value-conservation, repeated-spend and reward checks. No competing “private supply audit” URL is introduced. Its original publication date is preserved, with an updated date for the material revision.

Search check: official-domain queries for “who controls” and private-supply verification yielded official protocol/API material but no measured search demand. Demand is inferred from ordinary currency questions, not Search Console impressions or a claimed search volume. The keyword map records semantic boundaries; low wording overlap does not prove distinct intent.

## Pinned implementation

GitHub latest-release metadata checked: core v0.22.0, commit `5a0a5b510c1dce46f4eeb12c33a291052e44e7b3`. Read source from that exact Git object in the local blocknet-core repository, rather than current fork work. Public reference: https://github.com/blocknetprivacy/core/tree/5a0a5b510c1dce46f4eeb12c33a291052e44e7b3.

- `block.go:233–353`: block acceptance checks height/context, timestamp, expected difficulty, proof of work, size, transaction structure and validity. Mining work alone is insufficient.
- `block.go:543–574`: coinbase consensus reconstructs the expected commitment and encrypted amount from height-based reward and publicly derived blinding; compares both. A mining-software field change cannot alter another node's expected reward. Do not describe the coinbase amount as an ordinary hidden payment.
- `block.go:1741–1805`: ProcessBlock validates first, computes accumulated work, then invokes reorganization for a heavier branch. It does not choose a chain purely by a count of blocks or a balance-weighted vote. Reorganization rules still apply; no claim that all higher-work histories are accepted.
- `block.go:1807–1860`, `:859–902`, `transaction.go:967–977`: optional trusted-checkpoint historical fast sync may skip expensive PoW/signature/range-proof re-verification. Structural, binding, balance and double-spend checks remain. Scope statements about full current validation; do not claim every local node necessarily re-verifies every historic cryptographic proof.
- `transaction.go:985–988`: coinbase has no spending inputs and a separate path.
- `transaction.go:1002–1059`: duplicate key images, exact ring structure, canonical chain membership, RingCT signature, key-image/pseudo-output binding and spent-image lookup. Input authorization is separate from range proof and balance. The reviewed acceptance path does not weight approval by a wallet holder's balance.
- `transaction.go:1061–1090`: verify output range proofs and commitment balance using signed pseudo-outputs. Ordinary transaction value conservation is not issuance, and a range proof alone is not proof that an input has not already been spent.
- `miner.go:383–431`: scheduled reward and cumulative emission from height 1; actual genesis has no coinbase. Emission totals are not a sum of private wallet balances and do not establish current circulating/spendable supply.

Wallet owners' private-key authorization and optional disclosure follow the source-backed transaction walkthrough, payment-proof and view-only-wallet research already in the fact sheet. No private keys, actual payments, wallet balances or personal data are used in this batch.

## Software adoption and upgrades

Statements separating repository commits, executable updates and activation conditions are explanations of software deployment, not a claim about an unwritten voting system. Software can implement rule changes; deployed compatible software and applicable activation conditions matter. Do not say all operators must manually approve every update.

The pinned CLI v1.2.0 evidence in `research/faraday-and-node-2026-10-26.md` covers `setup.go:305–335` scheduled updates, `commands.go:293–305` auto-upgrade checks, and `docs/reference-upgrade.md` latest-following versus pinned core policy. This batch links the existing node guide for that procedure and makes no new current CLI-release claim.

The official October 27 article was opened and read: https://blocknetcrypto.com/blog/2026-10-27-how-blocknet-privacy-survives-quantum-computers/. It labels Faraday as under construction/testing. The new control article attributes the future proposal without introducing new dates, parameters or migration steps. Existing dated upgrade and monetary-policy guides own those details.

## Presentation and integration

Two original native SVG diagrams follow the existing article palette and list thumbnails. The four-role graphic is not a network topology or vote distribution; its translated caption says so. The private-validation graphic separates ordinary-spend checks 1–3 from coinbase issuance check 4. All labels are simple numbers/symbols with translated explanatory text.

Incoming related links are added from supply, software roles and node operation in all 20 languages through source metadata. Displaced related targets remain linked in the existing body. These 60 MDX changes preserve all body text and translation-review state; only English related metadata and translated source hashes change.

Validation: strict source/translation checks, protected values and link parity, source hashes, semantic overlap review, release-facts check, full build, local/live metadata, schema, sitemap/feed/internal-link checks, and real desktop/mobile captures with the configured Windows Playwright MCP. No Linux browser or live wallet process is used. Detailed final results and source revision live in the stable currency-trust showcase.

Parent integration assigns the new verification diagram as the existing Bulletproofs article’s list thumbnail and refreshes all translation hashes for that metadata addition. Final source hash: `3be778e9122b`.

# Bulletproofs accuracy refresh — 2026-10-28

Scope: `site/src/content/blog/bulletproofs-explained/*.mdx` only, English plus 19 translations. Original publication date remains 2026-10-25; English `updated` is 2026-10-28. Translations inherit dates and are marked `translation: draft`. Agent English content hash before parent thumbnail integration: `44187296a14b`.

## Primary evidence

All code references are pinned to released core v0.22.0, commit `5a0a5b510c1dce46f4eeb12c33a291052e44e7b3`. Parent extracted the files into this scratch directory; the relevant implementation was read directly.

- [transaction.go, lines 960–1090](https://github.com/blocknetprivacy/core/blob/5a0a5b510c1dce46f4eeb12c33a291052e44e7b3/transaction.go#L960): the public validation entry point enables full cryptographic verification. Normal spending checks canonical ring members and ring size, RingCT ownership and amount equality, binding of the key image and pseudo-output to the signed proof, duplicate key images within a transaction, and prior use on the accepted chain. It verifies each output range proof and separately checks commitment balance with the fee. The three checks in the article are complementary, not interchangeable.
- The same source explicitly limits the `skipCrypto` path to trusted historical checkpoints during fast sync. RingCT and range-proof verification can be skipped there; structural, binding, repeated-spend and balance checks still run. The article says it describes full validation and includes the checkpoint assumption instead of implying every synchronization mode redoes every expensive proof.
- [block.go, lines 543–574](https://github.com/blocknetprivacy/core/blob/5a0a5b510c1dce46f4eeb12c33a291052e44e7b3/block.go#L543): coinbase must have exactly one output. The validator derives the allowed reward from height, derives consensus blinding from public transaction data and height, and reconstructs both the commitment and encrypted amount. Both must match. Thus the coinbase amount is publicly derivable even though an amount encoding and commitment exist. The refresh scopes hidden amounts to ordinary payments and distinguishes pool payouts from the special reward transaction.
- [miner.go, lines 383–431](https://github.com/blocknetprivacy/core/blob/5a0a5b510c1dce46f4eeb12c33a291052e44e7b3/miner.go#L383): `GetBlockReward` defines the height-dependent reward and `TotalEmittedSupply` sums scheduled rewards beginning at height 1. Genesis has no coinbase. The cumulative issuance total is not obtained by adding private wallet balances and is not a measure of current spendability or circulation.
- Existing fact-sheet and existing article evidence establish 16-member ordinary spending rings and 64-bit per-output Bulletproofs. A 64-bit unsigned range is inclusive 0 through 2^64−1; all old inclusive 2^64 upper bounds were corrected. Existing proof-size calculations, commitment equation and pedagogical construction remain intact.

## Changes and boundaries

The fee is public alongside transaction hash and structure, not the sole public number or datum. The commitment arithmetic now subtracts the fee commitment as well as outputs. FAQ 3 allows deliberate disclosure via payment proofs or viewing access and explicitly separates public coinbase amounts. FAQ 4 describes conservation as one component of full validation.

The diagram identifies four roles: authorization/ring binding; range and balance; key image not already spent; and a separate coinbase issuance path. It is explanatory, not a live-transaction capture or complete block-validation checklist. Existing explorer and educational links remain. Added links connect the control, supply and transaction guides and the pinned validation source. No Faraday specifications, new monetary quantities, investment promises, additional competitor comparisons, hardware claims or fee-destination claims were introduced.

## Validation

- `node scripts/check-content.mjs --strict bulletproofs-explained`: passed, zero warnings/errors; this checks English and all 19 translations for the selected article.
- Custom checks across all 20 files: four FAQs, two Answer blocks, one CTA, consistent 42 blank-line-separated body parts; all original fenced blocks byte-identical and inline-code multisets unchanged; all original link destinations retained; new links localized; no symbolic placeholders left; no uncorrected inclusive 2^64 bound; exact final source hash and draft translation status.
- Per-field scratch checks: exact English key set, link-token counters, inline code and paragraph counts across all 19 translated updates.
- No browser, build, commit, push or deploy performed by this translation agent. Parent owns integration/build/visual checks/publication and diagram assets.
