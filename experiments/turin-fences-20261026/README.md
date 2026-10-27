# EPYC 9R45 fence improvement

**49.95 H/s at 32 threads**, up **1.01%** from the paired 49.45 H/s control.
Three fresh alternating 30-second pairs confirmed the improvement after a
separate two-pair screen. The paired 95% bootstrap interval is +0.39% to +1.64%
on this host. Screening and confirmation remain separate in the raw reports.

Measured October 26, 2026, during the 10:55–11:11 AM EDT rental on native Linux,
AWS `m8a.8xlarge`: AMD EPYC 9R45, 32 physical cores and 128 GiB RAM. Each run
used 32 full 2 GiB arenas backed by transparent huge pages, checked in every
report. Placement used the OS scheduler; no power limit was applied.

Both sides retain 64 cached blocks and prefetch depth three. The candidate
fences streaming writes before an arena read needs pending writes and before
finalization. The baseline fences periodically. The integrated path is
`avx512-256-stream-r64d3`; its automatic selection is scoped to this native
Linux host configuration, with full THP backing required for the startup hint.
Existing confirmed tuning remains the starting point while the new path is
compared productively.

This fixed-kernel driver counts completed hashes over the shared hashing
interval, including completion of in-flight work. Allocation, five seconds of
warmup and teardown are excluded. Autotuning, pool throughput, fees and energy
are separate measurements. The gain uses the fresh paired control, not the
previous 49.39 H/s result from another host session and driver.

All **13,103 timed hashes** matched independently computed libargon2 references.
The supplied subset contains 1,536 unique inputs. Twelve native full-size
RustCrypto checks also passed, including dirty reuse and guards. The integrated
loop matches the tested algorithm after resolving constant branches, as recorded
in [integration-equivalence.json](integration-equivalence.json). This is source
algorithm equivalence, not a claim of identical machine code or a separate
full-miner comparison.

## Reproduce

The separate frozen source archives preserve the baseline and candidate
revisions, dependencies and lockfiles. They omit unrelated website and agent
configuration. Binary checksums and exact revisions are in
[summary.json](summary.json). Rebuilding need not produce identical binaries.

On an AVX-512 Linux host with at least 80 GiB available RAM, Rust 1.93.0,
a C compiler and THP enabled:

```sh
mkdir /tmp/turin-baseline /tmp/turin-candidate
tar -xzf baseline-source.tar.gz -C /tmp/turin-baseline
tar -xzf candidate-source.tar.gz -C /tmp/turin-candidate
(cd /tmp/turin-baseline && cargo +1.93.0 build --locked --release \
  -p blocknet-pow-kernel --features cpu-research --example streaming_shipping_compare)
(cd /tmp/turin-candidate && cargo +1.93.0 build --locked --release \
  -p blocknet-pow-kernel --features cpu-research --example streaming_fence_experiment)
/tmp/turin-baseline/target/release/examples/streaming_shipping_compare verify 64 3
/tmp/turin-candidate/target/release/examples/streaming_fence_experiment verify 64 3
python3 run_ab.py \
  --baseline /tmp/turin-baseline/target/release/examples/streaming_shipping_compare \
  --candidate /tmp/turin-candidate/target/release/examples/streaming_fence_experiment \
  --candidate-ring 64 --pairs 3 --seconds 30 --output-dir /tmp/turin-confirm
```

The campaign used this wrapper through `scripts/benchctl.py campaign`, with
three seconds between runs. Confirmation used 20,000 paired percentile bootstrap
samples of mean log ratios, seed 24094. Its lower bound had to exceed zero.

Run `python3 verify.py` here to audit every report checksum, memory backing,
counter and captured hash against the supplied independent references.
To regenerate references, use libargon2 Argon2id v19: memory 2,097,152 KiB,
one iteration, one lane, 32-byte output, eight-byte little-endian nonce as
password and the 92-byte header as salt. Keys encode `header_hex:decimal_nonce`.
Regeneration needs 2 GiB per concurrent hash; the default audit only reads files.
The manifest covers every published file except itself.
