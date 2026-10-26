# bulletproofs-explained: research notes

## Intent

A reader searching "bulletproofs explained" (or "Pedersen commitment", "confidential transactions
range proof") wants to understand how a coin hides amounts yet still proves no coins were created;
the nearest owner, `/blog/blocknet-privacy-features/`, gives amounts one short section, while this
post explains Pedersen commitments, the negative-amount problem, how Bulletproofs reach 672 bytes,
and shows each check in Blocknet's code and on its explorer.

## Proposed keyword-map row

| bulletproofs explained | `/blog/bulletproofs-explained/` | Explain Pedersen commitments and Bulletproofs range proofs for anyone, then show how Blocknet verifies hidden amounts | pedersen commitment, confidential transactions, range proof, bulletproofs size, hidden transaction amounts, Bulletproofs 详解 / 詳解, Pedersen 承诺 / 承諾, 范围证明 / 範圍證明 |

Boundary: `/blog/blocknet-privacy-features/` keeps its one "how does Blocknet hide amounts" section
and links here for the mechanics; this post summarizes the other privacy layers in one sentence
and links back.

Overlap (scratch reimplementation of `npm run overlap`, because the script currently crashes on
another in-progress batch-3 folder): 0.6% of 8-word phrases shared with blocknet-privacy-features,
0.3% with ring-signatures-explained, 0.2% with stealth-addresses-explained.

## Facts used (outside or beyond the fact sheet)

External, general:
- Bünz, Bootle, Boneh, Poelstra, Wuille, Maxwell, "Bulletproofs: Short Proofs for Confidential
  Transactions and More", IACR ePrint 2017/1066, IEEE S&P 2018. Abstract (fetched 2026-10-25):
  "without a trusted setup; the proof size is only logarithmic in the witness size", range proof
  "using only 2log2(n)+9 group and field elements", "Proof generation and verification times are
  linear in n", improves on "linear (in n) sized range proofs in existing proposals for
  confidential transactions", aggregation adds "only an additive O(log(m)) group elements",
  "verification of multiple Bulletproofs can be batched", relies "only on the discrete logarithm
  assumption". https://eprint.iacr.org/2017/1066
- Pedersen commitment: T. P. Pedersen, "Non-Interactive and Information-Theoretic Secure
  Verifiable Secret Sharing", CRYPTO '91 (LNCS 576). Hiding (perfect) and binding (under discrete
  log) are the standard properties. https://en.wikipedia.org/wiki/Commitment_scheme
- Ristretto/Ed25519 group order l = 2^252 + 27742317777372353535851937790883648493 (about 2^252).
  https://ristretto.group/ ; RFC 8032.
- Fiat-Shamir heuristic: standard; Bulletproofs paper section 4.4.
- Monero v0.13.0 release: "the October 18th network update, which in turn enabled Bulletproofs for
  reduced transaction sizes". https://www.getmonero.org/2018/10/11/monero-0.13.0-released.html
  (fetched 2026-10-25)
- dalek-cryptography/bulletproofs: Rust implementation over Ristretto
  (https://github.com/dalek-cryptography/bulletproofs; crates.io `bulletproofs`).

Blocknet code (`git -C /home/zp/Code/blocknet/blocknet-core show pool:<path>`):
- Commitment formula `commitment = value*G + blinding*H`, random blinding:
  `crypto-rs/src/commitment.rs:7`, `:22-29`; add/subtract commitments `:106`, `:146`.
- Range proof: 64 bits (`RANGE_BITS = 64`), transcript label `b"Blocknet Range Proof"`,
  `RangeProof::prove_single` (one proof per output): `crypto-rs/src/rangeproof.rs:7-8`, `:39-47`.
- Library: `bulletproofs = "5.0"`, `curve25519-dalek = "4.1"`, `merlin = "3.0"`:
  `crypto-rs/Cargo.toml`.
- Proof size 672 bytes: dalek `RangeProof::to_bytes` = 7 × 32 (A, S, T1, T2, t_x, t_x_blinding,
  e_blinding) + inner-product proof `(2·lg n + 2) × 32` = 224 + 448 = 672 for n = 64
  (`~/.cargo/registry/src/*/bulletproofs-5.0.0/src/range_proof/mod.rs:488-500`,
  `src/inner_product_proof.rs:331-335`). Confirmed live on the explorer (2026-10-25, block 69,022,
  tx 40c081a1…076fa): "range proof 672 bytes · Bulletproof", "amounts hidden · Pedersen
  commitments". Explorer template: `explorer.go:1185`.
- Output fields: Pedersen commitment, range proof proving `[0, 2^64)`, amount "encrypted with ECDH
  shared secret ... The recipient can decrypt this with their view key": `transaction.go:24-34`.
- Node verifies every output's range proof, then the balance `sum(pseudo_outputs) = sum(outputs)
  + fee`; "The RingCT signatures prove that each pseudo_output commits to the same amount as the
  corresponding real input"; fee committed with "fee is public, blinding = 0":
  `transaction.go:1046-1061`, `:1066-1074`, `:1110`, `:1128`.
- Coinbase: node rebuilds the expected commitment for `GetBlockReward(height)` with a
  deterministic blinding and requires a match: `block.go:663-680`.
- Ring of 16, stealth addresses, Dandelion++, no transparent mode: fact sheet section 1.

## Choices

- "Hides every amount" is phrased as every output/payment amount; the post states that the network
  fee is public because the balance equation needs it.
- Kept other projects factual (Monero's 2018 adoption, dalek library); no rankings.
- `related: []` per the brief; the strict check's only warning is "list 2-4 related posts".
