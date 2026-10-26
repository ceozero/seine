# NVIDIA GPUs

Seine mines on every detected NVIDIA GPU by default, alongside the CPU, and the
CPU and GPU hashrates add together.

```bash
# Default: no flags needed — CPU plus every detected NVIDIA GPU
./seine

# GPU-only: one backend instance per detected device
./seine --backend nvidia

# Select specific devices (also the single-GPU opt-out, e.g. --nvidia-devices 0)
./seine --backend nvidia --nvidia-devices 0,1
```

If CUDA initialization fails, NVIDIA backends are quarantined and CPU mining
continues. If a backend fails mid-run, Seine keeps warning
(`running degraded: N/M backends active`) instead of silently mining slower.

## Requirements

Seine compiles its kernels at startup with NVRTC, so you need an up-to-date NVIDIA
display driver plus the NVRTC runtime libraries.

- **Windows:** the release archive bundles the CUDA 12.8.61 NVRTC DLLs beside
  `seine.exe`. No CUDA Toolkit installation or `PATH` change is needed.
- **Linux:** install the CUDA driver and NVRTC libraries from your distribution or
  NVIDIA.
- **Source builds on Windows:** the build uses cudarc's CUDA 12.8 loader, so a
  machine with only CUDA 13.x DLL names (for example `nvrtc64_130_0.dll`) is not
  discovered. Install the CUDA 12.8 NVRTC redistributable or add its `bin`
  directory to `PATH`.

## Tuning

The first launch autotunes kernel parameters per GPU and caches the result, so later
launches start in seconds. On the desktop RTX 5090 the first-run tune takes about
half as long as before thanks to a measured shortlist. With several GPUs the
autotune cache is written under a file lock, so devices never overwrite each
other's results.

Native Windows is about 9% faster than WSL2 on the same RTX 5090 because it avoids
WSL's job-boundary latency.

Blackwell / RTX 5090 tuning notes and the measured benchmark frontier:
[NVIDIA 5090 tuning](../NVIDIA_5090_TUNING.md). Kernel history:
[NVIDIA optimization log](../../NVIDIA_OPTIMIZATION_LOG.md).

## AMD GPUs

An experimental HIP backend exists for RDNA3 (wave32) GPUs in builds with
`--features amd`; it is never auto-selected. See [AMD bring-up](../AMD_BRINGUP.md).
