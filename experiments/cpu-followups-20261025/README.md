# CPU follow-up experiments

This campaign completes three bounded investigations. Physical energy measurement
remains deferred by the user. GPU work is outside scope.

| Investigation | Reviewable implementation | Required evidence |
|---|---|---|
| Joint count/kernel selection | [PR50](https://github.com/zpalmtree/seine/pull/50), compiled source `7477914` | Current v0.2.22 control, fixed-kernel controls, cold A/B/B/A productive runs and matching cached restarts on C5, Ice Lake and Turin |
| Intel regression isolation | [PR49](https://github.com/zpalmtree/seine/pull/49), source `c68ade5` | Legacy, enum-gated and independently aligned binaries on the same Ice Lake host; no promotion based on static disassembly |
| Actual reduced-memory hashing | [PR51](https://github.com/zpalmtree/seine/pull/51), source `aeab118` | Independent full-size reference parity, dirty reuse, measured throughput and process RSS; 24 full-memory versus 32 reduced-memory workers within a 48 GiB ceiling on Turin |

The joint integration starts from released master `6e54117`. It preserves the
merged multi-challenger EPYC tuner and its narrow hardware eligibility, without
pulling in the separate parked-slot/PID or ARM changes from the old PR47 stack.
PR50 supersedes that stack's joint integration.

## Reproduction and measurement boundaries

`lease.py` manages exclusively owned, tagged cloud resources with separate
115-minute controller and 120-minute shutdown-to-terminate limits. The user
approved a separate **$10 total cap**; the three maximum-duration rentals reserve
$6.16864 compute plus $2 for disk, IPv4 and transfer. Operational credentials,
launch state and raw downloads stay under ignored `data/followups-20261025/`.
The original $40 campaign is separate.

`binary-identities.json` records seven immutable main inputs and two additional
alignment builds. `run_native.py` verifies
their hashes, executes full-size parity, paired fixed-kernel controls, memory
experiments and productive cold/cached episodes. Each download is checked against
every entry in its manifest before cleanup. `analyze.py` independently recomputes
rates from the downloaded raw records and checks cumulative accounting.

Fixed-kernel throughput is completed hashes divided by actual measured duration,
including the measurement fence. Explicit 2 MiB HugeTLB backing, zero allocation
failures/timeouts/drops, no swap/OOM and bounded steal time are checked. Short
paired intervals describe repeatability on that host; they do not establish
architecture-wide uncertainty.

Productive windows use the real miner against an isolated loopback fixture.
Cold episodes last 900 seconds in A/B/B/A order; cached restarts last 180 seconds
in reverse order using each matching cold episode's own cache files. Counts,
kernel trials and interruptions remain natural. The reported lower-bound rate
includes startup and shutdown; final hashes after the last stats emission can be
omitted. The stats counter is cumulative across dev-fee transitions. Kernel/count
selection and cache restoration must be inspected separately from throughput;
ending an episode is not proof that every possible configuration converged.

Reduced-memory timings use ordinary allocator pages with THP disabled for both
the full-memory and reduced variants. Each worker warms before the synchronized
measured nonce stream. Hashes divided by the longest worker duration is the
aggregate rate. Native RSS excludes independent reference verification, which
runs separately. Buffer accounting includes metadata and retained allocation;
RSS additionally captures process/allocator overhead. The 48 GiB wide comparison
is a memory-constrained offline hashing experiment, not a comparison against the
production miner's HugeTLB path. Prototype workers use OS scheduling, without the
miner's affinity controller. The EPYC-only threshold-1 control retains every
block to expose prototype overhead without recomputation.

`run_alignment.py` runs a fresh AVX-512 2x2 comparison after the main Ice Lake
controller has stopped. Original and `-C llvm-args=-align-all-functions=6` builds
use separate Cargo target directories, distinct verified identities and four
rotated/reversed passes. Equal function-entry alignment cannot eliminate every
layout effect or establish a unique cause. An earlier shared-target artifact
reuse was caught by identical binary hashes before timing; that invalid pair is
excluded from all native evidence.

After C5's timed comparisons, `run_lifecycle.py` runs the established native
resource harness with a fresh ordinary-page cache and a four-worker cap. Its
360-second initial phase allows the joint count/kernel policy to persist a
confirmed count before testing reductions to one and zero arenas, recovery, CPU
contention, a constrained cached restart, and explicit opt-out. This is a safety
experiment separate from the twelve-worker HugeTLB throughput comparison. Only
task-owned systemd units are changed, and the existing rental deadline still
applies. `after_main.py` prevents either post-run experiment from overlapping the
main controller or starting without enough time remaining.

## Completion gate

Native work is complete; see `status.json` and `joint-native-results.json`. Final results include
all host outcomes, actual cache behavior, negative findings, verified resource
cleanup and spending. Draft status is intentional until those records exist.
