# blocknet-mining-hardware-hashrate: research notes

Writer notes for `/blog/blocknet-mining-hardware-hashrate/` (draft, 2026-10-25).

## Intent

A reader choosing a machine for Blocknet mining (or sizing up the one they have) wants to know
which hardware mines fastest, how many threads their RAM allows and what hashrate to expect.
The nearest owner is `/blog/how-to-mine-blocknet/`, which shows one best-per-generation table
and links out. This post adds the buying view: the per-generation table with the RAM each
result used, why memory bandwidth and 2 GiB per thread set the rate (with measured scaling on
the Zen 5 host), RAM-to-thread arithmetic for 16/32/64/128 GB, CPU plus NVIDIA mining, and what
seine tunes so the reader configures nothing.

## Proposed keyword-map row

| Primary keyword cluster | URL | Search job | Supporting phrases |
|---|---|---|---|
| best hardware for blocknet mining | `/blog/blocknet-mining-hardware-hashrate/` | Pick or size up a machine for Blocknet mining: which hardware mines fastest, threads per GB of RAM, expected H/s, CPU+GPU | blocknet hashrate, blocknet mining RAM per thread, best CPU for Blocknet, Argon2id mining hardware, blocknet GPU mining, 挖 Blocknet 用什么硬件 / 挖 Blocknet 用什麼硬體 |

Boundary: Mac depth (thread counts by Mac RAM, balanced vs max settings) stays with
`mine-blocknet-on-mac`; Argon2id internals stay with `argon2id-proof-of-work-explained`. This
post uses Argon2id only to explain why bandwidth and RAM matter.

Overlap (`npm run overlap`): 3.8% of 8-word phrases shared with how-to-mine-blocknet, 1.3% with
mine-blocknet-on-mac, 0.8% with what-is-blocknet.

## Facts used from the fact sheet

- Best-per-generation table, with the 2026-10-25 update note: Zen 5 49.4 H/s at 32 threads
  replaces 44.7 / 24 (fact sheet §5).
- 2 GiB Argon2id arena, iterations 1 (§1); 2 GB per thread (§2, §4); 5% memory reserve (§4).
- Cloud rows are AWS guests with explicit 2 MiB huge pages (§5).
- Kernel gains: EPYC 9R45 AVX2 → streaming +30% (34.47 → 44.74 at 24 threads); Graviton4
  NEON → SHA3 + prefetch +56% (13.80 → 21.50) (§5).
- NUMA/L3 placement +16.7% on EPYC 8434P at 24 threads (§4).
- Huge pages +4–6% (2 MiB) and a further +2% (1 GiB) (§4).
- NVIDIA: every detected GPU alongside the CPU, rates add, per-GPU autotune cached; Windows
  bundles NVRTC, Linux needs driver + NVRTC (§4). M4 Max CPU-only beat Metal (§4).
- Tuning never reconnects to the pool; update check at start and every 12 h (§4).
- Faraday ~2027-02-16 with "a lighter proof of work" (§0), attributed to blocknetcrypto.com.

## Facts added (not in the fact sheet), with sources

1. **Zen 5 32-thread host details and scaling.** AWS m8a.8xlarge, AMD EPYC 9R45 (family 26,
   model 2), 32 physical cores, no SMT, 1 NUMA node, four L3 groups of 32 MiB (8 cores each),
   123.45 GiB visible (AWS lists 128 GiB). Streaming kernel (`avx512-256-stream`), seine
   v0.2.22: 37.76 H/s @ 16 threads, 46.08 @ 24, 48.58 @ 30, 49.39 @ 32 (mean of 4 runs at 32,
   stdev 0.008). AVX2 at 32 threads: 37.72 H/s.
   Source: `seine@origin/codex/zen5-turin-result:experiments/readme-hardware-20261025/summary.json`
   (host `zen5-turin`, PR #59, commit 630b2c7), read 2026-10-25. Post uses 37.8 @ 16 and 49.4
   @ 32, the 32 MiB L3 group and the 128 GiB machine size.
2. **Derived:** 2 GiB arena ÷ 32 MiB L3 group = 64×. 49.4 H/s × 2 GiB = 98.8 GiB of arena
   written per second (Argon2 with t=1 computes, and writes, every block of the 2 GiB memory
   exactly once; each block is computed from the previous block and an earlier reference
   block, per RFC 9106 §3.2, https://www.rfc-editor.org/rfc/rfc9106).
3. **Automatic thread count formula.** `auto_cpu_threads` = min(logical CPUs,
   (available RAM − GPU/Metal reservation − 5% of effective total) ÷ 2 GiB).
   Source: `seine@origin/master:src/config.rs:2815-2845` (read 2026-10-25). The GPU reservation
   applies only to Metal (`src/config.rs:1091`).
4. **Derived thread table** (RAM − 5% − ~2–3 GB OS, ÷ 2 GiB, rounded down, labeled "roughly"):
   16 GB → 6, 32 GB → 14, 64 GB → 29, 128 GB → 59 (editor: 128 × 0.95 − 2 GB = 119.6 GiB ÷ 2 = 59.8, so 59, not 60). The 16 GB value matches how-to-mine-blocknet's
   "six to seven".
5. **Offline benchmark command:** `./seine --bench --bench-kind backend --backend cpu
   --bench-secs 20 --bench-rounds 3`, reporting completed hashes per second.
   Source: `seine@origin/master:docs/PERFORMANCE.md` ("Benchmark your own machine"), read
   2026-10-25.
6. **Memory-hard wording:** "hashrate depends as much on memory bandwidth and latency as on
   core count". Source: `seine@origin/master:docs/PERFORMANCE.md:3-5`.

## Deliberately left out

- Desktop Ryzen 9 9950X3D (10.31 H/s), older EPYC/Xeon/Graviton rows, and any GPU hashrate
  (none published; the RTX 5090 figure was removed by the owner).
- Memory-channel counts and vendor bandwidth specs (AMD and Apple spec pages didn't load or
  no longer list the M4 Max; not needed for the argument).
- `--nvidia-devices`: the guide shows it with `--backend nvidia`; behavior in the default
  CPU+GPU mode isn't documented, so it's not in the post.
- Zen 4 streaming auto-selection (unverified, fact sheet §7).

## Notes for the integrator

- `docs/PERFORMANCE.md` on seine master still shows Zen 5 at 44.74 / 24 until PR #59 merges;
  the post's link to it will show the older number until then.
- `scripts/check-content.mjs` drops the first positional argument when `--hash` is absent
  (`i !== hashIdx + 1` with `hashIdx = -1` excludes index 0), so `npm run check -- <slug>
  --strict` checks every post. `npm run check -- --strict <slug>` checks just the one.
