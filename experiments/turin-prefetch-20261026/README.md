# EPYC 9R45 prefetch improvement

**50.47 H/s at 32 threads**, up **0.35%** from the paired 50.29 H/s control.
Three fresh alternating 30-second pairs confirmed the gain after a separate
two-pair screen. The paired 95% bootstrap interval is +0.22% to +0.43% on this
host; all three confirmation pairs favored the candidate.

Measured October 26, 2026 during the 11:56 AM–12:07 PM EDT rental, on native
Linux AWS `m8a.8xlarge`: AMD EPYC 9R45, 32 physical cores and 128 GiB RAM.
Every report verifies 32 full 2 GiB transparent-huge-page arenas. Placement
uses the OS scheduler; no power limit was applied.

Both paths use a 64-block ring and demand fences. The candidate increases
prefetch lookahead from three blocks to four during data-independent hashing.
The integrated path is `avx512-256-stream-r64d4`; it is queued for the next
combined release. Automatic selection is limited to the measured native Linux
host configuration, with full THP backing required for the startup hint.
Saved confirmed tuning remains the initial setting while the new path is
compared productively.

The fixed-kernel driver counts completed hashes over the shared hashing
interval, including completion of in-flight work. Allocation, five seconds
of warmup and teardown are excluded. This measures kernel throughput;
startup, whole-miner throughput, fees and energy are separate. The gain uses
the paired control here, not the 49.95 H/s result from a previous rental.

All **13,302 timed hashes** match independent libargon2 reference outputs.
The included subset contains 1,538 unique inputs. Twelve native full-size
RustCrypto checks passed, including dirty reuse and guard checks. The complete
integrated loop matches the tested algorithm after resolving constant branches;
see [integration-equivalence.json](integration-equivalence.json). This records
source algorithm equivalence, not identical machine code or a separate
whole-miner comparison.

## Reproduce

The frozen source archives retain exact revisions, dependencies and lockfiles.
They omit unrelated website and agent configuration. Exact revisions and
binary checksums are in [summary.json](summary.json). Rebuilding need not
produce identical binaries.

On an AVX-512 Linux host with at least 80 GiB available RAM, Rust 1.93.0,
a C compiler and THP enabled:

```sh
mkdir /tmp/prefetch-baseline /tmp/prefetch-candidate
tar -xzf baseline-source.tar.gz -C /tmp/prefetch-baseline
tar -xzf candidate-source.tar.gz -C /tmp/prefetch-candidate
(cd /tmp/prefetch-baseline && cargo +1.93.0 build --locked --release \
  -p blocknet-pow-kernel --features cpu-research --example streaming_fence_experiment)
(cd /tmp/prefetch-candidate && cargo +1.93.0 build --locked --release \
  -p blocknet-pow-kernel --features cpu-research --example streaming_fence_experiment)
/tmp/prefetch-baseline/target/release/examples/streaming_fence_experiment verify 64 3
/tmp/prefetch-candidate/target/release/examples/streaming_fence_experiment verify 64 4
python3 run_ab.py \
  --baseline /tmp/prefetch-baseline/target/release/examples/streaming_fence_experiment \
  --candidate /tmp/prefetch-candidate/target/release/examples/streaming_fence_experiment \
  --candidate-depth 4 --pairs 3 --seconds 30 --output-dir /tmp/prefetch-confirm
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
