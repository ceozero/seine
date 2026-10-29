# Blocknet as currency and a privacy coin

Checked October 28, 2026 EDT. User explicitly approved all four proposed topics with “proceed with all of these”. This authorizes translation and publication; no independent reviewer gate. Two agents author and translate two topics each, while the parent reviews English/source evidence, integrates graphics, verifies and publishes. No external translation APIs, mining workloads, hardware rental or payments. Translations remain draft; no independent linguistic review is claimed.

## Scope and integration

Three new URLs and one substantial refresh preserve search-intent ownership. All four articles have 20 complete language versions and original SVG explanatory graphics. Two adjacent introductions get only their outdated Faraday-set passage corrected; their original publication dates remain and updated dates change. Four other existing owners get related-link metadata changes only. Existing related targets displaced from metadata remain linked in their body. All source hashes are refreshed from the final English. The blog keeps its established list presentation.

The latest public releases were checked during preparation: core v0.22.0 and seine v0.2.44. The reviewed release manifest already names v0.2.44, so no release identity or pool calculator change is needed. The pool reward and fair-launch articles are linked as established owners; this publication changes only seineminer.com.

## Validation approach

Check English and translation structure, source hashes, protected code and links, locale description budgets, semantic overlap and intent boundaries. Build the complete site, inspect canonical/hreflang/FAQ/BlogPosting/breadcrumb metadata, internal links, feeds and sitemap. Review real desktop/mobile pages, the article diagrams and list thumbnails, Arabic/Greek/Thai layouts and selector dismissal through the configured shared Windows Chrome MCP. Live verification follows deployment. Screenshots and audit evidence are preserved in the stable currency-privacy showcase.

# Supply and monetary-policy source notes

Checked October 28, 2026 (America/New_York, EDT). Authoring task: two English articles and complete translations. No mining, wallet actions or protocol changes performed.

## Search intent and scope

- `blocknet-supply`: explain cumulative issuance, approximate initial distribution target, continuing tail and the difference between supply growth and moving existing funds. The pool reward article keeps ownership of the month-by-month table and miner reward arithmetic.
- `blocknet-faraday-monetary-policy`: explain same-chain currency continuity and the reward-per-block versus time-based issuance distinction in the announced Faraday proposal. The existing Faraday upgrade article retains operational preparation and migration steps; privacy mechanisms have their existing dedicated pages.

## Pinned released implementation

Core v0.22.0 resolves to `5a0a5b510c1dce46f4eeb12c33a291052e44e7b3`.

- `miner.go:14–32`: approximate 100 million initial issuance target; tail 200,000,000 atomic units (2 BNT); 48 schedule months; blocks/month derived from 30 days and block interval. TargetSupply comment explicitly says actual supply exceeds it over time.
- `miner.go:383–397`: GetBlockReward selects the height-based month; fixed tail at month 48 onward; reward constant within each month before then.
- `miner.go:399–431`: TotalEmittedSupply sums from height 1; genesis has no coinbase. SupplyBreakdown uses TargetSupply as progress denominator and clamps remaining/progress after reaching it without disabling emission.
- `block.go:51–58`: five-minute target (300 seconds), maturity separate from issuance.
- `block.go:549–565`: coinbase checked against exactly GetBlockReward(blockHeight), with deterministic commitment and amount. Do not claim network fees are added to miner coinbase: the fact sheet labels destination/burning as an unverified inference. Articles state only that fees come from existing funds and create no new BNT.
- `block.go:2959–2973`: actual genesis has no transactions/coinbase. Do not confuse test-only CreateGenesisBlock helper with actual genesis.
- Existing transaction walkthrough and fee guides, sourced to released wallet builder, establish input/recipient/change/fee accounting. No claim that every new output means new supply.

Pinned public source links:
- https://github.com/blocknetprivacy/core/blob/5a0a5b510c1dce46f4eeb12c33a291052e44e7b3/miner.go#L383-L431
- https://github.com/blocknetprivacy/core/blob/5a0a5b510c1dce46f4eeb12c33a291052e44e7b3/block.go#L51-L58

## Published proposal

Primary source read in full with web tool:
https://blocknetcrypto.com/blog/2026-10-27-how-blocknet-privacy-survives-quantum-computers/

- Opening notice: still being built and tested; numbers, dates and design can change.
- Section 02: chain, history and balances remain. Same-currency/no-new-allocation explanation is a plain-language inference from that continuity; no airdrop is announced.
- Section 03: wallet migration remains required, exact steps forthcoming. Defer to existing upgrade guide instead of inventing live procedures. Do not imply continuity removes migration obligations.
- Section 05: target block time 5 to 10 minutes; per-block reward doubles at corresponding fork stage; approximately 343 to approximately 685 BNT and roughly 98,700 new BNT/day are rounded illustrations. No exact multiplication of rounded reward values. No assertion of a finalized 4 BNT future tail.
- Section 07: planned February 2027, block 103,680; date depends on testing, not a guarantee.
- Privacy adjacent correction: Section 02 says the Faraday coin set expands as coins move over, rather than every historical old-format output immediately belonging to it.

