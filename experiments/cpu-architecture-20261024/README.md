# CPU architecture matrix — 2026-10-24

This experiment tests real guest-visible CPU generations using the current
Blocknet Argon2id workload (2 GiB per worker). Its purpose is to validate
instruction-set paths and identify dispatch exceptions. It does not rank
whole servers or estimate mining profitability.

## Protocol

- Generic x86-64 Linux CPU-only release builds, Rust 1.93.0, no native CPU flags.
- The frozen matrix binaries contain scalar, AVX2 and existing AVX-512 paths;
  they predate `avx512-256`. That experimental path has separate Genoa and
  9950X3D checks below.
- Full-size RustCrypto reference parity before timing, for every supported
  kernel in both builds. Scalar is tested for correctness, not throughput.
- AVX2-only hosts compare the pre-paired implementation with paired AVX2.
  AVX-512 hosts compare explicitly selected AVX2 and AVX-512 in the **same
  binary**. These are different questions; their percentages are not additive.
- Fixed workers, autotuning disabled, `--cpu-affinity os`, persistent backend
  mode. No daemon, pool, network hashing, GPU, or changed PoW rules.
- Main matrix: one regular-page worker, one HugeTLB worker, four HugeTLB
  workers. HugeTLB means explicit 2 MiB pages, verified for every worker.
- Four alternating A/B pairs per configuration, each invocation containing one
  warmup and two measured 12-second rounds, with two seconds between runs.
- Followups use 20-second rounds and otherwise retain the paired protocol.
- Completed H/s is all completed hashes divided by actual elapsed time,
  including the round-end fence. The table uses the ratio of the arithmetic
  means of the four invocation rates. Deadline-counted rates are retained
  separately in `summary.json`.
- Paired bootstrap intervals enumerate all resamples of the four paired
  percentage changes. They describe repeatability on that VM, not uncertainty
  across physical hosts, operating systems, or an entire CPU generation.
- Each accepted run has the requested worker count/backing, no allocation
  failures, dropped events, assignment/control timeouts, swap or OOM, and
  less than 2% CPU steal. The inactive RAM-derived autotune cap may vary;
  actual fixed workers and arena bytes must match.
- Results are downloaded, SHA-256 verified, then analyzed. Binary checksums,
  source fingerprints, CPUID identity, configuration and PoW must match the
  intended comparison. A partially copied result is never accepted.

## Results

All ten main cells completed and passed integrity checks. Positive values
mean the candidate was faster; the baseline differs between these two tables.

### Paired AVX2 versus pre-pairing AVX2

| CPU | VM | Ordinary / 1 worker | HugeTLB / 1 worker | HugeTLB / 4 workers |
| --- | --- | ---: | ---: | ---: |
| Zen 1 / Naples (EPYC 7571) | `m5a.2xlarge` | +12.79% | +15.60% | +10.62% |
| Zen 2 / Rome (EPYC 7R32) | `c5a.2xlarge` | +22.24% | +34.36% | +10.49% |
| Zen 3 / Milan (EPYC 7R13) | `c6a.2xlarge` | +9.11% | +14.10% | +3.22% |
| Broadwell (Xeon E5-2686 v4) | `r4.2xlarge` | +10.81% | +11.90% | +11.86% |

### Existing AVX-512 versus paired AVX2, same binary

| CPU | VM | Ordinary / 1 worker | HugeTLB / 1 worker | HugeTLB / 4 workers |
| --- | --- | ---: | ---: | ---: |
| Zen 4 / Genoa (EPYC 9R14) | `c7a.2xlarge` | -1.19% | -3.07% | -2.63% |
| Zen 5 / Turin (EPYC 9R45) | `c8a.2xlarge` | +20.26% | +15.76% | -1.73% |
| Cascade Lake (Xeon 8275CL) | `c5.2xlarge` | +19.08% | +17.87% | +17.17% |
| Ice Lake (Xeon 8375C) | `c6i.2xlarge` | +21.47% | +28.71% | +25.55% |
| Sapphire Rapids (Xeon 8488C) | `c7i.2xlarge` | +7.93% | +8.53% | +7.36% |
| Granite Rapids (Xeon 6975P-C) | `c8i.2xlarge` | +6.10% | +7.22% | +6.23% |

Absolute rates, individual paired deltas, bootstrap intervals and VM counter
checks are preserved in `summary.json`. Granite Rapids was more variable than
the other Intel guests, although all pairs favored AVX-512.

### Guest-visible identity

Family/model/stepping are decimal. Every main guest exposes eight logical CPUs;
Genoa and Turin expose eight physical cores, the others expose four.

