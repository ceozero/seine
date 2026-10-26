# seine — Agent Guide

seine is the external Blocknet miner other people run on their own hardware.
The goal of almost every change: **the best hashrate on each user's exact
hardware, with zero configuration.** A user who runs `seine --address ...`
and touches nothing should get the right kernel, thread/lane count, page
mode, and affinity for their CPU and GPUs.

## Principles

- **Zero-config first.** A win that needs a flag helps nobody but us. Land it
  as an automatic default (gated to the hardware it was measured on) or as a
  candidate the runtime tuner can find by itself. Flags are for experiments
  and overrides, not the shipping path.
- **Gate by precise identity, not one global policy.** If something helps
  one architecture and is neutral or harmful on others, enable it only where
  it was measured: x86 vendor/family/model, aarch64 features, CUDA compute
  capability or exact device name, HIP `gcnArchName`. Don't reject it because
  it doesn't win everywhere, and don't extend it to "similar" hardware
  without evidence.
- **Two independent gates.** Identity decides whether we *try* a path. The
  runtime ISA/OS support check (`is_x86_feature_detected!`, etc.) decides
  whether we *can*. Never let identity bypass the support check, and always
  keep a safe fallback (`CpuKernel::preferred()`, the generic GPU candidate
  set).
- **Evidence before defaults.** A new default needs a paired A/B on the
  target hardware (interleaved, thermally stable, see Measuring), recorded in
  the relevant optimization log. Kernel micro-opts are mostly exhausted:
  read the REJECTED entries in the logs before proposing kernel work.
- **Correctness is non-negotiable.** Every kernel variant must match the
  reference Argon2id output. Consensus validation stays in the daemon, so a
  wrong hash costs users rejected shares, not chain safety.

## Where per-arch decisions live

| Decision | Location |
|---|---|
| CPU kernel variants + ISA support check + fallback order | `pow-kernel/src/cpu_kernel.rs` (`CpuKernel`, `is_supported`, `preferred`) |
| Kernel implementations | `pow-kernel/src/fixed_argon.rs`, `pow-kernel/src/fixed_argon/` |
| Which CPU kernels the live tuner may try, per identity | `src/miner/adaptive_kernel.rs` (`candidates_for`) |
| CPU identity (vendor/family/model) and build/runtime fingerprint | `src/runtime_identity.rs` (`cpu_identity`) |
| Live CPU worker count tuning, joint count/kernel comparisons (each candidate count finishes its kernel sweep), memory/PSI shedding | `src/miner/adaptive_cpu.rs` (`tick_joint`), `src/miner/adaptive_kernel.rs` |
| CPU topology / affinity (NUMA, L3, SMT, macOS P-cores) | `src/backend/cpu/topology.rs`, `src/config.rs` (`pcore_count`, `macos_hybrid_pcore_parallelism_cap`) |
| Page mode (HugeTLB / Windows large pages / THP) | `src/config.rs`, `src/backend/cpu.rs` |
| NVIDIA per-arch/per-device tuning (regcap candidates, launch depth, cancel interval) | `src/backend/nvidia.rs` (`*_RTX_5090`, `BLACKWELL_*`, `select_cancel_check_block_interval`) |
| AMD arch gating (wave32 only) and hipRTC flags | `src/config.rs` (`partition_wave32_amd_devices`), `src/backend/amd/engine.rs` (`build_hiprtc_options`) |
| Apple GPU | `src/backend/metal.rs` |

Every autotune cache is keyed by host/build/topology/page-mode fingerprints.
When you add an identity-gated path, add it to the fingerprint or candidate
set so stale caches from a different path get re-tuned, not reused.

## Adding or changing an arch-specific path

1. Measure on the exact target hardware (rented or remote is fine; the dev
   box is not a mining rig, so tear down hugepages and miners afterwards).
2. Gate it in the matching location above, with a one-line comment naming
   the identity and the measured win.
3. Add a unit test for the gate: the intended identity selects the path, a
   neighbouring identity doesn't, and an unsupported ISA never does (see the
   `candidates_for` tests).
4. Check parity: kernel reference tests in `pow-kernel`, plus
   `pow-kernel/examples/verify_streaming_dispatch.rs` for streaming/ring
   kernels.
