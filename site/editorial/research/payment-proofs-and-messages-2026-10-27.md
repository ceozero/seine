# Payment proofs and message signatures

Reviewed October 27, 2026, America/New_York (EDT). User approved publication in all 20 languages. One translation agent; translations remain draft without an independent-review claim.

## Source pins and claim boundaries

CLI v1.2.0: `948af4de8b7a3e3cddc86a329c7d2d003cb3fd6b`. Core v0.22.0: `5a0a5b510c1dce46f4eeb12c33a291052e44e7b3`. Latest release tags rechecked through GitHub. Core master has advanced; these guides describe the release tag, not unreleased changes.

- CLI `attach_wallet.go:659-691`: sign reads one line, trims leading/trailing whitespace, requires nonempty text, caps it at 1024 bytes, posts to wallet/sign, prints signature.
- CLI `attach_wallet.go:693-752`: verify prompts for address, message, signature; trims outer whitespace; posts to public verify and prints the VALID/INVALID result.
- CLI `attach_wallet.go:1343-1380`: prove accepts one 64-hex transaction ID, posts to wallet/prove, prints TxID and Tx Key. No wallet-wide key is required by the recipient-verification workflow.
- CLI `docs/reference-core.md:264-318,493-519`: signing/verification prompt sequences, limits and full/view-only distinctions.
- Core `api_handlers.go:227-282`: verify checks the message against the spending public key parsed from the address, accepts a 64-byte hex-encoded signature and returns valid. Its logic does not enforce challenge freshness, identity, expiry, balance or payment status.
- Core `api_handlers.go:358-481`: verify-proof validates the transaction key against the transaction public key, then reports recipient output matches, amounts, optional memo and total_matched. A true valid field alone is insufficient to establish recipient receipt. Amount fields are atomic integers; 100,000,000 atomic units per BNT (also explorer.go:857).
- Core `api_handlers.go:941-981`: full-wallet message signing uses the spending key and returns address, signature and message. View-only signing is rejected. No transaction construction/broadcast occurs in this handler.
- Core `api_handlers.go:2267-2335`: proof generation requires a loaded/unlocked wallet and transaction on local chain; rejects coinbase and mismatched sender-derived key. Derivation uses private viewing material and works with the corresponding view-only wallet.
- Official https://blocknetcrypto.com/api documents public verify and verify-proof without bearer tokens or a loaded wallet. Example local API port 8332 is configurable. JSON property names in article code are exact; placeholder values are deliberately nonfunctional.

Suggested fresh challenges, intended-purpose checks, recording used challenges and expiry checks are application guidance inferred from signature verification's limited inputs. They are not automatic wallet features. The guide explicitly distinguishes cryptographic validity from the verifier's authorization rules.

## Explorer observation

Read the public transaction page for `aa8ee7cc945e0cd3370d3fa9c2821752a59b72fa5e90a84a0c3afa11bd5994a7` in shared Windows Chrome. Inspected empty proof UI only; no private information submitted. The released template labels a sent-proof input as a view private key, although its handler checks it as the transaction private key (`explorer_templates.go:546-565`, `explorer.go:782-836`). The article therefore teaches the explicit documented API fields rather than sending readers through that form. No public-facing criticism or misleading UI instruction is added.

## Search intent

Payment proof owns generating and checking transaction-specific evidence, including the separate key-validity, recipient-match and chain-status checks. Sending and explorer guides remain the creation/public-lookup owners. Message signatures own agreed address-control challenges and their verification, distinct from receipts, wallet creation and the ring-signature explainer.

Both guides use original explanatory SVGs and exact documented command examples. No real wallet, seed, key, proof, funds, transaction, rented hardware or mining job is used. Signing and proof success are source-verified procedures, not claimed live wallet tests.

English strict checks pass. The two guides share 1.9% of their eight-word phrases, primarily the version introduction and common wallet context; existing guides overlap at most 0.3%. Their procedures and search jobs are distinct. All 80 existing related-article bodies remain unchanged; only related links and corresponding translation source hashes are updated.