| CPU | Vendor | Family / model / stepping |
| --- | --- | --- |
| Zen 1 / Naples (EPYC 7571) | AuthenticAMD | 23 / 1 / 2 |
| Zen 2 / Rome (EPYC 7R32) | AuthenticAMD | 23 / 49 / 0 |
| Zen 3 / Milan (EPYC 7R13) | AuthenticAMD | 25 / 1 / 1 |
| Zen 4 / Genoa (EPYC 9R14) | AuthenticAMD | 25 / 17 / 1 |
| Zen 5 / Turin (EPYC 9R45) | AuthenticAMD | 26 / 2 / 1 |
| Broadwell (Xeon E5-2686 v4) | GenuineIntel | 6 / 79 / 1 |
| Cascade Lake (Xeon 8275CL) | GenuineIntel | 6 / 85 / 7 |
| Ice Lake (Xeon 8375C) | GenuineIntel | 6 / 106 / 6 |
| Sapphire Rapids (Xeon 8488C) | GenuineIntel | 6 / 143 / 8 |
| Granite Rapids (Xeon 6975P-C) | GenuineIntel | 6 / 173 / 1 |

## Followups and dispatch decision

### Turin: independent longer repeat

A second `c8a.2xlarge` repeats one and four HugeTLB workers with 20-second
measured rounds. Both VMs expose the same 9R45 identity, one NUMA node, one L3
group and no SMT. AVX-512 relative to AVX2:

| VM / round length | 1 worker | 4 workers |
| --- | ---: | ---: |
| Initial / 12 seconds | +15.76% | −1.73% |
| Independent / 20 seconds | +15.06% | −2.56% |

All four pairs in both four-worker cells favor AVX2. The second VM's completed
rates are 2.5281 → 2.9087 H/s at one worker and 8.7424 → 8.5187 H/s at four;
paired intervals are +14.72% to +15.66% and −2.83% to −2.30%, respectively.
The worker-count crossover repeats, but its underlying hardware cause has not
been isolated.

### Genoa: higher worker counts

The larger `c7a.4xlarge` exposes 16 physical cores, one NUMA node and two L3
groups: CPUs 0–7 and 8–15. Fixed `os` placement packs eight workers into the
first group and places twelve as eight plus four. Production `auto` placement
would spread them differently. These are controlled scaling comparisons,
not a validation of a new default under production placement.

| Backing / workers | AVX2 H/s | AVX-512 H/s | AVX-512 delta | Paired 95% interval |
| --- | ---: | ---: | ---: | ---: |
| regular / 8 | 7.5365 | 7.4536 | -1.10% | -1.36% to -0.84% |
| large / 8 | 7.8084 | 7.6080 | -2.57% | -2.97% to -2.12% |
| large / 12 | 14.1548 | 13.7815 | -2.64% | -2.93% to -2.36% |

All four pairs favor AVX2 in each configuration. The twelve-worker case uses
24 GiB of verified explicit HugeTLB arenas. No swap/OOM, backing failures,
dropped events or assignment/control timeouts occurred. The topology and
placement limit above remains applicable despite the consistent direction.

### Retained policy

- Keep the existing paired AVX2 implementation; real older CPUs confirm its
  gains across every measured configuration in this matrix.
- Keep the existing portable automatic ISA preference and OS feature guards.
  Do not infer a single Zen 5 preference from a single-worker result, or extend
  the fixed-placement 9R14 results to all Genoa/Zen 4 systems.
- Keep `avx512-256` explicitly selectable for benchmarks. Its four-worker
  advantage over paired AVX2 is not consistent enough to select automatically.
- Any later kernel search should key observations by kernel, enabled worker
  count, actual backing and placement/topology. The separate count-only
  autotuner work is not expanded or overridden here.

## Experimental 256-bit AVX-512 path

`avx512-256` retains 256-bit data operations and uses AVX-512 native rotates.
It is separately labeled and requires AVX2, AVX-512F and AVX-512VL with OS
vector-state support. It is available only through explicit benchmark
selection; automatic dispatch does not choose this experimental path.

The cooperating EPYC experiment developed the implementation and measured it
on a separate Genoa 9R14 VM. Three paired prototype comparisons against the
existing 512-bit implementation gave completed-throughput gains of 5.71% at
one HugeTLB worker, 5.53% at four HugeTLB workers, and 1.86% at four ordinary-page
workers. Against paired AVX2, the one-worker HugeTLB gain was 2.13%, but the
four-worker gain was only 0.27% with mixed pair signs.

The final separately labeled binary (`ac4feba`) passed full-size reference
parity on Genoa and the local 9950X3D. Two opposite-order four-worker integration
passes gave the following completed rates; this is a short integration
confirmation, not an additional long performance trial:

