# AMD (HIP/ROCm) Backend Bring-Up Plan

Target: **RX 7900 XTX (gfx1100, RDNA3, 24 GB, wave32)** on a rented Linux
ROCm box. The backend is scaffolded to compile and unit-test on any x86_64
Linux host with no AMD hardware or ROCm installation; everything below is the
first-hardware iteration checklist.

## Status / scope

- `--features amd` (OFF by default). All HIP/hipRTC FFI is hand-declared and
  dlopen'd at runtime (`libamdhip64.so`, `libhiprtc.so`) — no ROCm headers or
  toolkit needed at build time.
- Kernel: HIP port of the CUDA Argon2id fill/seed/eval kernels
  (`src/backend/amd/amd_kernel.hip`), keeping A29 full-warp cooperative
  mapping, A77/A78 unrolled loads/stores, A81 closed-form G-round indexing,
  and A82 shuffle fusion. The A73 dead-code-prefetch codegen hack and its
  first-8-threads guard are NVIDIA/PTXAS-specific and were omitted.
- Wavefront strategy: **wave32 only**. hipRTC compiles with
  `--offload-arch=<gcnArchName>` plus `-mno-wavefrontsize64` (with a retry
  without the flag if a hipRTC build rejects it), and the engine hard-refuses
  devices reporting `warpSize != 32` — so CDNA (wave64) boxes quarantine at
  startup with a clear message. The cooperative barrier is `__syncthreads()`
  (block == one wave32 wavefront), chosen for correctness over speed.
- Autotune: stub. Lanes derive from free VRAM with allocation/probe backoff
  (11 × 2 GiB lanes expected on 24 GB); launch depth fixed at 1. Regcap/depth
  sweeps and any AMD-specific scheduling work come after this checklist
  passes.

## Qualify the rental and software stack

As of 2026-10-25 at 11:45 EDT, the AMD campaign had not established a
compatible GPU rental or a native HIP result.
Confirm the exact GPU, native device access and complete OS/kernel/driver/HIP
combination before reserving a machine. A provider's "AMD" label or installed
shared libraries do not prove the device is usable by this backend.

- Pin a combination listed in AMD's
  [Linux support matrix](https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/native_linux/native_linux_compatibility.html).
  As checked on 2026-10-25, that page lists RX 7900 XTX for ROCm 7.2.1 and
  explains that releases from Core SDK 7.13.0 use unified documentation.
  Select the matching version's matrix; do not assume "6.x or newer" is a
  qualified stack. Vendor support does not establish Seine correctness.
- The host must load `amdgpu`; verify the container/VM exposes usable
  `/dev/kfd` and `/dev/dri`. Record GPU name, PCI ID, `gcnArchName`, HIP-reported
  wavefront size, VRAM, driver/runtime/hipRTC versions, OS and kernel.
- Install build deps: `rustup` (repo pins 1.93.0 via rust-toolchain.toml),
  `build-essential`, `git`.
- If the loader cannot find the libraries, add ROCm to the search path:
  `export LD_LIBRARY_PATH=/opt/rocm/lib:$LD_LIBRARY_PATH`.

For the proposed RX 7900 XTX target, confirm `gfx1100`, approximately 24 GB
VRAM, and HIP-reported wavefront size **32**. Record actual available memory;
the number of usable 2 GiB arenas can be lower than the nominal VRAM capacity.

## Verification sequence

Run steps in order; each gate must pass before the next is meaningful.

### (a) Unit tests, including the ignored hardware tests

```bash
cargo +1.93.0 test --locked --no-default-features --features amd backend::amd:: -- --test-threads=1
cargo +1.93.0 test --locked --no-default-features --features amd backend::amd::engine::tests::hip_device_props_parse_sanely -- --ignored --exact --nocapture
cargo +1.93.0 test --locked --no-default-features --features amd backend::amd::engine::tests::hiprtc_kernel_compiles_for_device_arch -- --ignored --exact --nocapture
```

The checks, in dependency order (run each hardware test separately and stop on
failure; disabling default features avoids unrelated NVIDIA hardware tests):

The compile and differential hardware tests currently use the first enumerated
device. Confirm that it is the intended wave32 GPU before running them; checking
another device's properties is insufficient.

1. `backend::amd::hip_ffi::…loader_reports_missing_rocm…` (not ignored; on
   a pass alone does not prove ROCm loaded, because the test also accepts the
   expected missing-library error. The subsequent device query must succeed).
2. `backend::amd::engine::tests::hip_device_props_parse_sanely` — validates
   the hand-declared legacy (`R0000`) `hipDeviceProp_t` ABI: wavefront size
   must read a plausible 32 or 64 and `gcnArchName` must start with `gfx`.
   Separately require **32 for the selected mining device**; a plausible wave64
   device can pass the ABI test but is unsupported by this backend. **If the ABI test fails, the
   struct layout in `src/backend/amd/hip_ffi.rs` is wrong for the installed
   ROCm — fix offsets before anything else; every later step depends on it.**
3. `backend::amd::engine::tests::hiprtc_kernel_compiles_for_device_arch` —
   first real hipRTC compile of the ported kernel. Compile-log errors surface
   in the test failure message.
4. `backend::amd::tests::gpu_solution_target_bracket_matches_cpu_reference`

### (b) Small-scale correctness differential vs the CPU backend

