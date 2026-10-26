# EPYC 9355P: combined page and power configuration

**Prepared, not measured; not launched in this campaign.** The full short-sample
experiment completed and its evidence was collected, but fresh provider cleanup
access was not restored before this protocol's **13:42 EDT** latest-start deadline.
No combined page/power result, partial comparison or additional rental was created.
The frozen protocol below remains a future experiment; its preparation did not
change or shorten the preceding measurement protocol.

The earlier independent experiments found a package-efficiency benefit from a
240 W cap and a small benefit from 1 GiB pages. Their gains cannot be multiplied:
this new comparison measures the combined configuration directly. It does not
isolate either factor or establish an interaction effect; that would require a
fresh matched four-cell factorial design.

## Frozen comparison

Use the same portable Rust 1.93.0 CPU-only ring-64 executable as the page-size
trial: SHA-256 `a4d3bd3b1091102b9d50b8d5c80aed057e8d30534ddcfee742b1d69ec137f6dc`.
Use the already verified EPYC 9355P: 32 cores, 64 threads, one socket/NUMA node,
192 GiB in twelve DDR5-4800 channels. Both roles use 64 workers, explicit
`avx512-256-stream`, automatic affinity and disabled runtime tuning.

| Role | Explicit pages | Requested package cap |
|---|---|---|
| Baseline | 2 MiB | 280 W |
| Candidate | 1 GiB | 240 W |

These caps are settings, not measured watts. Read package RAPL over each complete
invocation; do not add the core subdomain. Startup, mapping, hashing, fences and
teardown are included. Pool reservation and the ten-second settling interval
are excluded. DRAM and wall energy are unmeasured.

1. Verify all prior controllers are inactive, their archives collected with
   verified checksums, and the host restored: both pools empty, unused swap
   enabled, stock 280 W cap. Freeze the new scripts, authorization, binary and
   verifier identities before admission.
2. Disable unused swap. Attempt 128 free 1 GiB pages. If unavailable, record the
   allocation result and restore settings; do not reboot, shrink the experiment
   or silently fall back. Run all 21 full-size reference/dirty-reuse/guard checks
   with the actual 1 GiB mapping.
3. Run four fresh alternating pairs (AB, BA, AB, BA). Each leg has one full
   120-second end-to-end measurement and zero uncounted warmup rounds. Before
   every leg, empty both pools, reserve 65,536 two-MiB pages or 128 one-GiB pages,
   set and read back that role's power cap, and settle for ten seconds.
4. Require all 64 arenas to use the requested backing without fallback or
   allocation failure. Preserve raw energy samples, reports, before/after pool
   states and cap readbacks. Require the same executable/build identity, CPU
   masks, boot, frequency policies and RAPL constraints across all legs, with
   no swap or OOM activity. The HSMP cap is the explicitly varied power control.
5. Recompute four paired ratios from raw measurements. Efficiency passes only
   when the upper descriptive 95% J/hash bound is below zero and the lower H/s
   bound is at least −2%. Report every pair and preserve losses or null results.
   A positive lower H/s bound is a separate throughput result. No automatic
   defaults are proposed from this manually configured operating-point test.
6. Restore the 280 W cap, empty both pools, re-enable the originally unused swap,
   and verify restoration. Collect and checksum all evidence before deletion.

## Hard admission limits

The existing reservation remains USD 13.20 Cherry plus USD 3.25 AWS, USD 16.45
of the approved USD 25 total. This experiment requires no additional funding or
rental extension. Record its admission in the same ledger before starting.

The controller deadline must leave ten minutes before the already recorded
**14:25 EDT** provider-deletion deadline, and at least 30 minutes of execution
plus three minutes of restoration after admission. Therefore the latest start
is strictly before **13:42 EDT** on 2026-10-25. If the earlier complete protocol
and evidence review do not finish in time, defer this follow-up without running
any partial pair. The provider/funding/goal deadlines take precedence.

Use unit `seine-amd-efficient-config.service`, runtime maximum 1,980 seconds,
SIGINT and a 180-second control-group stop timeout. The controller also checks
remaining time before every bounded child. No earlier experiment's durations,
pair count, cleanup allowance or deadline may change to make this fit.

Use `/usr/bin/python3` for collection, analysis and export. Graph records retain
manual configuration, whole-invocation package scope, both power caps, complete
binary provenance, all repetitions and their variability. An unavailable or
unrun experiment must not produce numeric graph points.
