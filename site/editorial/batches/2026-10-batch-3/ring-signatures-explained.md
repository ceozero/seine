# ring-signatures-explained (batch 3, 2026-10-25)

## Intent

A reader searching "ring signatures explained" (any coin) wants to understand how a signer hides
in a group of public keys, how key images make ring signatures linkable to stop double spends, and
what CLSAG and ring size mean; the nearest owner is `/blog/blocknet-privacy-features/`, which
covers Blocknet's ring of 16 in one section, while this post adds the general mechanism and history
(RST 2001, LSAG 2004, CryptoNote key images, RingCT/MLSAG, CLSAG) with Blocknet as the worked
example and routes to the privacy post, seine and bntpool.com.

Suggested keyword-map row:

| ring signatures explained | `/blog/ring-signatures-explained/` | Explain how ring signatures work (signer hidden among public keys, key images, CLSAG, ring size) for any coin, with Blocknet's ring of 16 as the example | what is a ring signature, how do ring signatures work, linkable ring signature, key image, CLSAG ring signature, ring size, 环签名 / 環簽章 |

Boundary: the privacy post keeps one section on Blocknet's ring and links here for the mechanism;
this post keeps one paragraph on stealth addresses and amounts and links to the privacy post (and
to `stealth-addresses-explained` / `bulletproofs-explained` once published).

Overlap (`npm run overlap`): 3.0% of 8-word phrases shared with blocknet-privacy-features (mostly
the quoted daemon line and ring-of-16 facts), 1.0% with what-is-a-privacy-coin, 0.3% with
bulletproofs-explained.

## Facts from the fact sheet

- CLSAG with RingCT, ring exactly 16, "ring of 16 (15 decoys)" (§1 Privacy features).
- Fixed size "to prevent information leakage from variable ring sizes"; ring members must be real
  on-chain outputs; key images stop double spends (§9).
- No transparent mode (§1). Stealth addresses, Pedersen commitments + Bulletproofs (§1).
- Faraday quotes and date (~2027-02-16, planned, design/testing/adversarial review) (§0, §9).
- seine's default pool is bntpool.com (§3 line 250); automatic thread sizing (§9 macOS line, §4).

## New facts verified in code (blocknet-core@pool, checked 2026-10-25)

- Key image `I = x * Hp(P)`, `Hp` = SHA-512 hash to a Ristretto point with domain
  `blocknet_hash_to_point`: `git show pool:crypto-rs/src/ring.rs` lines 29-36, 125-158.
- RingCT signature proves both key ownership and that the pseudo-output commits to the same amount
  as the real ring member ("Signer knows private key for one ring member"; "Pseudo-output
  commitment contains same amount as that ring member's commitment"): `crypto-rs/src/ring.rs`
  lines 1-10, 423-441. Signature carries c_0, s and t responses, key image and pseudo-output
  (lines 609-636). Not described in the post as identical to Monero's CLSAG layout; the post only
  says "CLSAG and RingCT" (the code's own label) and what the proof establishes.
- Ring member selection: decoys come from the canonical output index, shuffled with Fisher-Yates
  using `crypto/rand`; the real key goes at a random index from `crypto/rand`:
  `git show pool:block.go` lines 2836-2933 (`SelectRingMembersWithCommitments`,
  `finalizeRingSelection`).
- Validation: duplicate key images within one transaction rejected (`transaction.go:987-995`);
  key image and pseudo-output must match the signed RingCT payload, then the key image is checked
  against the spent set (`transaction.go:1027-1045`); ring size check (`transaction.go:1000-1005`);
  spent-set `MarkSpent` (`transaction.go:452-463`).

## External sources (general background)

- Rivest, Shamir, Tauman, "How to Leak a Secret", ASIACRYPT 2001, LNCS 2248 pp. 552-565.
  https://people.csail.mit.edu/rivest/pubs/RST01.pdf (read 2026-10-25): cabinet member of "Lower
  Kryptonia" leaking to a journalist; no group managers, no setup; name chosen because "rings are
  geometric regions with uniform periphery and no center".
- Liu, Wei, Wong, "Linkable Spontaneous ... Group Signature for Ad Hoc Groups", ACISP 2004,
  https://eprint.iacr.org/2004/027 (LSAG; the full title contains a word the check forbids, so the
  post uses "LSAG" only).
- CryptoNote v2.0 whitepaper (Nicolas van Saberhagen, 2013): one-time ring signatures with key
  images. https://bytecoin.org/old/whitepaper.pdf (background; general knowledge, Wikipedia "Ring
  signature" also notes CryptoNote's use).
- Shen Noether, "Ring Signature Confidential Transactions for Monero", ePrint 2015/1098,
  https://eprint.iacr.org/2015/1098 (MLSAG).
- Goodell, Noether, Blue, "Concise Linkable Ring Signatures and Forgery Against Adversarial Keys",
  ePrint 2019/654, https://eprint.iacr.org/2019/654.
- Moneropedia CLSAG, https://www.getmonero.org/resources/moneropedia/clsag.html (read 2026-10-25):
  mandatory from the October 2020 upgrade; verification about 20% faster; 2-in/2-out transaction
  about 2.5 kB to 1.9 kB.
- Monero v0.18 "Fluorine Fermi" upgrade, 13 August 2022: ring size 11 to 16
  (https://lists.getmonero.org/hyperkitty/list/monero-announce@lists.getmonero.org/2022/7/,
  https://decrypt.co/107441/monero-rolls-out-enhanced-privacy-features-with-hard-fork).

## Wording notes

- "anonymous"/"anonymity" are forbidden by the check, so CLSAG/LSAG/MLSAG acronyms are not expanded
  and "anonymity set" is avoided.
- The Faraday quantum line is quoted from blocknetcrypto.com in the future tense.
- `related: []` per the brief; the strict check's "list 2-4 related posts" warning is expected.
