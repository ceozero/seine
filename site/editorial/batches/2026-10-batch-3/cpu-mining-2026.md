# cpu-mining-2026: research notes

## Intent

A reader searching "CPU mining 2026" or "what to mine with a CPU" wants to know whether CPU mining
still works, why some coins suit processors, what to look for in a CPU-mineable coin and what makes a
CPU fast; nearest owners are `/blog/blocknet-mining-hardware-hashrate/` (which machine to buy for
Blocknet) and `/blog/argon2id-proof-of-work-explained/` (Argon2id mechanics). This post adds the
generic landscape (Bitcoin ASICs, Ethereum's Merge, CPU-oriented algorithms), a neutral checklist for
choosing a coin, and routes to Blocknet, seine and bntpool.com.

Suggested keyword-map row:

| cpu mining 2026 | `/blog/cpu-mining-2026/` | Explain CPU mining in 2026: why memory-hard coins favor ordinary computers, what to check in a CPU coin, what makes a CPU fast, and how to start with seine | what to mine with a cpu, cpu mineable coins, memory-hard coin cpu, is cpu mining dead, CPU 挖矿 / CPU 挖礦, 用 CPU 挖什么币 |

Boundary: this post keeps one best-per-generation table and a RAM rule of thumb and links to the
hardware post for buying advice and full sizing; Argon2id internals stay in the Argon2id explainer;
old-PC/laptop safety (cooling, power) belongs to `mine-crypto-on-old-pc-or-laptop`; PoW vs PoS
belongs to `proof-of-work-vs-proof-of-stake`.

## Facts from the fact sheet

Argon2id 2 GiB / 1 pass / parallelism 1 (§1); code comment "Memory-hard PoW to resist ASICs and
ensure fair mining" / "Uses 2GB memory, making specialized hardware impractical" (§1, re-checked
below); 5-minute blocks, 288/day (§1, §2); expected blocks/day formula (§2); genesis has no
transactions, coinbase is one output equal to the reward, no premine/treasury/dev fund (§1);
genesis 2026-02-15 EST = "launched February 2026" (§1, §7); PPLNS 6 h, 0.1 BNT minimum payout (§3);
default pool URL (§3); seine BSD-3 (§4); 2 GB per thread, 5% reserve, zero config, auto-tuning,
NVIDIA alongside CPU on Windows/Linux, update check every 12 h (§4); CPU kernels (§4); best per
generation with Zen 5 at 49.4 H/s / 32 threads (§5 update); kernel gains Graviton4 +56%
(13.80 → 21.50) and EPYC 9R45 +30% (34.47 → 44.74) (§5); huge pages +4-6% / +2% (§4); hash
writes ~2 GiB and reads ~2 GiB, second half data-dependent (§9); Faraday "a lighter proof of work"
~2027-02-16 (§0).

Derived: 49.4 × 2 GiB ≈ 99 GiB/s written; 32 GB → 16 arenas on paper, ~14 threads after the 5%
reserve and OS headroom (same arithmetic as the published hardware post).

## New facts (external, general)

- Bitcoin whitepaper, section 4: "Proof-of-work is essentially one-CPU-one-vote."
  Source: https://bitcoin.org/bitcoin.pdf (extracted with pdftotext, checked 2026-10-25).
- Bitcoin mining moved from CPUs to GPUs, then FPGAs and ASICs; "Bitcoin-specific ASICs are now the
  primary method of mining bitcoin." Source: https://en.wikipedia.org/wiki/Bitcoin_protocol
  (checked 2026-10-25). Bitcoin's block hash is SHA-256 (twice): https://en.wikipedia.org/wiki/Bitcoin.
- Ethereum's Merge happened September 15, 2022; it "completed Ethereum's transition to proof-of-stake
  consensus, officially deprecating proof-of-work" and "Mining is no longer the means of producing
  valid blocks." Source: https://ethereum.org/roadmap/merge/ (checked 2026-10-25).
- RandomX: "RandomX is a proof-of-work (PoW) algorithm that is optimized for general-purpose CPUs."
  "RandomX was successfully activated on the Monero network on the 30th November 2019."
  Source: https://github.com/tevador/RandomX README (checked 2026-10-25). Memory figures (2080 MiB
  shared in fast mode, 256 MiB light mode) were read but deliberately not used.

## Code checks

- `git -C blocknet-core show pool:crypto-rs/src/pow.rs` lines 1-4 (pool = c646196): "Memory-hard
  PoW to resist ASICs and ensure fair mining. Uses 2GB memory, making specialized hardware
  impractical."
- Offline benchmark command: `seine@master:docs/PERFORMANCE.md:121-125` (worktree HEAD 36f40e6).
- Zen 5 49.4 H/s is now in `seine@master:README.md` chart alt text (PR #59 has landed on master).

## Left out on purpose

Fees (not needed to act), RandomX vs Argon2id memory-per-thread comparison, desktop Ryzen and GPU
H/s figures (not best-per-generation / removed from marketing), coin rankings and profit claims.
`related: []` per the brief, so the strict check's "list 2-4 related posts" warning is expected.
