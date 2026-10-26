# Apple Silicon

Apple Silicon Macs are excellent Blocknet miners: their unified memory gives the
memory-hard Argon2id workload plenty of bandwidth. A 48 GB M4 Max reaches about
**29–31 H/s** on CPU alone.

Seine defaults to CPU-only mining on Apple Silicon, with `pcore-only` scheduling,
and automatically sizes the thread count to your RAM. Just run `./seine`.

## Tuning

On the 48 GiB M4 Max validation host:

| Profile | Threads | H/s | Notes |
|---|---:|---:|---|
| Balanced | 14, `pcore-only` | 29.26 | 2.6% faster than 13 threads; 0.9% faster than 14 with `auto` affinity. |
| Maximum | 16, `auto` | 30.94 | macOS used about 3 GiB of swap; a throughput setting, not a balanced default. |

```bash
# Balanced on a 48 GiB 12P+4E M4 Max
./seine --backend cpu --threads 14 --cpu-affinity pcore-only

# Maximum observed rate; expect much higher memory pressure
./seine --backend cpu --threads 16 --cpu-affinity auto
```

CPU autotuning confirms close balanced-profile finalists with longer
reversed-order samples, so a noisy first scan does not cache a slower setting.

On macOS, affinity values are Mach scheduler tags plus a high-QoS preference; they
are not hard CPU-ID pinning.

## Metal (experimental)

Metal support is experimental and is never auto-selected. On the M4 Max, CPU-only
mining substantially outperformed Metal-only and CPU+Metal because both processors
compete for the same unified memory bandwidth. Pre-built macOS ARM binaries include
Metal for explicit experiments. To build from source:

```bash
cargo build --release --no-default-features --features metal
```

## Signing

The macOS binary is ad-hoc signed. If Gatekeeper blocks the first launch, allow it
in *System Settings → Privacy & Security* or run
`xattr -d com.apple.quarantine ./seine`.
