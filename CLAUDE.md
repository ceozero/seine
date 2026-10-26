# seine

External Blocknet miner with pluggable CPU/GPU backends.

## Developer & Agent Reference

See [AGENTS.md](AGENTS.md): the zero-config, per-architecture performance goal, where arch-specific decisions live, and how to measure changes.

## Key Paths

- `src/miner/` — runtime orchestration (mining, scheduler, backend control, stats)
- `src/backend/` — PoW backend implementations (CPU, NVIDIA, AMD, Metal)
- `pow-kernel/` — CPU hash kernels and ISA dispatch
- `scripts/` — build and benchmark helpers
- `CPU_OPTIMIZATION_LOG.md` — measured CPU tuning history
- `NVIDIA_OPTIMIZATION_LOG.md` — measured NVIDIA tuning history