This mirrors the NVIDIA backend's ignored GPU-vs-CPU differential
(`gpu_solution_target_bracket_matches_cpu_reference` in
`src/backend/nvidia.rs`, which brackets each nonce with target == CPU hash
(must solve) and target == hash − 1 (must not solve)):

```bash
cargo +1.93.0 test --locked --no-default-features --features amd backend::amd::tests::gpu_solution_target_bracket_matches_cpu_reference -- --ignored --exact --nocapture
```

A pass proves the full pipeline — seed blocks, 2 GiB Argon2id lane fill,
last-block export, Blake2b target evaluation — is bit-exact against
`blocknet-pow-kernel` for several nonces. If hashes mismatch, bisect with the
seed kernel first (dump `seed_blocks` DtoH and compare against the CPU H0
path) before suspecting the compression loop.

### (c) Single-lane kernel benchmark

```bash
cargo +1.93.0 run --locked --release --no-default-features --features amd -- --bench --bench-kind kernel \
  --backend amd --amd-max-lanes 1 --bench-secs 20 --bench-rounds 3 \
  --bench-output bench-amd-1lane.json
```

Record the measured rate without an expected H/s target. Also run
`--bench-kind kernel-effective` to measure the benchmark's effective wall-time
scope; keep that result separate from kernel timing.

### (d) Lane scaling on 24 GB

```bash
for lanes in 1 2 4 8 11; do
  cargo +1.93.0 run --locked --release --no-default-features --features amd -- --bench --bench-kind backend \
    --backend amd --amd-max-lanes $lanes --bench-secs 20 --bench-rounds 3 \
    --bench-warmup-rounds 1 --bench-output bench-amd-${lanes}lane.json
done
```

- 11 lanes is the expected maximum: 24 576 MiB total − 384 MiB reserve →
  ~23.6 GiB budget / 2 GiB per lane (the engine backs off automatically if
  the display or other processes hold VRAM).
- Treat this ascending sweep as screening only. Confirm any chosen lane count
  with fresh interleaved paired runs, recording actual allocated lanes,
  warmup, duration, completed hashes, variability and thermal conditions.
  Do not infer AMD hashrate or scaling from NVIDIA measurements or theoretical
  memory bandwidth. Keep failed allocations and negative results.
- Check `late_hash_pct` in the report: with depth 1 and cancel checkpoints
  every 64 blocks, round-end preemption should be comparable to the NVIDIA
  backend's; a large value suggests the device-side cancel flag isn't being
  observed (verify the `volatile` load in the kernel actually bypasses
  caches on RDNA3 — see "Known risks" below).

### (e) Mining smoke test (pool)

```bash
cargo +1.93.0 run --locked --release --no-default-features --features amd -- --backend amd --address YOUR_BLOCKNET_ADDRESS
```

Confirm: backend line shows `amd` with its actual allocated lane count; cancel/fence startup probe
passes (the backend advertises cooperative deadlines, so it is NOT gated
behind `--allow-best-effort-deadlines`); shares from backend `amd` are
accepted by the pool.

## Evidence and power scope

Preserve source revision, binary and kernel-source checksums, compiler options,
commands, full JSON reports, correctness/cancel logs and the exact device/software
identity. Export completed observations with their benchmark kind, numerator,
denominator, repetitions and uncertainty. A screen or ignored test is not native
validation, and no result from this guide should enter README/website graphs
until its evidence is collected and reviewed.

For efficiency, record the actual sensor and measurement interval. A configured
board power limit is not measured watts. If only sampled board power is
available, disclose the sampling/integration method and missing samples; do not
present it as a hardware energy counter. Keep GPU-board, CPU-package and wall
power distinct, and leave unavailable measurements null. Confirm any power
setting with a new paired hashrate/energy comparison before recommending it.

## Known risks to verify on hardware (in priority order)

1. **`hipDeviceProp_t` legacy ABI layout** — covered by step (a)/test 2.
2. **hipRTC option acceptance** — `--offload-arch` with a full target id
   (`gfx1100:sramecc-:xnack-`) and `-mno-wavefrontsize64`; the engine
   already retries without the wave flag and surfaces the compile log.
3. **Cancel-flag visibility during a running kernel** — the interrupt
   controller writes via a non-blocking stream while the fill kernel polls a
   `volatile` global pointer. Verify with a mid-round cancel (`Ctrl-C`
   during mining or the step-(d) round fences) that fences complete in
   ≪ 1 s rather than after a full launch.
4. **`__shfl` on 64-bit values under wave32** — exercised by the (b)
   differential; a wrong-width shuffle shows up as hash mismatches.
5. **Multi-device** — a bare `--backend amd` on a 2-GPU rental now
   auto-expands to one instance per wave32 device (`--amd-devices 0,1`
   pins the same topology explicitly); device binding is per worker
   thread (`bind_thread()`), which this verifies.

## After bring-up (deferred tuning surface)

Only after (a)–(e) pass, in an AMD_OPTIMIZATION_LOG.md mirroring the NVIDIA
process: launch-depth sweep (`hashes_per_launch_per_lane`), cancel-check
cadence, waves-per-CU occupancy experiments, `s_setprio`/scheduling hints,
`__builtin_amdgcn` barrier relaxations replacing `__syncthreads()`,
wave64-native kernel for CDNA, and a persisted autotune cache keyed like the
NVIDIA one (device, arch, hiprtc version, kernel fingerprint).