## Explicit arithmetic and interpretation

- 30 × 24 × 60 / 5 = 8,640 target blocks per schedule month.
- 48 × 8,640 = 414,720, current released tail activation height.
- 24 × 60 / 5 = 288 target blocks per day.
- 288 × 2 BNT = 576 BNT per target day.
- 576 × 365 = 210,240 BNT over 365 target-paced days. Not guaranteed calendar-year production.
- 24 × 60 / 10 = 144 target blocks per day under proposed timing.
- Symbolic matched-stage identity: `288 × R = 144 × (2 × R)`. R is reward at the compared stage, not a new constant or current live quote.
- Supply growth percentage = new issuance over chosen period / starting supply × 100. A fixed addition with a larger denominator yields a smaller percentage. This is arithmetic, not a purchasing-power or price forecast.
- Cumulative issued supply is a count of scheduled creation, distinct from a circulating-supply methodology or wallet's spendable balance. Articles do not quote today's circulating supply.

## Image semantics

- Supply: I_SUPPLY, numbered 1 = declining rewards through height-based stages; 2 = released ongoing 2 BNT/block tail. Conceptual, no exact plotted dates or curve values.
- Monetary: I_MONETARY, numbered 1 = two five-minute target intervals, R each; 2 = proposed single ten-minute target interval, 2R. Both total 2R in target ten minutes; no promise of actual block arrival.

## Link token mapping

- E_REWARD_CODE: https://github.com/blocknetprivacy/core/blob/5a0a5b510c1dce46f4eeb12c33a291052e44e7b3/miner.go#L383-L431
- E_FARADAY: https://blocknetcrypto.com/blog/2026-10-27-how-blocknet-privacy-survives-quantum-computers/
- I_SUPPLY: /assets/blog/blocknet-supply.svg
- I_MONETARY: /assets/blog/blocknet-faraday-monetary-policy.svg
- P_FAIR: https://bntpool.com/blog/blocknet-fair-launch/
- P_REWARDS: https://bntpool.com/blog/blocknet-block-reward-schedule/
- P_PPLNS: https://bntpool.com/blog/how-pplns-payouts-work/
- S_TRANSACTION: /blog/blocknet-transaction-explained/ (verified existing article).
- S_EXPLORER: /blog/blocknet-explorer-guide/
- S_MONETARY: /blog/blocknet-faraday-monetary-policy/
- S_SUPPLY: /blog/blocknet-supply/
- S_UPGRADE: /blog/blocknet-faraday-upgrade/
- S_MINE: /blog/how-to-mine-blocknet/

## Review addition

Supply entry 8 adds the continuing-reward incentive explanation, linked through S_POW to `/blog/how-crypto-mining-works/`. This is an economic interpretation of the released ongoing coinbase reward, supported by that existing proof-of-work guide, not a guarantee of security, profit or fixed participation. English frozen after parent review.


# Privacy-by-default refresh and fungibility

Prepared October 28, 2026 EDT. Parent owns publication. English authoring and translations by the active model; no external translation services, no separate independent-review claim. No payment or mining workload was executed.

## Reader jobs and ownership

- Existing `blocknet-privacy-features`: explain how privacy is applied by default to ordinary BNT payments, retaining the useful mechanism hub and distinguishing current rules from proposed Faraday. Preserve the original URL/publication date and record the material refresh with updated metadata.
- New `blocknet-fungibility`: explain interchangeability of equal currency amounts and how payment privacy supports that currency property. Conceptual examples are expressly illustrative. No claim of universal acceptance, stable exchange price, investment return, erased outside records or perfect source concealment.
- `what-is-a-privacy-coin` remains coin-agnostic definition; `blocknet-payment-visibility` owns observer views, deliberate proof/viewing disclosure and procedures. Links delegate those jobs rather than duplicating them.
- Supply and monetary policy belong to the parent's two new articles. Transaction anatomy and actual payment steps retain their current owners.

## Primary evidence inspected

Released core v0.22.0 commit `5a0a5b510c1dce46f4eeb12c33a291052e44e7b3`, read using `git show <commit>:<file>` from blocknet-core without editing checkout:

