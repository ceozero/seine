# Atomic swaps and the public VEIL announcement

Checked October 28, 2026 (America/New_York, EDT). User approved the article and then explicitly selected a general explainer with a short VEIL announcement section when a public implementation could not be verified.

## Intent and evidence boundary

Explain generic two-party conditional settlement, successful claims, refund paths and disclosure to a Blocknet reader, then identify what the public VEIL announcement establishes. Nearest owners: ordinary send/receive (one payment), payment visibility (ordinary BNT disclosure), and Faraday upgrade (network transition). No separate owner currently explains cross-chain exchange. Search demand is inferred from the user's approved currency/privacy direction, not measured query volume. Search results primarily return generic atomic-swap research and the project's brief announcement.

The source is deliberately not a VEIL tutorial. No supported asset pair, available service, current wallet command, VEIL-specific contract design or numerical timeout is asserted. No private specification is published, linked, quoted, or used as evidence for protocol mechanics. Anonymous web access did not expose a public VEIL repository. Unverified details remain outside this article. The generic diagram's A/B labels do not represent a supported BNT pair.

## Public primary sources

1. Maurice Herlihy, *Atomic Cross-Chain Swaps*, PODC 2018: https://arxiv.org/abs/1801.09515 and https://arxiv.org/pdf/1801.09515. Pages 1–2 describe coordinated conditional transfers, phase order, shared-secret disclosure and staggered deadlines. The paper conditions protection on conforming parties; stopping after the other side claims is not an automatic safe cancellation. Article uses these distinctions, without promising instant settlement or unconditional recovery.
2. Sean Bowe and Daira Hopwood, BIP 199: https://github.com/bitcoin/bips/blob/master/bip-0199.mediawiki. Status Closed; dual BSD-3-Clause/CC0. Summary and script show a preimage plus designated recipient signature on the claim branch and a timeout plus refund-party signature on the other branch. Interaction shows funding, claim revelation or timeout recovery. Article identifies its closed status and does not represent it as a Blocknet specification. The same public hash and disclosed preimage in the generic two-chain example provide cross-chain linking evidence (direct inference from script/flow).
3. Peter Todd, BIP 65: https://github.com/bitcoin/bips/blob/master/bip-0065.mediawiki. Public domain. Abstract, summary and non-interactive-refund section: timelock makes a spend valid only at/after a condition. It does not itself submit a transaction. Article describes refund eligibility and the need for transaction management, without prescribing timeout values.
4. Blockstream's own glossary: https://help.blockstream.com/education/glossary/atomic-swap. Read as supporting conceptual background for noncustodial conditional exchange. We do not reuse its broad “simultaneously” simplification: the article explicitly says chains process separate transactions. No competitor comparison or specific pair recommendation is included.
5. Official Blocknet overview: https://blocknetcrypto.com/#faraday (read October 28). Its comparison includes VEIL and presents a post-quantum redesign as a Faraday goal. It supplies no pair, command, timeout or verified end-user swap service for this article. This is the only source for VEIL claims. Faraday remains a planned upgrade. No unannounced design details are introduced.
6. Existing source-pinned payment visibility owner: site/src/content/blog/blocknet-payment-visibility/index.mdx, based on released public core v0.22.0, 5a0a5b510c1dce46f4eeb12c33a291052e44e7b3. Ordinary payments distinguish public fields from sender/recipient knowledge and viewing access. Article routes there rather than repeating its mechanics or assuming they establish whole-swap privacy.

## Structure and diagram

One Answer, three FAQ answers, six question headings, four numbered steps, one original SVG and one CTA. Diagram uses the established blog palette, generic chain labels A/B, funding steps 1–2, reverse-order claims 3–4, shared-secret cue and dashed curved refund paths. Caption explicitly identifies a general example, not a VEIL interface or actual transaction. No test funds, swap service, wallet keys or rented hardware are involved.

## Integration

Add to Blocknet topic and related reading from `what-is-blocknet` and `blocknet-faraday-upgrade`. Displaced related links remain in each original body. Across those 40 MDX files only source related metadata and matching translation hashes change; body text and review status are preserved. Existing article titles, dates, intent and source evidence remain unchanged. New translations remain draft unless separately reviewed; no independent linguistic review is claimed.

## Validation evidence

Two existing translation agents handled 10 and 9 locales, with no additional subagents. Both report all assigned locales passing strict checks and preserving the 27 blank-line body parts, six headings, four numbered steps, three FAQs, ten link occurrences, designated-recipient authorization and BIP 199 status. All new translations remain `translation: draft` with English sourceHash `d62e4e93d4c6`; no separate linguistic review is claimed. Parent checks independently confirm structure, protected values, links and hashes across all 20 versions.

`node scripts/check-content.mjs blocknet-atomic-swaps --strict`: passed. `npm run check`: 61 source posts passed, release and benchmark facts consistent. `npm run check:release`: Seine v0.2.44 verified against GitHub. All four external article sources returned HTTP 200. Wording-overlap tool found 0% shared eight-word phrases among its top matches; the semantic ownership boundaries above are the separate reason for a new URL.

Build, rendered-page, locale, browser and production verification evidence is retained at the stable local showcase directory `/home/zp/Code/blocknet/showcases/blog-i18n/atomic-swaps`; URL `http://localhost:8874/atomic-swaps/`. Its revision record is filled when the source is committed. The full source and built assets are archived before task-worktree cleanup.
