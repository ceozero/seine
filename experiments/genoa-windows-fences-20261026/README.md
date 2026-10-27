# EPYC 9R14 Windows fence improvement

**33.70 H/s at 32 threads**, up **2.61%** from the paired 32.84 H/s control.
Three fresh alternating 30-second pairs confirmed the improvement after two
20-second screening pairs. The paired 95% bootstrap interval is +2.19% to
+2.99%; all three confirmation pairs favored the candidate.

Measured October 26, 2026 during the 9:03–9:13 AM EDT rental on native Windows
Server 2025, AWS `m7a.8xlarge`: EPYC 9R14, 32 physical cores, 128 GiB.
Each run used 32 committed 2 GiB arenas (64 GiB total), ordinary Windows pages
and OS placement. The process working set and private usage were checked in
each report. No power limit was applied.

Both sides use ring eight and prefetch depth two. The change replaces periodic
streaming-write fences with fences before arena reads that need pending writes,
and before finalization. The confirmed implementation ships in v0.2.33 with the
existing hardware, runtime instruction, worker-count and backing gates.

The fixed research driver counts every completed hash over the shared hashing
interval, including in-flight completion. Allocation, five seconds of warmup
and teardown are excluded. No autotuning runs. These are kernel rates;
startup, pool fees and energy are separate measurements.

All **8,936 timed hashes** matched independently computed libargon2 outputs.
Twelve native full-size RustCrypto checks preceded timing, including dirty reuse
and guard checks. The integrated shipping kernel also passed its native Windows
MSVC reference, dispatch and streaming-boundary tests.

The campaign used the repository's `benchctl.py campaign`, with separate
screening and confirmation, three seconds between invocations, and frozen
binaries. The confirmation gate required a positive 95% lower bound. The
interval uses 20,000 paired percentile bootstrap samples of mean log ratios,
seed 24094. Raw reports and TSV remain unchanged in [screen/](screen/) and
[confirm/](confirm/). Revisions, binary checksums and rates are in
[summary.json](summary.json).

## Reproduce

Use the [frozen research source](../genoa-fences-20261026/source.tar.gz) from
the Linux investigation. It includes both Windows-compatible drivers. The
original Windows control revision differs only in unused dispatch alternatives
and comments in its driver; its periodic loop and measurement logic match,
as recorded in [source-equivalence.json](source-equivalence.json).
Rebuilt executables need not be byte-identical to the measured binaries.

On native Windows with Rust 1.93.0, the MSVC build tools, Python and at least
80 GiB available RAM, extract the source and build:

```powershell
cargo +1.93.0 build --locked --release --target x86_64-pc-windows-msvc `
  -p blocknet-pow-kernel --features cpu-research `
  --example streaming_ring_grid --example streaming_fence_experiment
.\target\x86_64-pc-windows-msvc\release\examples\streaming_ring_grid.exe verify 8 2
.\target\x86_64-pc-windows-msvc\release\examples\streaming_fence_experiment.exe verify 8 2
```

From this evidence directory, provide absolute binary paths to the wrapper:

```powershell
python run_ab.py --baseline C:\source\target\x86_64-pc-windows-msvc\release\examples\streaming_ring_grid.exe `
  --candidate C:\source\target\x86_64-pc-windows-msvc\release\examples\streaming_fence_experiment.exe `
  --pairs 3 --seconds 30 --output-dir C:\seine-fence-confirm
```

`python verify.py` audits the published file checksums, memory observations,
counters and every captured hash against the supplied independent references.
Reference keys are `header_hex:decimal_nonce`. Independent regeneration uses
libargon2 Argon2id v19, 2,097,152 KiB, one iteration, one lane, 32-byte output,
eight-byte little-endian nonce as password and the 92-byte header as salt.
Regeneration needs 2 GiB per concurrent hash; the default audit only reads data.
