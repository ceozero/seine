# EPYC 9355P: 2 MiB versus 1 GiB HugeTLB

Completed: [native results](RESULTS.md) measured **+0.908% whole-invocation H/s**
and **−0.330% package J/hash** with 1 GiB pages, passing both predeclared gates.
All 128 pages allocated and all 21 native reference transitions passed. Two
[JSON](benchmark-records.json)/[CSV](benchmark-records.csv) graph records retain
the same executable and complete measurement scope. No default policy changed.

Preregistered on 2026-10-25 after a read-only capability check found a zero-sized
1 GiB HugeTLB pool exposed by the qualified host. Allocation feasibility and
performance were unmeasured when this protocol was frozen. Do not change either page pool during the earlier
productive-tuner or streaming-ring experiments.

This compares page backing with the **same frozen ring-64 streaming executable**
and 64 workers. Keep the stock 280 W cap, affinity auto, kernel selection explicit,
autotuning disabled, one socket/NUMA node and twelve DDR5-4800 channels. No kernel,
compiler, worker-count, runtime policy or power-cap change belongs in the pair.
Use the existing 120-second whole-invocation package-energy metric so hashrate,
watts and joules per completed hash come from the same observed interval.

## Sequence and gates

1. Require earlier native controllers inactive, their evidence collected and
   verified, unused swap restored, both page pools empty and stock cap unchanged.
   Freeze the executable, verifier, scripts and protocol identities before launch.
2. Disable the unused swap and attempt to reserve 128 one-GiB pages dynamically.
   Verify all 128 pages are free. If this is not possible, preserve the allocation
   evidence and restore settings; do not reboot, fall back to smaller pages or
   reduce the worker count inside this experiment.
3. Verify full-size RustCrypto parity, dirty reuse and guard blocks with the
   streaming kernel actually operating on a 1 GiB HugeTLB mapping. Record the
   observed mapping page size; ordinary-page parity alone does not pass this gate.
4. Run four alternating pairs, control/candidate then candidate/control. Control
   is `large` (2 MiB), candidate `large-1g` (1 GiB). Each invocation is one
   120-second end-to-end round with zero uncounted warmup rounds. Before each leg,
   empty both pools and reserve only the required pool (65,536 two-MiB pages or
   128 one-GiB pages), verify its free count, and allow ten seconds to settle.
5. Record package RAPL energy and all completed hashes over the same invocation.
   Require the requested backing for all 64 arenas (128 GiB), no fallback,
   allocation errors, swap or OOM; unchanged CPU masks, boot, clocks/power policies
   and 280 W cap. Preserve before/after pool states and raw samples/checksums.
6. Recompute paired ratios from raw evidence. A useful efficiency result requires
   the upper descriptive 95% bound for joules/hash below zero and the lower
   throughput bound at least -2%. A throughput-only result needs a positive lower
   throughput bound and must not be called an efficiency improvement. Preserve
   null or adverse outcomes as well as wins; four pairs describe this host only.
7. Restore both pools to zero and re-enable the originally unused swap. Verify
   restoration, collect evidence locally, then proceed or delete the rental.

Pool reservation and the ten-second settling interval occur outside the measured
invocation. Startup, arena mapping, hashing, fencing and teardown are included.
These are CPU-package measurements, excluding unmeasured DRAM and wall losses.
No default page-policy change is proposed; any benefit is an explicit operating
configuration with disclosed host preparation.

## Time and spending

Require a bounded 40-minute controller window plus collection and provider
cleanup margin. Record any required Cherry extension in the existing campaign
ledger before starting; this document schedules no extension. Keep the campaign
under its $25 total and **14:42:52 EDT** cleanup deadline. This steady-state
investigation may take priority over the still-unmeasured short tuning-window
candidate if both cannot fit. Never shorten an already-running protocol to fit it.

`run.py` additionally requires verified prior-collection markers and a
ledger-backed authorization file containing the controller deadline, provider
deletion deadline, funded-credit horizon and total reserved campaign dollars.
The provider deadline must precede both the funded horizon and goal deadline.
Use outer unit `seine-amd-page-size.service`, a 2,520-second runtime maximum,
SIGINT, default control-group termination and a 180-second stop timeout. The
controller reserves three minutes for restoring both pools and swap, and ten
minutes between its deadline and provider deletion for collection/cleanup.
