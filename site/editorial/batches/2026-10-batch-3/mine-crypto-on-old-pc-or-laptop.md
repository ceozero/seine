# mine-crypto-on-old-pc-or-laptop: research notes

Post: `src/content/blog/mine-crypto-on-old-pc-or-laptop/` ("How to mine crypto on an old PC or
laptop"), drafted 2026-10-25. English `sourceHash` 663f7b93783f; zh-Hans and zh-Hant are
`translation: draft` (no independent review yet).

## Intent

Reader's job: someone with a spare old desktop or laptop wants to know if it can mine at all,
what decides how well it mines (RAM, memory bandwidth, cooling, power), how many threads its
memory allows, how to keep a laptop cool, and how to start safely. Nearest owners:
`blocknet-mining-hardware-hashrate` (which machine to buy, best-per-generation results, sizing
for 16-128 GB) and `how-to-mine-blocknet` (zero-to-shares setup). This post adds the generic
"old PC / laptop" framing (memory-hard vs ASIC coins), small-RAM arithmetic (4-12 GB rows),
old-instruction-set coverage (portable kernel, AVX2 since Haswell/Excavator), laptop cooling
habits, the `--cpu-profile efficiency` option, and electricity arithmetic.

## Keyword-map row (proposed)

| Primary keyword cluster | URL | Search job | Supporting phrases |
|---|---|---|---|
| mine crypto on old pc or laptop | `/blog/mine-crypto-on-old-pc-or-laptop/` | Decide whether a spare old desktop or laptop can mine, size threads to its RAM, keep it cool, and start safely with seine on bntpool.com | mining on an old laptop, mine crypto on laptop, old computer crypto mining, laptop mining 8GB RAM, seine efficiency profile, 用旧电脑挖矿 / 用舊電腦挖礦, 笔记本电脑挖矿 / 筆記型電腦挖礦 |

Boundaries: the hardware post owns buying advice and full per-chip results (this post links
to it and shows no hashrate table); `how-to-mine-blocknet` owns the full setup walkthrough
(this post has a five-step summary and links there); `cpu-mining-2026` (batch 3) owns "what to
mine with a CPU" (this post has one paragraph on memory-hard vs ASIC coins). Overlap report:
3.7% of 8-word phrases shared with blocknet-mining-hardware-hashrate, 2.3% with
how-to-mine-blocknet, 1.9% with cpu-mining-2026.

## Facts used from the fact sheet

2 GiB per thread, Argon2id, "designed to resist ASICs" (§1, §2, §4, §6); 5% memory reserve and
threads parking under memory pressure (§4); auto threads = min(cores, (free RAM − 5%) ÷ 2 GiB)
(§9 macOS bullet); release archives and glibc 2.39 (§4); x86 scalar/AVX2/AVX-512/streaming and
Arm NEON/SHA3 kernels, switching after two confirmed gains (§4); NVIDIA mined alongside the CPU
(§4); default pool `stratum+tcp://bntpool.com:3333`, PPLNS 6 h, minimum payout 0.1 BNT (§3);
288 blocks/day and expected output formula (§2); reward steps down every 8,640 blocks (§2);
update check at startup and every 12 h (§4); Faraday lighter PoW ~2027-02-16 (§0). Pool and
dev fees deliberately not mentioned (brief: don't volunteer fees); output is called "gross".

## Facts added (verified 2026-10-25)

Refs: seine = this worktree at 36f40e6 (seine master, same as `origin/master`);
`blocknet-pool@master` = 9bf4eb6.

- Automatic thread sizing: `min(logical CPUs, (available RAM − reserve% of effective total) ÷
  2 GiB)`, at least 1. `seine:src/config.rs:2815-2845`.
- `--cpu-profile balanced|throughput|efficiency`, default balanced.
  `seine:docs/MINER_FLAGS.md:37`. Efficiency preset starts at half the automatic thread cap
  (`src/config.rs:278-285`). Autotune keeps the fewest threads reaching 99% (balanced) or 75%
  (efficiency) of the measured peak: `src/miner/mod.rs:73-74`, `:1493-1518`;
  `docs/guides/autotuning.md:20-23`.
- `--threads N` sets a fixed count and disables thread autotuning; `+`/`-` (and `=`) in the
  dashboard add or remove one thread. `seine:docs/guides/configuration.md:41-42`, `:55-64`.
- Free RAM checked once per second; threads finish their current hash, park, and come back
  when headroom returns. `seine:docs/guides/autotuning.md:61-82`.
- The scalar (portable) kernel is always supported on x86 and is the fallback in the
  preference order AVX-512 > AVX2 > NEON > scalar. `seine:pow-kernel/src/cpu_kernel.rs:43`,
  `:67-70`. AVX2/AVX-512 are compared while mining only on CPUs that have both
  (`docs/guides/autotuning.md:28-30`, `:56-57`).
- AVX2 kernel measured on Haswell (Xeon E5-2666 v3, 9.72 H/s at 11 threads) and Broadwell
  (Xeon E5-2686 v4, paired-column AVX2 +11-12%). `seine:docs/PERFORMANCE.md:38`, `:100`. The
  post names the generations only, no number.
- If CUDA initialization fails, NVIDIA backends are quarantined and CPU mining continues.
  `seine:docs/guides/nvidia.md:17-18`.
- bntpool.com dashboard shows "Network Hashrate".
  `blocknet-pool@master:frontend/src/pages/DashboardPage.tsx:171-172`.
- `SHA256SUMS.txt` published with each release: already stated in how-to-mine-blocknet and
  fact sheet §9 (macOS archive contents).

General external facts:

- AVX2 introduced with Intel Haswell (2013) and AMD Excavator (2015):
  https://en.wikipedia.org/wiki/Advanced_Vector_Extensions#Advanced_Vector_Extensions_2
- Bitcoin mining is dominated by SHA-256 ASICs:
  https://en.wikipedia.org/wiki/Bitcoin#Mining
- RandomX "is a proof-of-work (PoW) algorithm that is optimized for general-purpose CPUs":
  https://github.com/tevador/RandomX
- Dual-channel memory raises peak bandwidth over single-channel:
  https://en.wikipedia.org/wiki/Multi-channel_memory_architecture
- Processors reduce clock speed when hot (thermal throttling):
  https://en.wikipedia.org/wiki/Dynamic_frequency_scaling

Arithmetic in the post: the RAM table uses RAM ÷ 2 GiB "on paper", then subtracts the 5% reserve
and an assumed 2-3 GB for the OS (same assumption and same 16/32 GB results as the hardware
post). 65 W × 24 h = 1,560 Wh = 1.56 kWh is an illustrative example, not a measurement.

## Notes for the integrator

- `related: []` per the brief, so strict check shows only "list 2-4 related posts".
  Suggested related: `blocknet-mining-hardware-hashrate`, `how-to-mine-blocknet`,
  `mine-blocknet-on-mac`, `cpu-mining-2026`.
- Cross-links to add: from `blocknet-mining-hardware-hashrate` (RAM table, "laptop or older
  PC" line) and `how-to-mine-blocknet` ("What do you need" RAM bullet) to this post; between
  this post and `cpu-mining-2026` (once published) and `how-crypto-mining-works`.
