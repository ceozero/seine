# Streaming-ring locality on SMT Turin

Completed: [screening and fresh confirmation](RESULTS.md) retained the shipping
64-block buffer. The 16-block/64-worker candidate gained 0.367% in confirmation,
below the predeclared lower-bound-above-1% gate; no energy phase or kernel change
followed. [JSON](benchmark-records.json)/[CSV](benchmark-records.csv) retain all
ten screening/confirmation graph points, including slower variants.

Prepared before measuring these variants, during the separate productive-tuner
campaign on 2026-10-25. No shipping kernel change is authorized by this protocol.

## Hypothesis and controls

The qualified EPYC 9355P exposes 48 KiB L1 data cache per physical core and two
hardware threads per core. The shipping streaming kernel keeps a 64 KiB recent
block ring per worker. Smaller rings could improve locality under SMT, but
require more frequent MFENCE operations. The prior VM work did not establish
this tradeoff on a complete socket with SMT. No gain is assumed.

Generate **16- and 32-block rings**, against the unchanged 64-block control.
Change the ring size, recent-reference distance and data-dependent prefetch mask
consistently. Keep the strict less-than distance rule (equal distance aliases
the destination), full cache-line streaming stores, MFENCE before older arena
loads, final fence, SIMD schedule, prefetch distance and all other kernels intact.

`prepare.py` builds portable CPU-only variants in this owned experimental
worktree, saves each exact patch/source/binary identity, runs boundary/dirty-arena
tests and the full-size reference verifier, and restores the original production
source files after every build. Variant labels are experiment identities: all
three binaries still report the same explicit streaming CLI kernel name.
Do not publish a generated variant as a replacement for the normal binary.

## Native sequence

Run only after the current cold/cached tuner and lifecycle controller is finished
and its evidence has been collected. Never overlap these workloads.

1. Recheck host identity, stock 280 W cap, restored page pool/swap and available
   PMU interfaces. Capture available events and a short diagnostic profile of
   the control at 32 and 64 workers. Only interpret counters whose definitions
   and complete scheduling are verified; do not infer DRAM bandwidth from a
   generic cache-miss counter.
2. Repeat full-size reference parity on the native host for every frozen build.
   Reserve explicit 2 MiB HugeTLB arenas and verify backing. Keep affinity auto.
3. Screen each challenger at 32 and 64 workers in two opposite-order pairs:
   one 15-second warmup plus two measured 15-second rounds per invocation.
   Keep every completed observation, including slower variants.
   `run_native.py` freezes the order as 32 workers then 64, ring 32 then ring 16
   at each count. Shortlist the largest positive paired geometric delta for the
   first confirmation; a positive screen alone never passes the shipping gate.
4. A screen is only a shortlist. If a challenger is promising, confirm it against
   ring 64 at that worker count with four fresh alternating pairs, one 30-second
   warmup and two measured 30-second rounds. Require a lower descriptive 95%
   paired throughput bound above +1%, correct hashes and no resource failures.
5. If confirmed, make a separate four-pair package-energy comparison using
   120-second whole-invocation windows, same count/cap/pages/affinity. Both binary
   identities must be explicit; the existing worker/power comparator intentionally
   disallows comparing different binaries. Validate raw measurements and common
   context before computing a cross-build paired result.
6. Only an accepted native result may motivate a hardware-gated production path.
   Preserve the current implementation for unmeasured identities. Validate its
   actual automatic path, fallback/ISA gate and caches before landing it.

The screen controller uses the unchanged paired harness from
`experiments/cpu-followups-20261025/bench.py`, copied into the frozen upload.
It requires an operator-written `prior-evidence-collected.json` marker, an
inactive prior controller and verified restored host settings before starting.
Every child has a deadline and process-group cleanup. The outer systemd service
must also have a bounded runtime and default control-group termination.

The diagnostic profiles use grouped userspace cycles, retired instructions, core
data-cache requests to L2, and those requests missing L2. Event definitions are
captured from the host's own `perf list --json`. These are whole-invocation
profiles with no uncounted warmup. Failed or incompletely scheduled counters are
uninterpretable, and the L2 counters do not measure DRAM bandwidth. This host has
core/IBS PMUs but no exposed Data Fabric PMU. Profiling and hash throughput runs
are separate; profiling overhead is not part of the throughput comparison.
The read-only HSMP sysfs interface is also available: `profile.py` records its
DDR-bandwidth, clock and thermal-limit readings every two seconds only while
each diagnostic invocation runs. These integer GB/s firmware estimates are
separate non-atomic reads, not integrated byte counters. They may help diagnose
saturation but cannot establish precise bytes per hash. Units follow the
[Linux HSMP documentation](https://docs.kernel.org/arch/x86/amd_hsmp.html).
No HSMP observer runs during the throughput or energy comparisons.

`confirm.py` runs four fresh throughput pairs for the recorded shortlist. A
failed +1% lower-bound gate completes as a rejected experiment without spending
time on energy pairs. A passed gate triggers the four fresh package-energy
pairs. `compare_energy.py` recomputes every numerator and denominator from the
raw samples and checksummed benchmark reports. It requires each role's frozen
binary identity, unchanged host/runtime/compiler settings, verified page backing,
no swap/OOM activity, and the same 280 W HSMP cap before and after every run.
This experimental comparator leaves the production power/worker comparator's
same-binary restriction intact. `test_compare_energy.py` checks successful
cross-build comparison and rejection of corrupted or incompatible evidence.

Collect all evidence and restore cap/pages/swap before the rental cleanup point.
The existing six-hour Cherry reservation is USD 7.20. If a ready experiment needs
more time, record a bounded extension before starting it; at most two additional
hours would make Cherry USD 9.60 and, with the USD 3.25 Genoa reservation, USD
12.85 total. This remains inside the user-approved USD 25 campaign limit. The
overall goal cleanup deadline is 14:42:52 EDT; unused time or budget is not a
reason to keep an idle rental.
