# EPYC 9R45 prefetch depth six

Three fresh alternating 30-second pairs measured **49.63379 H/s**, versus
**49.53885 H/s** for the paired depth-four control: **+0.19166%**, with a
paired 95% bootstrap interval of **+0.12560% to +0.26755%**. All three
confirmation pairs favored depth six. This is a small, hardware-specific
kernel gain; the three-pair interval does not establish variation across hosts.

The preceding two-pair screen was inconclusive: **-0.41978%**, interval
**[-0.90873%, +0.07158%]**. The predeclared screen rule advanced unresolved
results whose upper bound remained positive to a separate fixed confirmation.
Both stages are included here; the screen was not rerun until it passed.

Measured October 26, 2026 during the 12:41:50–12:57:03 PM EDT rental on
native Linux AWS `m8a.8xlarge`: AMD EPYC 9R45, 32 physical cores and 128 GiB
RAM. Every report verifies 32 full 2 GiB transparent-huge-page arenas.
Placement uses the OS scheduler; no power limit was applied.

Both paths use a 64-block ring and demand fences. The candidate increases
data-independent prefetch lookahead from four blocks to six. The integrated
path is `avx512-256-stream-r64d6`, queued for the next combined release.
Automatic eligibility is limited to the measured native Linux host
configuration; startup additionally requires actual full THP backing and
32 workers. Compatible confirmed local winners remain the initial setting
while the new path is compared productively.

The driver counts completed hashes over the shared hashing interval, including
completion of in-flight work. Allocation, five seconds of warmup and teardown
are excluded. Startup, whole-miner throughput, fees and energy are separate.
Absolute rates from earlier rentals must not be used to infer a regression or
to add these gains together.

All **13,119 timed hashes** match independent libargon2 reference outputs.
The included subset contains 1,526 unique inputs. Twelve native full-size
RustCrypto checks passed, including dirty reuse and guards. The complete
integrated loop matches the tested algorithm after resolving constant branches;
see [integration-equivalence.json](integration-equivalence.json). This records
source algorithm equivalence, not identical machine code or a separate
whole-miner performance comparison.

## Reproduce

The frozen source archives retain exact revisions, dependencies and lockfiles.
They omit unrelated website and agent configuration. Exact revisions and
binary checksums are in [summary.json](summary.json). Rebuilding need not
produce identical binaries.

On an AVX-512 Linux host with at least 80 GiB available RAM, Rust 1.93.0,
a C compiler and THP enabled:

```sh
mkdir /tmp/depth6-baseline /tmp/depth6-candidate
tar -xzf baseline-source.tar.gz -C /tmp/depth6-baseline
tar -xzf candidate-source.tar.gz -C /tmp/depth6-candidate
(cd /tmp/depth6-baseline && cargo +1.93.0 build --locked --release \
  -p blocknet-pow-kernel --features cpu-research --example streaming_fence_experiment)
(cd /tmp/depth6-candidate && cargo +1.93.0 build --locked --release \
  -p blocknet-pow-kernel --features cpu-research --example streaming_fence_experiment)
/tmp/depth6-baseline/target/release/examples/streaming_fence_experiment verify 64 4
/tmp/depth6-candidate/target/release/examples/streaming_fence_experiment verify 64 6
python3 run_ab.py \
  --baseline /tmp/depth6-baseline/target/release/examples/streaming_fence_experiment \
  --candidate /tmp/depth6-candidate/target/release/examples/streaming_fence_experiment \
  --candidate-depth 6 --pairs 3 --seconds 30 --output-dir /tmp/depth6-confirm
```

The campaign used this wrapper through `scripts/benchctl.py campaign`, with
three seconds between runs. Confirmation used 20,000 paired percentile bootstrap
samples of mean log ratios, seed 24094; its lower bound had to exceed zero.

Run `python3 verify.py` here to audit report checksums, memory backing, counters
and every captured hash against the supplied independent reference subset.
To regenerate references, use libargon2 Argon2id v19: memory 2,097,152 KiB,
one iteration, one lane, 32-byte output, eight-byte little-endian nonce as
password and the 92-byte header as salt. Keys are `header_hex:decimal_nonce`.
Regeneration needs 2 GiB per concurrent hash; the default audit only reads files.
The manifest covers every published file except itself.