5. Record the result (kept or reverted) in `CPU_OPTIMIZATION_LOG.md` or
   `NVIDIA_OPTIMIZATION_LOG.md`, and add a user-facing line to `CHANGELOG.md`
   if defaults change.

## Measuring

- Before choosing hardware optimization targets or answering a telemetry status
  request, run `python3 telemetry/agent_report.py` when production SSH access is
  available. It checks service/storage health and returns aggregate inventory and
  comparable performance cohorts without installation IDs or raw reports.
- Handle the analysis for the user: summarize collection health, adoption and the
  next evidence-backed experiment. Do not direct them to a dashboard or require
  manual SQL. If data is sparse or the query fails, say so; do not infer a regression
  from missing reports or treat live hashrates as benchmark proof. See
  `telemetry/README.md#agent-analysis` for interpretation and operating limits.
- Use the interleaved A/B harnesses, not single runs:
  `scripts/bench_cpu_ab.sh`, `scripts/bench_nvidia_ab.sh`,
  `scripts/benchctl.py` (paired runs with CIs). Leave tuning flags unset so
  both sides use their shipping defaults, unless the flag is the experiment.
- `--bench-kind kernel` isolates the hash kernel. `backend` measures
  steady-state workers. `end-to-end` includes start/fence/teardown and is
  closest to what users see.
- The zero-config path is what matters: also check a cold start with an
  empty `--data-dir` and see what the tuner picks, not only a hand-pinned
  config.
- More harness detail: `docs/PERFORMANCE.md`, `docs/benchmarks.md`.

## Runtime invariants (don't break these)

- Backends get disjoint nonce chunks per round. Solutions are never dropped
  (lossless `Solution` events, deferred re-queue on submit backlog).
- A faulty backend is quarantined alone; mining continues on the rest.
- Mining control loops do no network I/O (prefetch/submit workers own it).

## Formatting

- Use the pinned toolchain: `cargo +1.93.0 fmt` (see `rust-toolchain.toml`).
- Format only files you edited. No repo-wide `cargo fmt --all` and no
  formatting-only churn in commits unless asked.

## Release notes (`CHANGELOG.md`)

- Write for miners deciding whether to upgrade: what improves, who benefits,
  and any action they need to take. Lead with the biggest user benefit; put
  measured hashrate gains and the affected hardware first when available.
- Use short, plain-language bullets, usually one sentence each. Aim for 3–5
  bullets; small releases may need only one. Combine related fixes. A useful
  example is "About 33% higher CPU hashrate on Ryzen 9 9950X3D at 8 threads."
- Omit internal test data and implementation details: no run counts, sampling
  windows, confidence intervals, cache schemas, kernel internals, code symbols,
  or validation narratives. Keep those in engineering docs. Users need the
  benefit, not an explanation of how we implemented or tested it.
- Never show losses, regressions or no-gain results in release notes. Those
  belong in `CPU_OPTIMIZATION_LOG.md` / `NVIDIA_OPTIMIZATION_LOG.md`.
- Quote only measured gains on named hardware, and don't extrapolate to
  untested models. Round sensibly, retain a short qualifier when needed for
  accuracy, and distinguish faster startup from higher sustained hashrate.
  Use a qualitative benefit when a number needs a lengthy explanation.
- Keep required upgrade steps and compatibility changes, including API auth
  and changed flags, in a brief note for affected users. Link to instructions
  when needed. Never hide a required action to make the notes shorter.
- Keep `CHANGELOG.md` and published GitHub release notes in sync. Publish the
  edited notes plus a full-changelog link, without generated commit/PR lists.
  When editing existing releases, preserve tags, binaries and release status.

## References

- Every flag: `docs/MINER_FLAGS.md` / `seine --help`.
- Tuning history and rejected ideas: `CPU_OPTIMIZATION_LOG.md`,
  `NVIDIA_OPTIMIZATION_LOG.md`, `docs/NVIDIA_5090_TUNING.md`.
- Hardware-specific notes: `docs/AMD_BRINGUP.md`, `docs/CPU_ENERGY.md`,
  `docs/validation/`.
