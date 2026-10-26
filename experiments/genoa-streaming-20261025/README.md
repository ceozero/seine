# Genoa productive streaming eligibility

Status on 2026-10-25: **validation complete; automatic trial eligibility accepted**.
Cold discovery improved **2.85%** and cached restarts **7.99%** in two paired
windows each on the tested EPYC 9R14 VM. See [RESULTS.md](RESULTS.md) for the
full measurement scope and adoption review. The instance was terminated at
07:44 EDT immediately after evidence collection; its volume and security group
were verified deleted. The duration-based upper cost estimate is $2.765,
not an AWS invoice.

This experiment adds AMD family 19h/model 11h to streaming **trial** eligibility.
It preserves runtime ISA checks, the default starting kernel, count-specific
comparisons, two confirmations, and cache scoping. Existing native 9R14 evidence
at 24 workers showed +27.19% versus AVX2; eight-worker results were flat.

Control source: `751e808`. The candidate differs only in eligibility and its
tests. Frozen executable SHA-256 values are recorded before rental launch.
CPU-only portable Rust 1.93.0 release builds use the same toolchain and flags.
This is throughput validation, not a package-energy or whole-system H/W test.

Graph-ready [JSON](benchmark-records.json) and [CSV](benchmark-records.csv)
contain four records with per-run hashes, duration, variability, source and
binary identities, and explicit VM/power scope. Re-export from the verified
private archive with:

```sh
python3 experiments/genoa-streaming-20261025/export_records.py \
  data/genoa-streaming-20261025/collected \
  experiments/genoa-streaming-20261025/frozen-builds.json \
  experiments/genoa-streaming-20261025 \
  --review experiments/genoa-streaming-20261025/adoption-review.json
python3 experiments/genoa-streaming-20261025/plot.py
```

The explicit review is bound to the exact result-manifest and binary checksums.
Omitting it retains the assessor's pending-review status.

`frozen-builds.json` records the measured revisions, build settings and binary
checksums. To reconstruct the measured candidate after branch rebases, check out
its recorded control revision and apply `candidate-runtime.patch`. The patch
checksum is recorded in the same JSON; applying it to the control reproduces
every runtime/library/build-file difference in the measured candidate.

## Frozen protocol

One exclusively owned `c7a.8xlarge` in us-east-1, 32 vCPUs (one thread per
guest-exposed core) and 64 GiB guest RAM. This is a Linux VM, not a full bare-metal
EPYC socket; physical memory-channel population and DIMM speed are unobserved.
Require AMD family 25/model 17, all expected instructions, no swap, and
an independent shutdown timer with EC2 shutdown-to-terminate. The account's
existing 32-vCPU quota must be free; do not interrupt another campaign.
Live rate checked through AWS Pricing: $1.64224/hour. One 110-minute lease has
$3.011 compute exposure; reserve $3.25 total including boot time, root volume,
IPv4 and small evidence downloads. No automatic extra lease or budget reset.

1. Run full-size RustCrypto parity, including all 21 dirty-arena kernel switches.
2. Check fixed AVX2 build effects at 24 workers using two alternating pairs,
   15-second warmup plus two measured 15-second rounds, verified 2 MiB HugeTLB.
3. Natural productive cold-cache runs: control A, candidate A, candidate B,
   control B, 900 seconds each, with a 24-worker maximum and default kernel
   selection. No minimum count or kernel is forced. The local fixture uses an
   impossible target; service networking is restricted to loopback.
4. Restart each run from its own cache, in reverse order, for 180 seconds.
   Verify that candidate cache restoration actually selects streaming and that
   all restarted counts match the corresponding cold-cache selections.
5. On ordinary pages, run the established RAM/load/restart harness with a
   600-second initial phase, four-CPU/four-worker ceiling, one- and zero-arena
   budgets, recovery, CPU contention, constrained restart and explicit opt-out.
   This checks resource behavior separately from HugeTLB throughput.
6. Restore the initially empty HugeTLB pool, stop every owned unit, archive
   raw logs/reports/caches with a checksum manifest, download and verify them,
   then terminate the instance and verify volume/security-group deletion.

`run.py` copies and uses the established helpers from
`../cpu-followups-20261025/` (their frozen copies/hashes travel in the bundle).
`../cpu-followups-20261025/analyze.py` recomputes fixed and productive results
from raw evidence. Cold and cached rates are completed-hash lower bounds over
startup through shutdown. Two paired windows describe this host/session only.

The local coordinator uses `/usr/bin/python3` (Python 3.12), including the safe
tar extraction filter. It rejects older interpreters before allocating a lease.

## Landing gate

All correctness/resource checks must pass, both cold candidate runs must
confirm streaming for a reached count, cached restarts must restore it, and
paired productive rates must be reviewed alongside the fixed-kernel build
control. Interrupted/noisy runs are retained as such. If this gate fails or
the time/cost limit is reached, preserve the candidate on its branch and do
not enable Genoa trials on master. Do not report the prior fixed-kernel 27%
gain as a new automatic-mining gain.

The assessor and graph exporter accept `--include-rejected` to preserve complete,
integrity-checked observations when tuning confirmation or cache restoration
fails. Such records carry a rejected landing status and list the failed gates
in the analysis. This option does not relax correctness, resource, provenance
or completeness checks, and does not authorize enabling the candidate.
