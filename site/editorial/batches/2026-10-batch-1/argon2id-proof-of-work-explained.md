# argon2id-proof-of-work-explained: research notes

Written 2026-10-25 for batch 1. Draft only (`draft: true`, translations `translation: draft`,
sourceHash 966b003a7322).

## Intent

A reader who searched "Argon2id proof of work" (or wondered why Blocknet mining needs 2 GB per
thread) wants to understand what Argon2id computes, how Blocknet sets it up as PoW, and why
memory decides hashrate. Nearest owner: `/blog/how-to-mine-blocknet/` (a setup guide that
states the 2 GB rule and shows a hardware table without explaining it). Unique here: the
RFC 9106 mechanism, the full consensus parameter table, the difficulty/target arithmetic, the
per-hash memory-traffic arithmetic, and how each seine kernel (vector, prefetch, streaming,
NEON+SHA3) attacks the memory-bound loop.

## Keyword-map row (proposed)

| argon2id proof of work | `/blog/argon2id-proof-of-work-explained/` | Explain how Blocknet's Argon2id PoW works, why it is memory-hard and why RAM and bandwidth set hashrate | argon2id mining, argon2id parameters, memory-hard proof of work, blocknet 2 GB per thread, designed to resist ASICs, Argon2id 工作量证明 |

Boundary: the hardware post owns buying advice and per-chip results; this post links to the
mining guide's table instead of repeating it.

## Facts used from the fact sheet

PoW parameters (2 GiB, t=1, p=1, 32 bytes, v0x13), nonce as password and header-without-nonce
as salt, target = (2^256−1)/difficulty and difficulty ≈ expected hashes per block, network
hashrate ≈ difficulty/300, LWMA 60-block window, "Memory-hard PoW to resist ASICs and ensure
fair mining" (`pow.rs:1-4`), per-connection vardiff, 2 GB per thread, 5% memory reserve,
16 GB ≈ six to seven threads (wording from the how-to-mine FAQ), huge pages +4–6% (2 MiB),
1,024 two-MiB pages per thread, kernel list, two-confirmed-gains switching and caching,
NVIDIA rates add, NVRTC compile at startup, first-launch GPU autotune cached, kernel gains
(Graviton4 +56%, Graviton3 +45%, EPYC 9R45 +30%).

## Facts added (not in the fact sheet), with sources

- RFC 9106 abstract: "This document describes the Argon2 memory-hard function for password
  hashing and proof-of-work applications." Published 2021 (copyright line; September 2021),
  Informational, a product of the IRTF Crypto Forum Research Group (CFRG).
  Source: https://www.rfc-editor.org/rfc/rfc9106 (checked 2026-10-25)
- RFC 9106 §1: Argon2 has "one primary variant, Argon2id, and two supplementary variants";
  Argon2d's data-dependent access "makes it suitable for cryptocurrencies and proof-of-work
  applications"; Argon2i is "preferred for password hashing"; "Argon2id works as Argon2i for
  the first half of the first pass over the memory and as Argon2d for the rest."
  Source: RFC 9106 §1 (checked 2026-10-25)
- RFC 9106: "Argon2id MUST be supported by any implementation of this document."
  Source: RFC 9106 (checked 2026-10-25)
- RFC 9106 §3: memory is 1,024-byte blocks; G takes two 1024-byte inputs and gives a
  1024-byte output; G "is built upon the BLAKE2b-based transformation P"; each block is
  B[i][j] = G(B[i][j-1], B[l][z]). Source: RFC 9106 §3 (checked 2026-10-25)
- RFC 9106 §7: time-space trade-offs store fewer blocks "at the cost of more calls to the
  internal compression function"; the recommended Argon2id setting "maximizes adversarial
  costs on dedicated brute-force hardware." Source: RFC 9106 §7 (checked 2026-10-25).
  Deliberately not quoted: the RFC's trade-off attack factors (1.33, ~2.1).
