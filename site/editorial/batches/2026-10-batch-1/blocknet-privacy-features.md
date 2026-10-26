# blocknet-privacy-features: research notes

Post: `src/content/blog/blocknet-privacy-features/` ("How Blocknet keeps payments private"),
drafted 2026-10-25. English `sourceHash` a21e8ef23a89; zh-Hans and zh-Hant are `translation: draft`.

## Intent

Reader's job: understand what each Blocknet privacy layer hides and how, and what that means
when they send or receive BNT. Nearest owner: `what-is-blocknet` (overview that names privacy
in one section). This post adds the layer-by-layer mechanics (ring of 16 and key images,
stealth one-time keys and the view key, commitments plus range proofs, Dandelion++ stem/fluff,
fixed-size memo padding), a "what an observer sees vs what the receiver sees" walkthrough, and
the attributed Faraday privacy roadmap.

## Keyword-map row (proposed)

| Primary keyword cluster | URL | Search job | Supporting phrases |
|---|---|---|---|
| blocknet privacy | `/blog/blocknet-privacy-features/` | Explain each layer of Blocknet's mandatory privacy (ring of 16, stealth addresses, Bulletproofs, Dandelion++, encrypted memos) and what it means when you pay | blocknet ring signatures, blocknet stealth address, blocknet ring size, blocknet encrypted memo, is blocknet private, Blocknet 隐私 / Blocknet 隱私 |

Boundary: `what-is-blocknet` summarizes privacy in a paragraph and links here; this post owns
the mechanics and does not cover launch, emission or mining beyond one link.

## Facts used from the fact sheet

Ring of exactly 16 (CLSAG, RingCT), one-time stealth addresses, Pedersen commitments with
64-bit Bulletproofs, Ed25519/Ristretto (curve25519-dalek), Dandelion++ stem probability 0.9,
128-byte memo with 124 bytes of plaintext, no transparent mode, Faraday quotes and dates
(https://blocknetcrypto.com/#faraday).

## Facts added (verified in `blocknet-core@pool`, commit c646196, 2026-10-25)

- Ring size is fixed "to prevent information leakage from variable ring sizes".
  `crypto.go:659-660`
- Every ring member must be a canonical on-chain output; non-canonical members are rejected.
  `transaction.go:1007-1009`
- Key images prevent double spends "without revealing which output is spent"; a reused key
  image is rejected as a double-spend attempt. `transaction.go:51`, `transaction.go:452-461`
- Stealth construction: sender picks random r, publishes R = rG, shared secret = H(r·view_pub),
  one-time key = shared_secret·G + spend_pub; receiver scans with the private view key.
  `crypto-rs/src/stealth.rs:1-14`
- Address = spend public key + view public key (+ checksum). `wallet/wallet.go:244-256` (fact sheet)
- Commitment balance (inputs = outputs + fee) is verified by consensus.
  `transaction.go:1060`, `transaction.go:1067-1074`
- Range proofs prove the value is in [0, 2^64) "without revealing value".
  `crypto-rs/src/rangeproof.rs:8-11`
- Amounts are recoverable by the receiver: the blinding and the encrypted amount derive from
  the same per-output shared secret. `wallet/builder.go:294-316`
- Memos are encrypted with that same sender/receiver shared secret, so only the two parties
  can read them. `wallet/builder.go:317`, `wallet/memo.go:21-33`
- Short or empty memos are padded with cryptographic random bytes "to make empty memos
  indistinguishable". `wallet/memo.go:76-77`
- Dandelion++ stem routes change every 10 minutes (`EpochDuration`). `p2p/dandelion.go:30`

## Wording decisions

- The check fails on "anonymity" (and "anonymous"), so "full-chain anonymity sets" is written
  as the site's own sentence: "Today a spend hides among 16 outputs. After Faraday, it hides
  among every output on the chain." Never expand CLSAG (its name contains "Anonymous").
- `--strict` warns on every "post-quantum", so the Faraday item reads "spend proofs meant to
  stay secure against quantum computers", with the site's specifics (hash-based proofs in place
  of elliptic curves, ML-KEM payment detection), in the future tense and attributed. Chinese
  avoids 抗量子/后量子/後量子 for the same reason.
- Monero is mentioned only as "the same proven cryptography family", with handles and memos
  on top. No comparison of privacy strength.
- No claims about pool payouts' on-chain privacy: bntpool.com publishes recent payouts, so the
  mining mention is limited to a link to the guide and mining to an address or `@name`.
- The mandatory-privacy paragraph explains why opt-in users stand out without naming any coin.
