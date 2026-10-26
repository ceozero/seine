# what-is-a-privacy-coin: research notes

Post: `src/content/blog/what-is-a-privacy-coin/` ("What is a privacy coin? How private
cryptocurrencies work"), drafted 2026-10-25. English `sourceHash` 603362df02e6 (1,461 body words);
zh-Hans and zh-Hant are `translation: draft` (structure checked against the source with a local copy
of the translation checks; only the expected "must be reviewed" errors remain).

## Intent

Reader's job: understand what a privacy coin is in general, what a transparent chain such as Bitcoin
reveals, how privacy coins hide sender, receiver, amount and network origin, and why privacy by
default matters. Nearest owners: `what-is-blocknet` (lists "Blocknet privacy coin" as a supporting
phrase; answers "what is Blocknet") and `blocknet-privacy-features` (Blocknet's layers in depth).
This post owns the coin-agnostic concept and routes Blocknet detail to those posts; batch-3 siblings
(ring signatures, stealth addresses, Bulletproofs, Dandelion++) own the mechanics of each technique.

## Keyword-map row (proposed)

| Primary keyword cluster | URL | Search job | Supporting phrases |
|---|---|---|---|
| what is a privacy coin | `/blog/what-is-a-privacy-coin/` | Explain what a privacy coin is, what a transparent chain reveals, how privacy coins hide sender, receiver and amount, and why privacy by default matters; Blocknet as the worked example | privacy coin meaning, privacy cryptocurrency, how privacy coins work, private by default crypto, privacy coin vs bitcoin, 什么是隐私币 / 什麼是隱私幣 |

Boundaries: one paragraph per technique here, depth in the sibling explainers; one bulleted Blocknet
summary here, depth in `blocknet-privacy-features`. Overlap (2026-10-25): 0.9% with
ring-signatures-explained (draft), 0.7% with blocknet-privacy-features (the shared Faraday quote),
0.3% with what-is-blocknet.

## Facts used from the fact sheet

Ring of exactly 16 (15 decoys), CLSAG, consensus-enforced; one-time stealth addresses; Pedersen
commitments with 64-bit Bulletproofs; Dandelion++; no transparent mode (§1 Privacy). Key images stop
double spends; Dandelion++ routes rotate every 10 minutes (§9). 128-byte memo, 124 bytes plaintext
(§1), readable by sender and receiver only, padded (§9). Address = spend_pub + view_pub, 92-93
characters, written "90-plus" (§1, §6). Argon2id ~2 GB per hash (§1, §2). seine on Windows, macOS,
Linux, NVIDIA on Windows/Linux archives, auto-tuning (§4). Faraday full-chain quote (§0, §9).

## Facts added (general sources, checked 2026-10-25)

- Bitcoin whitepaper §10 Privacy: "The public can see that someone is sending an amount to someone
  else, but without information linking the transaction to anyone." Source:
  https://bitcoin.org/bitcoin.pdf (text extracted with pdftotext).
- Ring signatures: Rivest, Shamir, Tauman, "How to Leak a Secret", ASIACRYPT 2001.
- CryptoNote v2 white paper (Nicolas van Saberhagen, 2013) introduced ring signatures and one-time
  addresses to cryptocurrency; Monero (initial release 18 April 2014) is based on it, and its privacy
  features are enforced by default. Source: https://en.wikipedia.org/wiki/Monero
- CLSAG: Goodell, Noether, RandomRun, "Concise Linkable Ring Signatures and Forgery Against
  Adversarial Keys" (IACR ePrint 2019/654); Monero adopted it in October 2020. Blocknet uses CLSAG
  per fact sheet §1.
- Bulletproofs: Bünz, Bootle, Boneh, Poelstra, Wuille, Maxwell, "Bulletproofs: Short Proofs for
  Confidential Transactions and More", IEEE S&P 2018 (IACR ePrint 2017/1066). Smaller than earlier
  range proofs.
- Dandelion++: Fanti et al., "Dandelion++: Lightweight Cryptocurrency Networking with Formal ...
  Guarantees", ACM SIGMETRICS 2018 (arXiv 1805.11060): stem phase then fluff phase.
- Zcash: initial release 28 October 2016; zero-knowledge proofs (zk-SNARKs); shielded addresses hide
  sender, recipient and amount; transparent addresses work like Bitcoin's; funds can move between
  them. Source: https://en.wikipedia.org/wiki/Zcash
- Fungibility as the interchangeability of units is a standard definition; no numbers attached.

## Wording decisions

- Pool payouts (not coinbase outputs) are described as arriving on stealth addresses with hidden
  amounts, since bntpool.com pays miners with ordinary wallet transactions.
- Zcash and Monero described factually, no ranking. "Anonymity set" avoided (check forbids
  "anonymity"); written as "the group each spend hides in".
- `related: []` per the brief, so strict check keeps one warning ("list 2-4 related posts").