- RFC 9106 §7.4 (editor, 2026-10-25): "The Argon2id variant with t=1 and 2 GiB memory is the FIRST
  RECOMMENDED option ... This setting is secure against side-channel attacks and maximizes
  adversarial costs on dedicated brute-force hardware." (§4 lists it with p=4 lanes; Blocknet
  uses p=1, so the post says Blocknet shares the pass count and memory size, not the whole setting.)
- Target check is `hash <= target` (`blocknet-core@pool:crypto-rs/src/pow.rs:143-160`), so the FAQ
  says "at or below".
- Data-dependent reference index comes from the first 64-bit word of the previous block
  (`rand = memory_blocks[prev_index].as_ref()[0]`), and slices 0-1 of 4 are data-independent
  in the one-pass, one-lane kernel. Source: `seine@origin/master (d03a1b0):pow-kernel/src/fixed_argon.rs`
  `fill_blocks_neon_sha3` and `fill_streaming_ring` (checked 2026-10-25)
- Streaming kernel: keeps a 64-block cached ring and writes each block to the arena with
  `_mm256_stream_si256` (non-temporal stores), fenced every 64 blocks; autotuning guide says it
  "keeps recent blocks cached and streams outputs into the normal 2 GiB arena", compared on
  validated Zen 5 EPYC (family 26, model 2). Source: `fixed_argon.rs` `fill_streaming_ring`;
  `seine@origin/master:docs/guides/autotuning.md:39-41` (checked 2026-10-25)
- Mid-compress prefetch: the next reference block is prefetched inside the compression
  "after column round 0 writes dst[0] to its final value. Remaining column rounds overlap with
  the DRAM fetch." Data-independent half prefetches 3 blocks ahead (`DI_PREFETCH_DISTANCE`).
  Source: `fixed_argon.rs` (checked 2026-10-25)
- NEON+SHA3: `neon-sha3` "combines XOR/rotate instructions and 64-byte prefetch coverage";
  the code emits XAR directly. Source: `seine@origin/master:docs/guides/autotuning.md:29-31`;
  `fixed_argon.rs` `fill_blocks_neon_sha3` comment (checked 2026-10-25)
- AVX-512 256-bit kernel "uses paired 256-bit rows/columns and native rotate instructions".
  Source: `seine@origin/master:pow-kernel/src/fixed_argon/avx512_256.rs:1-5` (checked 2026-10-25)
- Ice Lake Xeon 8375C: AVX-512 over AVX2 +21–29% (range across one to four threads, regular
  and huge pages); Graviton3 12.52 → 18.17 H/s. Source: `seine@origin/master:docs/PERFORMANCE.md:70`, `:102`, `:114` (checked 2026-10-25)
- PERFORMANCE.md: hashrate "depends as much on memory bandwidth and latency as on core count."
  Source: `seine@origin/master:docs/PERFORMANCE.md:3-4` (checked 2026-10-25)
- Huge pages "cuts TLB misses". Source: `seine@origin/master:docs/guides/linux-hugepages.md:3-4`
- Parallelism comment in the daemon: "Parallelism: 1 (single-threaded for fairness)".
  Source: `blocknet-core@pool:crypto-rs/src/pow.rs:14` (checked 2026-10-25)

## Derived (arithmetic shown)

- 2,097,152 KiB / 1 KiB = 2,097,152 blocks per hash.
- Per hash: 2,097,152 blocks × 1 KiB written ≈ 2 GiB; each block reads one 1 KiB reference
  block ≈ 2 GiB read (the previous block is just written and usually cached). So ≈ 4 GiB of
  memory traffic per hash; 10 H/s × 4 GiB ≈ 40 GiB/s.
- Pages per arena: 2 GiB / 4 KiB = 524,288; 2 GiB / 2 MiB = 1,024 (matches the guide).

## Left out on purpose

Faraday (owner is writing Argon2id posts for now), hardware buying advice and per-chip tables
(hardware post), Ryzen 9950X3D streaming gain (streaming auto-selection is only validated on
Zen 5 EPYC), EPYC 9R14 streaming gain (Zen 4 auto-selection unstated), Graviton2 +4%, RFC
trade-off attack factors, GPU H/s.
