# EPYC 9R14 fence improvement

**45.30 H/s at 32 threads**, up **2.55%** from the paired 44.18 H/s control.
Three fresh alternating 30-second pairs confirmed the improvement after a
separate two-pair screening stage. The paired 95% bootstrap interval is
+2.53% to +2.58% on this host. The confirmed kernel change ships in v0.2.32.

| Pair | Order | Previous policy H/s | Improved policy H/s |
|---|---|---:|---:|
| 1 | Previous, improved | 44.1813 | 45.2973 |
| 2 | Improved, previous | 44.1606 | 45.2791 |
| 3 | Previous, improved | 44.1879 | 45.3276 |

Measured October 26, 2026, during the 8:16–8:25 AM EDT rental on native Linux,
AWS `m7a.8xlarge`: EPYC 9R14, 32 physical cores, 128 GiB and one visible NUMA
node. Each run used 32 full 2 GiB arenas backed by transparent huge pages
(64 GiB total), checked in every report. Placement used the OS scheduler.
No power limit was applied.

Both sides use ring eight and prefetch depth two. The previous policy fences
streaming writes periodically; the new policy fences before an arena read
that needs pending writes and before finalization. The automatic hardware
selection remains scoped to the existing validated Genoa configuration.
Windows retains its previous policy pending native performance measurement.

The frozen research driver counts every completed hash over the shared hashing
interval, including completion of in-flight work. Allocation, five seconds of
warmup and teardown are excluded. Autotuning is disabled. This measures kernel
throughput; cold-start, pool throughput, fees and energy are separate results.
The earlier 43.89 H/s measurement used another driver and host session; the
2.55% gain is calculated against the fresh 44.18 H/s paired control here.

All **11,870 timed hashes** across screening and confirmation matched independently
computed libargon2 references. The supplied reference subset contains 1,393
unique inputs reused across runs. Twelve native full-size RustCrypto checks
also passed before timing, including dirty reuse and guard checks. Source-level
algorithm equivalence to the integrated loop is recorded in
[integration-equivalence.json](integration-equivalence.json); this does not
claim identical machine code or a separate full-miner comparison.

## Reproduce

The [frozen source archive](source.tar.gz) includes the exact research revision's
build inputs, lockfile and both drivers. It omits unrelated documentation,
website and agent configuration. The original revisions and binary checksums
are in [summary.json](summary.json). The baseline driver and fixed kernel
source are unchanged between the original baseline and this archive's revision.
Rebuilding does not imply byte-identical binaries across build environments.

On an AVX-512 Linux host with at least 80 GiB available RAM, Rust 1.93.0,
a C compiler and THP enabled:

```sh
mkdir /tmp/seine-fence-source
tar -xzf source.tar.gz -C /tmp/seine-fence-source
cd /tmp/seine-fence-source
cargo +1.93.0 build --locked --release -p blocknet-pow-kernel \
  --features cpu-research --example streaming_ring_grid \
  --example streaming_fence_experiment
./target/release/examples/streaming_ring_grid verify 8 2
./target/release/examples/streaming_fence_experiment verify 8 2
```

From this evidence directory, with absolute paths for both binaries:

```sh
python3 run_ab.py \
  --baseline /tmp/seine-fence-source/target/release/examples/streaming_ring_grid \
  --candidate /tmp/seine-fence-source/target/release/examples/streaming_fence_experiment \
  --pairs 3 --seconds 30 --output-dir /tmp/seine-fence-confirm
```

The campaign used this same wrapper through `scripts/benchctl.py campaign`:
correctness, two 20-second screening pairs, then three fresh 30-second
confirmation pairs, with three seconds between runs. The confirmation gate
required a positive 95% lower bound. The interval uses 20,000 paired percentile
bootstrap samples of mean log ratios, seed 24094. Screening remains in
[screen/](screen/), separate from [confirmation](confirm/).

Run `python3 verify.py` here to audit report checksums, memory backing, counters
and every captured hash against the independently generated reference subset.
To regenerate that subset independently, use libargon2 Argon2id v19 with
memory 2,097,152 KiB, one iteration, one lane, 32-byte output, the eight-byte
little-endian nonce as password, and the 92-byte header as salt. Reference keys
encode `header_hex:decimal_nonce`. Regeneration requires 2 GiB per concurrent
hash; the default audit only reads existing evidence.

The manifest covers every published file except itself. Raw run JSON and TSV
are unchanged; private operational credentials and rental records are excluded.
