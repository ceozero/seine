# seine

External Blocknet miner with pluggable CPU/GPU backends.

## Developer & Agent Reference

See [AGENTS.md](AGENTS.md): the zero-config, per-architecture goal, where arch-specific decisions live, and runtime invariants.

## Key Paths

- `src/miner/` — runtime orchestration (mining, scheduler, backend control, stats)
- `src/backend/` — PoW backend implementations (CPU, NVIDIA, AMD, Metal)
- `pow-kernel/` — CPU hash kernels and ISA dispatch
- `scripts/` — build, release and chart helpers
