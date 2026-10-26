# how-crypto-mining-works: research notes

Post: `src/content/blog/how-crypto-mining-works/` ("How crypto mining works"), drafted
2026-10-25. English `sourceHash` 7056e4fdd708; zh-Hans and zh-Hant are `translation: draft`.
`npm run check -- --strict how-crypto-mining-works`: 0 errors, one warning ("list 2-4 related
posts"), left on purpose because the brief requires `related: []`.

## Intent

Reader's job: understand how proof-of-work mining works in general (blocks, headers, hashes,
nonce, target and difficulty, difficulty adjustment, block rewards, pools and shares, heaviest
chain and confirmations), whatever coin they have in mind. Nearest owners: `how-to-mine-blocknet`
(the procedure) and `argon2id-proof-of-work-explained` (Argon2id internals). This post adds the
coin-agnostic concepts, with Blocknet's real parameters as the worked example, and routes to
both.

## Keyword-map row (proposed)

| Primary keyword cluster | URL | Search job | Supporting phrases |
|---|---|---|---|
| how crypto mining works | `/blog/how-crypto-mining-works/` | Explain proof-of-work mining in plain words (blocks, hashes, nonce, difficulty, rewards, pools and shares) with Blocknet as the worked example, then route to the mining guide | how does cryptocurrency mining work, what is crypto mining, mining difficulty explained, what is a mining pool share, block reward explained, 加密货币挖矿原理 / 加密貨幣挖礦原理 |

Boundaries: `how-to-mine-blocknet` owns the steps (this post ends with a three-step summary and a
link); `argon2id-proof-of-work-explained` owns how the Argon2id hash works and why it needs 2 GiB
(this post has one paragraph and a link); `blocknet-mining-hardware-hashrate` owns hardware
results (this post quotes two best results and links). Pool-side jobs (PPLNS details, payouts)
stay with bntpool.com's blog; this post has one three-bullet list. Overlap report: 1.0% shared
8-word phrases with how-to-mine-blocknet, 0.7% with blocknet-mining-hardware-hashrate and
what-is-blocknet.

## Facts used from the fact sheet

5-minute (300 s) blocks, 288/day, 10 safe confirmations, 60-block coinbase maturity, 100-block
max reorg (§1, §2); LWMA window 60, solvetime clamp 1-1,800 s (§1); target = (2^256-1)/difficulty,
difficulty ≈ expected hashes per block, network H/s ≈ difficulty/300, expected solo blocks/day =
288 × share (§1, §2); Argon2id 2 GiB, 32-byte output, nonce = password, header without nonce =
salt (§1); "designed to resist ASICs" wording (§6); coinbase exactly one output equal to the
reward, genesis has no transactions (§1); reward 723.25 BNT start, monthly step of 8,640 blocks,
~100M over 4 years, 2.0 BNT tail (§1); bntpool PPLNS 6h, 0.1 BNT minimum, 60 blocks, vardiff ~10
shares / 5 min (§3); 2 GiB per thread, CPU + NVIDIA rates add (§4); 49.4 H/s Zen 5 at 32 threads
(owner-approved update, §5), M4 Max 30.9 H/s (best measured; not presented as balanced);
a hash writes ~2 GiB and reads ~2 GiB (§9); Faraday "lighter proof of work", date (§0); update
checks at startup and every 12 h (§4). 16 GB → six or seven threads is the arithmetic already
used in how-to-mine-blocknet's FAQ.

Hypothetical example: "a difficulty of 6,000,000 would mean about 20,000 H/s" (6,000,000 / 300)
and "one thousandth of the network → 0.288 blocks/day, one per ~3.47 days" (288 / 1000). Both
are labelled as examples in the post; no live figures are quoted.

## Facts added (verified 2026-10-25)

Refs: `blocknet-core@pool` = c646196; `blocknet-pool@master` = 9bf4eb6.

- Block header fields: Version, Height, PrevHash, MerkleRoot, Timestamp, Difficulty, Nonce.
  `blocknet-core@pool:block.go:82-90`
- First transaction must be the coinbase. `blocknet-core@pool:block.go:289-291`
- A hash is valid when it is at or below the target (byte-wise compare; equal is valid).
  `blocknet-core@pool:crypto-rs/src/pow.rs:143-160`
- Fork choice: cumulative work = parent work + block difficulty; a node reorganizes to a block
  whose cumulative work exceeds the current tip's ("Does this create a heavier chain?").
  `blocknet-core@pool:block.go:40-45`, `:1847-1871`
- Pool shares: each share is checked against a share target from the connection's share
  difficulty ("low difficulty share" otherwise); a share whose hash also meets the network
  target is a block candidate and is submitted as a block.
  `blocknet-pool@master:crates/pool-runtime/src/engine.rs:884-887`, `:966-975`, `:1122-1130`
- External (general background, cited for the concept only):
  - Bitcoin whitepaper (Nakamoto, 2008) introduced proof-of-work block chains with a
    moving-average difficulty target. https://bitcoin.org/bitcoin.pdf
  - Bitcoin targets 10-minute blocks and retargets every 2,016 blocks (about two weeks).
    https://developer.bitcoin.org/devguide/block_chain.html
  - Bitcoin uses SHA-256 (double), and most Bitcoin mining is done on ASICs.
    https://en.wikipedia.org/wiki/Bitcoin#Mining

## Not used

Transaction fees (Blocknet's coinbase is subsidy only and the fee destination is unverified,
§7), live difficulty/hashrate/reward, pool and dev fees, GPU hashrates.
