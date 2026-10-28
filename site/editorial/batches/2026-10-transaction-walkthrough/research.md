# Inside a Blocknet transaction

Checked October 27, 2026 (EDT). User skipped Android, accepted a practical inputs/outputs/change walkthrough with a diagram, and authorized publication in all 20 languages with “proceed”. One translation subagent handles 17 locales; parent authors English and both Chinese translations, verifies sources, integrates and checks. Translations remain draft; no independent linguistic review is claimed. No payments, hardware rentals or mining jobs.

## Reader job and scope

Understand why spending one output can pay a smaller amount, why one recipient can produce multiple outputs, where change goes, and how this relates to wallet versus explorer records. Existing fee guide owns exact fee calculation and preview procedure, send/receive owns actual sending, timing owns maturity intervals, visibility owns disclosure boundaries. The user explicitly approved fees/change as part of the explanation; that scope overrides general marketing guidance not to volunteer fees. No search-volume claim.

## Primary evidence

Released core v0.22.0, commit `5a0a5b510c1dce46f4eeb12c33a291052e44e7b3`; verified latest released version at https://github.com/blocknetprivacy/core/releases/tag/v0.22.0 . Read pinned source using git show without changing the daemon checkout.

- https://github.com/blocknetprivacy/core/blob/5a0a5b510c1dce46f4eeb12c33a291052e44e7b3/wallet/builder.go : Transfer lines135–206 reserves mature inputs to cover recipients plus estimated fee; ordinary build uses one change output when remainder is positive. TransferWithInputs lines209–247 permits selected inputs and change splitting. buildTransaction lines254–450 computes remainder; recipient output derivation uses recipient keys; positive change derives one-time keys from the sending wallet's public keys and splits the remainder if requested. The implementation appends recipient outputs then change; article makes no output-shuffling or position-unlinkability claim. TransferAll lines454–596 subtracts fee and creates one recipient output without change.
- https://github.com/blocknetprivacy/core/blob/5a0a5b510c1dce46f4eeb12c33a291052e44e7b3/wallet/coinselect.go : whole OwnedOutput selection, exact-match preference, multiple-input selection. The article does not promise a particular selection order or algorithm outcome.
- https://github.com/blocknetprivacy/core/blob/5a0a5b510c1dce46f4eeb12c33a291052e44e7b3/wallet/wallet.go : maturity/spendable balance at lines713–767, ReserveMatureInputs at1042. Unspent output ownership differs from immediate spendability. No new maturity constants are asserted; existing transfer-time guide supplies precise timing.
- https://github.com/blocknetprivacy/core/blob/5a0a5b510c1dce46f4eeb12c33a291052e44e7b3/transaction.go : TxInput, TxOutput, Transaction and TxID lines25–113; fee public and separate from outputs, hidden amounts and one-time keys, rings with real member plus decoys, key images. Validation lines961–1145 checks ring proofs, repeated spends, ranges and commitment balance against fee. Transaction hash covers canonical serialization, not one recipient output.
- Existing source-backed privacy, ring-signature, stealth-address, range-proof, payment-visibility, send/receive and transfer-time articles support the linked explanation. The diagram shows the wallet's accounting, not traceable public graph edges; no public label identifies the sender's reusable address as change.

## Example and graphics

10 BNT selected, 3 BNT recipient, 6.9995 BNT change and assumed0.0005 BNT fee. Arithmetic sums exactly; identical to the existing fee guide's illustrative example for consistency. It is not a measured payment, current quote or rate promise. Inline-code amounts remain byte-identical in translation. The original SVG uses numerical badges with localized alt text and a localized prose legend. Fee branch differs from recipient/change outputs; no fabricated wallet interface.

## Integration and checks

Three existing owners link through related metadata in all20 locales. Displaced related targets remain linked in the existing article bodies. English source hashes are propagated without changing those bodies or their linguistic review statuses. New page belongs to the Blocknet topic. Local and live checks and reviewed desktop/mobile captures are archived in the stable transaction-walkthrough showcase.