| Backing | AVX2 H/s | AVX-512 H/s | AVX-512/256 H/s |
| --- | ---: | ---: | ---: |
| HugeTLB | 7.3018 | 7.0162 | 7.3968 |
| Ordinary | 5.6842 | 5.5692 | 5.6795 |

The new path consistently improves on the old 512-bit path in these Genoa
checks, but does not establish a consistent multiworker win over AVX2.
A further prototype that fused the XOR and row stage was rejected: three
paired four-worker HugeTLB comparisons fell from 7.4037 to 6.4136 completed
H/s (−13.37%). It is not included in the integrated implementation.

Its algorithm remains consensus-equivalent; its name describes an
implementation, not a new PoW or an entire CPU-generation guarantee.

## Reproduction and artifacts

Build the current miner and `pow-kernel/examples/verify_cpu_kernels.rs`.
For the AVX2-only comparison, build a second checkout differing only by the
reversal of the paired-AVX2 change (`103f170`). The frozen sources are recorded
in `sources.json`; all matrix/followup miners use those exact binaries.

On a dedicated, otherwise idle Linux host, lay out:

```text
bin/seine
bin/seine-old-avx2
bin/verify-current
bin/verify-old-avx2
scripts/bench_cpu_ab.sh
scripts/bench_cpu_architecture.py
```

Then run:

```sh
python3 scripts/bench_cpu_architecture.py --root "$PWD"
# Longer selected configurations, with enough RAM for 2 GiB per worker:
python3 scripts/bench_cpu_architecture.py --root "$PWD" \
  --seconds 20 --configs regular-t8 large-t8 large-t12
```

The runner requires sudo to reserve HugeTLB pages, refuses a pre-existing
pool, disables no system services, and restores the pool in `finally`.
Each run creates a new `results/` directory and refuses to overwrite it.
Provisioning is deliberately separate from this host-local runner.

Raw reports, binaries, launch/cleanup records, manifests and exact controller
scripts are retained locally in the matrix worktree under:

- `data/architecture-matrix-20261024/`
- `data/architecture-turin-confirmation-20261024/`
- `data/architecture-genoa-scaling-20261024/`

Experimental-path evidence is retained in the kernel-variants worktree under
`data/variant-validation/` and the EPYC worktree under `data/epyc-avx512vl/`,
`data/epyc-control/`, and `data/epyc-final/`. Source-module commit:
`7cf798122cdb41e934106710cbba861f14252f27`; explicit-label integration:
`ac4febae92970dddb9012812df50337f26b19247`.

## Limits

These are small EC2 VM allocations. A new VM allocation does not prove a
different underlying physical host. CPU model, exposed SMT/topology, memory
bandwidth share, page policy and worker count can all affect the winner.
A four-worker result is not a fully populated EPYC socket result. Fixed `os`
affinity may also differ from production `auto` placement when a larger guest
exposes multiple L3 groups or NUMA nodes. There is no
hardware-counter evidence here attributing a difference specifically to
bandwidth, clock throttling, cache, or vector execution width.

Testing an AVX2 override on Zen 5 is not a substitute for a Zen 1–3 host; this
matrix uses actual separate generations. It still does not cover every
stepping, desktop SKU, Zen+, Intel hybrid client CPU, or every Intel server
generation. Windows and macOS kernel cross-compilation establish buildability,
not native performance. Existing desktop evidence remains separate.

AWS instance families identify the requested platforms; actual guest CPUID
and CPU brand in the reports determine what was tested. See the official
[AWS compute instance catalog](https://docs.aws.amazon.com/ec2/latest/instancetypes/co.html).

## Cloud lifecycle

Each rental has an instance-initiated termination deadline, delete-on-termination
root disk, task-specific tags, and SSH restricted to the controller's /32.
The controller retrieves results and terminates each VM immediately afterward.
The original launcher attempt failed before producing accepted timings; those
resources were cleaned up and its artifacts are kept separately. No results
from that failed attempt enter this analysis. A Genoa followup launch also hit
the vCPU quota before creating an instance; its temporary security group and
key were removed before the successful queued retry.

All 12 accepted validation VMs, their root disks and the three dedicated
security groups have been removed. Temporary private keys are gone, including
those from the discarded launcher/quota attempts. A final tag-scoped AWS audit
found no remaining task instances, volumes or security groups; unrelated
resources were left alone. See `lifecycle.json` and `cleanup-audit.json`.

The accepted evidence contains 35 configurations, 140 A/B pairs (280 invocations) and
560 measured rounds, plus warmups and full-size reference checks.
