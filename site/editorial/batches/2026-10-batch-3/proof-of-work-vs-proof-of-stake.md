# proof-of-work-vs-proof-of-stake: research notes

Written 2026-10-25 for batch 3. Draft only (`draft: true`, translations `translation: draft`,
sourceHash ca93241ee795).

## Intent

A reader who searched "proof of work vs proof of stake" (or "PoW vs PoS", "difference between
proof of work and proof of stake") wants a neutral explanation of how each mechanism picks the
next block, what makes it secure and how it issues coins. Nearest owners:
`/blog/argon2id-proof-of-work-explained/` (how Blocknet's specific PoW hash works) and the batch-3
sibling `/blog/how-crypto-mining-works/` (mining mechanics in general). Unique here: the side-by-side
comparison of the two consensus families (block selection, chain choice, attack cost, issuance,
who can join) with Ethereum's PoS parameters, and why Blocknet chose memory-hard PoW. PoW mechanics
are kept to one paragraph plus Blocknet's four consensus facts; the Argon2id internals link out.

## Keyword-map row (proposed)

| proof of work vs proof of stake | `/blog/proof-of-work-vs-proof-of-stake/` | Explain neutrally how PoW and PoS choose blocks, stay secure and issue coins, and why Blocknet uses memory-hard PoW | pow vs pos, difference between proof of work and proof of stake, proof of stake explained, is blocknet proof of work, 51% attack, 工作量证明和权益证明的区别 / 工作量證明與權益證明的差異 |

Boundaries: the Argon2id explainer owns the hash internals and memory arithmetic; how-crypto-mining-works
owns the general mining walkthrough (hashes, difficulty, rewards, pools); this post owns the
PoW-vs-PoS comparison and only summarizes PoW in one section.

## Facts used from the fact sheet

Argon2id 2 GiB PoW; target = (2^256 − 1)/difficulty so difficulty ≈ hashes per block; 5-minute
blocks, 288/day; LWMA 60-block window; 10 confirmations ~50 min "safe"; MaxReorgDepth 100 blocks
(~8 h hard finality); genesis has no transactions; no premine/treasury/founder output, one coinbase
output = block reward; reward 723.25 BNT at month 0, exponential decay per 30-day month, 2.0 BNT tail
from month 48 "forever"; `pow.rs:1-4` "Memory-hard PoW to resist ASICs and ensure fair mining";
about 2 GB RAM per thread; seine auto threads from RAM, kernel comparison while mining, NVIDIA
on Windows/Linux alongside CPU, default pool bntpool.com, `@name` accepted; Faraday "A lighter
proof of work. New nodes catch up with the chain faster." planned ~2027-02-16
(https://blocknetcrypto.com/#faraday).

## Facts added (not in the fact sheet), with sources

Blocknet code:
- Nodes switch to a competing chain only when its cumulative work (sum of block difficulties) is
  higher: `addCumulativeWork` = parentWork + blockDifficulty; "Does this create a heavier chain?"
  `if blockWork > c.totalWork { reorganizeTo }`. Source: `blocknet-core@pool:block.go:40-45`,
  `block.go:1839-1871` (checked 2026-10-25).
- Deep reorgs are rejected: `enforceReorgFinalityLocked` "rejects reorgs that would disconnect
  finalized blocks" (MaxReorgDepth = 100). Source: `blocknet-core@pool:block.go:57`, `:2497-2500`
  (checked 2026-10-25).
- "Parallelism: 1 (single-threaded for fairness)". Source: `blocknet-core@pool:crypto-rs/src/pow.rs:14`
  (checked 2026-10-25; already quoted in batch-1 argon2id notes).
- No staking anywhere in consensus: `git grep -i stake|staking` on `pool` (*.go, *.rs) matches only
  the wordlist word "mistake" (checked 2026-10-25).

External:
- Bitcoin paper (Satoshi Nakamoto, https://bitcoin.org/bitcoin.pdf, published 2008-10-31):
  "Proof-of-work is essentially one-CPU-one-vote. The majority decision is represented by the
  longest chain, which has the greatest proof-of-work effort invested in it." (§4); "the probability
  of a slower attacker catching up diminishes exponentially as subsequent blocks are added" (§4);
  difficulty "determined by a moving average targeting an average number of blocks per hour" (§4);
  "the first transaction in a block is a special transaction that starts a new coin owned by the
  creator of the block ... provides a way to initially distribute coins into circulation, since
  there is no central authority to issue them" (§6); attacker must "redo the proof-of-work of the
  block and all blocks after it" (§4). Text extracted from the PDF with pdftotext (checked 2026-10-25).
- Bitcoin supply: "a 50% reduction every 210,000 blocks, or approximately four years"; supply "will
  not exceed slightly less than 21 million". Source: https://en.bitcoin.it/wiki/Controlled_supply
  (checked 2026-10-25).
- Ethereum PoS (https://ethereum.org/en/developers/docs/consensus-mechanisms/pos/, checked
  2026-10-25): "a user must deposit 32 ETH into the deposit contract"; "slots (12 seconds) and epochs
  (32 slots)"; "One validator is randomly selected to be a block proposer in every slot"; finality
  needs "at least two-thirds of the total staked ETH"; slashable: "proposing multiple blocks in a
  single slot (equivocating) and submitting contradictory attestations", penalties up to "100% of the
  validator's stake getting destroyed"; "An attacker would need 51% of the staked ETH"; one-third of
  stake can "prevent the network from reaching finality"; reverting a finalized block means "losing
  at least one-third of the total supply of staked ETH".
- The Merge: "The Merge was executed on September 15, 2022." Source:
  https://ethereum.org/en/roadmap/merge/ (checked 2026-10-25). The page's ~99.95% energy figure was
  deliberately left out (writing guide: leave out axes where the other side wins).
- Ethereum rewards: base_reward ∝ effective_balance / sqrt(sum(active_balance)); "The more
  validators, the greater the overall issuance"; rewards for attestations, proposals, sync
  committees; "All rewards and penalties are applied once per epoch." Source:
  https://ethereum.org/en/developers/docs/consensus-mechanisms/pos/rewards-and-penalties/ (checked 2026-10-25).
- Peercoin: initial release August 2012; first cryptocurrency to implement proof of stake. Source:
  https://en.wikipedia.org/wiki/Peercoin (checked 2026-10-25; whitepaper by Sunny King and Scott
  Nadal dated 2012-08-19).
- RandomX: "a proof-of-work (PoW) algorithm that is optimized for general-purpose CPUs"; "activated
  on the Monero network on the 30th November 2019". Source: https://github.com/tevador/RandomX
  (checked 2026-10-25).

## Left out on purpose

Energy-use comparisons and numbers, PoS attack-theory jargon (nothing-at-stake, long-range attacks),
staking yields, Ethereum validator counts or total stake (live numbers), Zcash (its consensus plans
are in flux), Faraday PoW parameters (unannounced), current block reward and network hashrate
(volatile), fees.

## Translation terms

工作量证明 / 工作量證明 (PoW), 权益证明 / 權益證明 (PoS), 验证者 / 驗證者, 质押 / 質押,
认证 / 認證 (attestation), 罚没 / 罰沒 (slashing), 时隙 / 時槽 (slot), 周期 / 週期 (epoch),
哈希 / 雜湊, 内核 / 運算核心程式, 守护程序 / 守護程式, 合并 / 合併 (the Merge).