- `crypto.go:655–661`: CLSAG section and fixed RingSize=16. `transaction.go:1013–1041` requires exactly RingSize canonical on-chain ring members and verifies RingCT. Source: https://github.com/blocknetprivacy/core/blob/5a0a5b510c1dce46f4eeb12c33a291052e44e7b3/transaction.go#L1013
- `transaction.go:985–988`: coinbase has no inputs and a separate validation path. All ring/default spending claims in articles are scoped to ordinary payments/normal inputs; no sweeping claim that block-reward creation uses rings.
- `transaction.go:1002–1010,1044–1058`: duplicate key images, cryptographic binding, previously spent key-image checks. Decoy outputs are possible proof sources; their owner funds are not contributed. Existing source-backed transaction anatomy and ring explainer establish one real +15 decoys.
- `transaction.go:1061–1088`: output range proofs and commitment balance, input pseudo-outputs = outputs +fee; verifies money accounting without publishing ordinary output amounts.
- `wallet/builder.go:250–270,295–330`: selected input total, recipient amount/fee/change; shared secret, one-time key, commitment, range proof, encrypted amount and memo. Source: https://github.com/blocknetprivacy/core/blob/5a0a5b510c1dce46f4eeb12c33a291052e44e7b3/wallet/builder.go#L295
- `wallet/memo.go:21–62,65–89`: encryption/decryption using shared secret and random padding. `protocol/params/memo.go:7–17`: fixed128-byte field and124-byte text payload. State field-size/length property precisely, rather than absolute claims that no third party can ever read a memo; explicit proof/viewing sharing can disclose it.
- `p2p/dandelion.go:21–47`: stem/fluff states,0.9continue probability,10-minute route epochs; article only needs conceptual stem-then-broadcast relay. Wording reduces exposure of origin; no guarantee of hiding IP in every network circumstance. Existing Dandelion guide/source research owns exact routing configuration.
- `api_handlers.go:100–140`: public transaction and confirmation/block status. Existing pinned-source payment-visibility research establishes public fee/hash/structure and private wallet amount/memo versus shared transaction proof/viewing access. Research: `site/editorial/batches/2026-10-privacy-faraday/research.md` and fact-sheet sections Payment disclosure/Faraday coin-set scope.
- Existing source-backed transfer-time guide establishes maturity/confirmation versus spendable balance; no new timing parameter is introduced here.

Faraday primary source opened directly:
https://blocknetcrypto.com/blog/2026-10-27-how-blocknet-privacy-survives-quantum-computers/

At retrieval, introduction says design remains under construction/testing and figures/dates/design may change. What-changes section specifies hash-based spend proof, ML-KEM receiving, full set of Faraday coins. The set grows as coins enter the new format, not every historical output immediately. No current quantum-security claim; no new dates, performance results, proof sizes, future fees or future wallet instructions in these articles. Source detail was already established in editorial fact-sheet; this refresh preserves the scoped interpretation.

## Conceptual statements and examples

Fungibility is defined as interchangeability of equal amounts of one currency in payment. Illustrative5BNTpurchase and twoequal5BNTreceipts are explanatory examples, not observed transactions, prices or merchant availability. Equal quantity versus changing exchange price is a conceptual distinction. Privacy reduces published transaction-history information and thereby supports the currency goal; it does not prove real-world acceptance behavior. Statements about invoices, conversations and chosen disclosure describe information supplied outside the public transaction record, not logging or retention measurements.

## Adjacent accuracy issue

The current generic privacy-coin article includes an old official homepage quote that overstates Faraday eligibility as every historical output. Parent requested replacing only that paragraph in all20locales with the precise proposed Faraday-coin-set wording. That separate scratch payload is `privacy-adjacent.json`. Other broad wording in the old article was flagged to parent but is outside this two-article refresh.

## Link token mapping

- E_VALIDATION = https://github.com/blocknetprivacy/core/blob/5a0a5b510c1dce46f4eeb12c33a291052e44e7b3/transaction.go#L1013
- E_FARADAY = https://blocknetcrypto.com/blog/2026-10-27-how-blocknet-privacy-survives-quantum-computers/
- S_RINGS = /blog/ring-signatures-explained/
- S_STEALTH = /blog/stealth-addresses-explained/
- S_NAMES = /blog/blocknet-id-pay-by-name/
- S_MEMOS = /blog/blocknet-encrypted-memos/
- S_PROOFS = /blog/bulletproofs-explained/
- S_TRANSACTION = /blog/blocknet-transaction-explained/
- S_RELAY = /blog/dandelion-plus-plus-explained/
- S_VISIBILITY = /blog/blocknet-payment-visibility/
- S_FARADAY = /blog/blocknet-faraday-privacy/
- S_FUNGIBILITY = /blog/blocknet-fungibility/
- S_PRIVACY = /blog/blocknet-privacy-features/
- S_SEND = /blog/send-receive-blocknet/
- S_SUPPLY = /blog/blocknet-supply/
- S_TIMING = /blog/blocknet-transfer-time/
- S_MONETARY = /blog/blocknet-faraday-monetary-policy/
- I_PRIVACY = /assets/blog/blocknet-privacy-default.svg
- I_FUNGIBILITY = /assets/blog/blocknet-fungibility.svg

Graphics coordinated with parent. Privacy: one ordinary-payment frame;1ring16withoutidentifyingreal,2one-timeoutput,3amountcommitment. Fungibility: twoillustrative5BNTreceipts represent equaldenominatedvalue; no spendamount/fee claim. Alt and explanatory paragraphs match these scopes.

## Responsive correction

The 320-pixel browser pass found that the long Russian noun in the fungibility H1 overflowed the content column. The Russian title was rewritten with the equivalent plain-language meaning “why equal amounts of BNT can replace one another”; the body and keyword-bearing description remain unchanged. The complete site was rebuilt and the affected narrow-width check repeated. No global CSS change was needed. Existing Arabic/Thai social-image fallback remains English; their article copy and metadata are localized.
