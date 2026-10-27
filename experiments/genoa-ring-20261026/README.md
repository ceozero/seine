# EPYC 9R14 streaming-ring confirmation

**43.89 H/s at 32 threads**, up **15.43%** from the paired 38.02 H/s control.
Three fresh alternating 60-second pairs confirmed the improvement after a
separate two-pair screening stage. The paired 95% bootstrap interval is
+14.90% to +16.03% on this host.

| Pair | Order | Previous kernel H/s | Improved kernel H/s |
|---|---|---:|---:|
| 1 | Previous, improved | 38.1039 | 43.9563 |
| 2 | Improved, previous | 38.1246 | 43.8039 |
| 3 | Previous, improved | 37.8370 | 43.9015 |

Measured October 26, 2026, 4:41–4:49 AM EDT on native Ubuntu Linux in an AWS
`m7a.8xlarge`: EPYC 9R14, 32 physical cores, 128 GiB, one visible NUMA node.
Every run used 32 full 2 GiB arenas backed by transparent huge pages
(64 GiB total), verified in each report. `auto` page mode fell back from
unavailable explicit HugeTLB pages to THP. No power limit was applied.

The fixed binary compares `avx512-256-stream` (ring 64, depth 3) with
`avx512-256-stream-r8d2` (ring 8, depth 2). Both kernels, the CPU backend and
benchmark implementation match the source shipped in v0.2.27. The frozen
development revision and binary SHA-256 are recorded in [summary.json](summary.json).

Schema-15 kernel H/s counts completed hashes over actual hashing time,
including completion of in-flight work. Allocation, the excluded warm hash
per worker and teardown are outside that denominator. Autotuning is disabled.
This measures sustained kernel throughput; cold-start, pool fee and energy
measurements are separate.

All supported kernels passed full-size parity against independent RustCrypto
before timing; see [correctness.log](correctness.log). This fixed-kernel
benchmark records counters rather than every timed output. Separate miner
captures validated the integrated path against independent libargon2.

The repository's `benchctl.py campaign` ran correctness, two 20-second
screening pairs, then three fresh 60-second confirmation pairs, with a
3-second gap between invocations. The declared confirmation gate required a
95% lower bound above +1%; it passed. The interval uses 20,000 paired
percentile bootstrap samples of mean log ratios, seed 24094. The screening
measurements remain in [screen/](screen/), separate from [confirmation](confirm/).

Per-run JSON, the paired comparison, [summary.json](summary.json) and
[manifest.json](manifest.json) preserve the measurements. Only the ephemeral
VM hostname is removed from published per-run reports; original and published
checksums are both recorded.

To reproduce the confirmation with a release build that contains both kernels:

```sh
bash scripts/bench_cpu_ab.sh \
  --baseline-dir . --candidate-dir . \
  --baseline-binary "$PWD/target/release/seine" \
  --candidate-binary "$PWD/target/release/seine" \
  --bench-kind kernel --threads 32 --page-mode auto \
  --pairs 3 --bench-secs 60 --bench-rounds 1 --bench-warmup-rounds 0 \
  --cooldown-secs 3 \
  --baseline-miner-arg --bench-cpu-kernel \
  --baseline-miner-arg avx512-256-stream \
  --candidate-miner-arg --bench-cpu-kernel \
  --candidate-miner-arg avx512-256-stream-r8d2 \
  --output-dir /tmp/seine-genoa-confirm
```

Check every report for 32 THP-backed workers before comparing with this result.
