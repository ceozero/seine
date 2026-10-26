# EPYC 9355P package-energy qualification

**Measurements complete.** See [results and paired comparisons](RESULTS.md),
[graph-ready JSON](benchmark-records.json), [CSV](benchmark-records.csv), and
[full numerical analysis](results.json).

One hourly Cherry Servers advertised EPYC 9355/192 GB configuration, ordered on
2026-10-25 and qualified as an **EPYC 9355P**. Rate: USD 1.20/hour. The original
measurement plan below reserved two hours/USD 2.40, with deletion by 05:46 EDT.
All three measurement phases finished within that original window. The user
subsequently authorized a separate overnight campaign and rental extension for
native automatic-tuner validation; this did not change these measurements or
their deadlines. Operational accounting and private host inventory remain under
ignored `data/cherry-epyc-energy-20261025/`.

This is the legacy 2 GiB Argon2id workload. The frozen miner source is
`36f40e6381ddc99d5b97b8cb3b5436b119a335c6`; its binary SHA-256 is
`0831080222054ab087cfc0c6253eafa79a4870a5ed4be741f8f6c15db9ff496d`.
The controller, energy harness and binary hashes travel with the evidence.
No miner default or power-limit change is part of this measurement.

## Protocol, before observing measurements

1. Use `qualify.py` to capture actual CPU identity, physical topology, DIMM
   locators and configured speeds, page-pool state, kernel and package-energy
   availability. Review the installed DIMMs before describing twelve populated
   channels. Raw DMI serial numbers stay private.
2. If necessary, load the stock kernel's `intel_rapl_msr` module and repeat the
   sensor probe separately, preserving the initial result and module state.
   Despite its name, the [upstream driver supports AMD family 1Ah](https://github.com/torvalds/linux/blob/master/drivers/powercap/intel_rapl_msr.c).
   Do not install an out-of-tree driver or change counter permissions globally.
3. Require readable, advancing package counters, no swap/OOM, sufficient RAM,
   and full-size reference parity through all 21 guarded dirty-arena transitions.
   The image's unused `/swap.img` is recorded, disabled before measurement, and
   restored by the controller's cleanup. No samples were collected in the first
   preflight, which correctly refused the image's active swap configuration.
   If the host cannot provide qualified energy measurements, collect its
   inventory and terminate early instead of reporting a watts estimate.
4. Take a 20-second one-worker plumbing measurement. Reserve 64 GiB of explicit
   2 MiB HugeTLB pages only on this exclusively owned host, recording the prior
   pool size for restoration. Use the existing harness to test 8/16/24/32 workers,
   fixed `avx512-256-stream`, automatic affinity, stock power policies,
   60-second windows, four alternating pairs against 24 workers, ten-second
   settling, and a 2,400-second sweep limit.
5. Review the measured throughput/energy frontier. If a different worker count
   has lower joules/hash while retaining 95% of the observed peak rate, confirm
   it against the peak count with fresh alternating pairs and 120-second windows.
   Otherwise retain the result as an exploratory sweep, without manufacturing
   an efficiency winner. Neighboring counts can be a separate future experiment.
6. Stop owned workloads, restore the initial page pool and any module state
   changed for this task, copy all reports and raw counter samples with hashes,
   then delete the server and verify zero hourly usage. Keep time for collection
   and deletion; do not extend the rental to finish a measurement phase.

Energy covers each complete miner invocation, including allocation, startup,
fences and teardown. It is CPU package energy, not wall-plug energy or separately
measured DRAM consumption. Do not compare these invocation rates directly to
steady-state kernel benchmark H/s or substitute TDP for measured power.

These observations can inform the next worker/power-policy investigation.
They do not independently justify an automatic miner policy change: productive
cold/cached selection and resource recovery need validation for that change.

## Separate SMT follow-up

Prepared during the physical-core sweep, before measuring more than 32 workers.
The host exposes 64 hardware threads and Seine's automatic count ceiling permits
SMT. `smt.py` therefore checks 32/48/64 workers in four fresh alternating pairs
against 32, at the unchanged 280 W cap, with 60-second windows and a 30-minute
phase limit. It reserves 128 GiB of explicit pages and restores the original
empty pool and unused swap file afterward. Keep this phase's controls separate
from the earlier 24-worker baseline; do not call 32 the socket's best count
without evaluating the SMT results.

## Separate power-limit follow-up

Prepared while the stock worker sweep was running, before taking any reduced-cap
measurement. Host qualification found `amd_hsmp_hwmon` with a 280 W cap and
300 W maximum. [AMD specifies 240–300 W cTDP for this CPU](https://www.amd.com/en/products/processors/server/epyc/9005-series/amd-epyc-9355p.html);
the [kernel documents its writable HSMP power cap](https://kernel.org/doc/html/latest/arch/x86/amd_hsmp.html).

If time permits after the stock sweep and any required count confirmation,
`power.py` fixes the completed SMT sweep's peak-throughput count (or the original
sweep's count if SMT was not run) and runs four fresh
alternating pairs at 280 W versus 240 W. Each invocation uses 120 seconds of work
and ten seconds of settling. It records and verifies the HSMP cap before and
after every invocation, separately from the energy harness's RAPL constraints.
Both arms use the same binary, streaming kernel, page mode, worker count and
affinity. The original cap, hugepage pool and swap configuration are restored.

Treat reduced-cap efficiency as a within-session result only if all four paired
joules/hash differences improve, their descriptive 95% interval is below zero,
and the throughput interval's lower bound retains at least 95% of the baseline.
Otherwise report the result as neutral, rejected or inconclusive as appropriate.
This phase does not extend the original rental deadline or change miner defaults.
