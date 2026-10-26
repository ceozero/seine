# AMD overnight campaign, 2026-10-25

The Turin ordering experiment is complete and accepted. See [results and
limitations](RESULTS.md), [the bound adoption review](adoption-review.json) and
[graph records](benchmark-records.json). The original resource fixture failed
to create reclaim pressure; its unchanged failed archive and the complete
[same-binary resource supplement](RESOURCE_SUPPLEMENT.md) are audited together.

The user authorized up to ten hours and **USD 25 total**, including the active
Cherry session and any AWS rentals. The goal began at 04:42:52 EDT; finish all
collection and rental cleanup before **14:42:52 EDT**. Operational identities,
SSH material and cumulative spending remain in ignored data directories.

## Order and budget

1. Finish the already frozen Cherry physical-worker, SMT and stock/240 W phases.
   Their protocols and original 05:40 EDT controller deadline are unchanged.
2. Resume the frozen Genoa eligibility validation when the shared AWS quota is
   free. Its one 110-minute lease retains its USD 3.25 sub-budget. Do not stop
   another campaign's instance or increase the account quota.
3. Extend Cherry only for the following native work, at USD 1.20/hour, to a
   planned maximum of six total rental hours (USD 7.20), including provisioning.
   Collect and delete by **09:46 EDT** unless a subsequent experiment is
   explicitly recorded within the overall goal deadline and remaining budget.
   Shutdown alone does not terminate a Cherry rental.

These reservations total USD 10.45, leaving USD 14.55 unallocated. Reserved
amounts are exposure limits, not claims of actual billed cost. Keep provider
charges distinct from account credit and estimated charges.

Subsequent operational reservation, recorded before launching follow-ups:
eight total Cherry hours (USD 9.60), with provider deletion before **11:35 EDT**,
for the separately frozen buffer and page-size experiments. With the unchanged
AWS USD 3.25 reservation, the reserved total is USD 12.85 of USD 25. Delete
promptly when measurements and evidence collection finish; the reservation is
an upper bound. The original productive protocol and deadline were unchanged.

## Turin cold-start challenger ordering: pre-measurement protocol

Existing paired evidence establishes that streaming can beat uniform kernels
at higher concurrency on Turin. The shipping tuner tries AVX2 before streaming.
Test whether trying streaming first improves completed productive work during
cold starts. Do not force a winner or remove a challenger, confirmation cycle,
drift gate, retry, ISA check or resource-pressure safeguard.

- Control: portable CPU-only build from `09ca72c`; candidate differs only in
  challenger ordering for AuthenticAMD family 1Ah/model 02h. Other identities
  retain their existing order. Freeze exact revisions and binary hashes.
- Host: the qualified Cherry EPYC 9355P, 32 cores/64 threads, twelve populated
  DDR5-4800 channels, 192 GiB installed RAM, one NUMA node. Stock 280 W cap.
- First check the new fixture/controller for 60 seconds; this plumbing run is
  excluded from comparative results.
- Check fixed streaming at 32 workers in three alternating build-control pairs
  (one 20-second warmup, two measured 20-second rounds per invocation). This
  separates changes in discovery from incidental build/code-layout effects.
- Four fresh paired cold runs, alternating control/candidate then
  candidate/control, **1,200 seconds per invocation**. Each gets an empty data
  directory. All 64 logical CPUs are available, with no explicit thread count,
  minimum, maximum or kernel flag. This is automatic count/kernel selection on
  pre-reserved 2 MiB HugeTLB pages, not a claim of unconfigured page setup.
- Run each leg's own cached restart for 180 seconds, in reverse cold-run order.
  Never copy caches between builds. Preserve logs, actual commands, cache
  contents, CPU masks, cgroup counters and completed-hash lower bounds.
- Measure completed hashes reported by the miner divided by wall time from
  service-start request through stopped service. This includes discovery,
  startup and shutdown; log counters may omit final unreported completions.
  Do not compare it as though it were the fixed-kernel backend or energy metric.
- Require no quarantine, swap, OOM, persistent fixture interruption or resource
  loss. Review all paired results, time to first confirmed streaming selection,
  selected counts and cold/cached trajectories. Adoption requires a positive
  lower descriptive 95% paired bound for cold throughput, no meaningful cached
  regression (lower bound at least -2%), and intact confirmation/cache behavior.
  Otherwise retain the experiment without changing the shipping policy.
- Run reference/unit gates and resource interruption/restart recovery before
  landing an accepted policy. Restore swap and page pools after each controller.
  After the cold/cached matrix, run the existing black-box lifecycle checks on
  four CPUs with ordinary pages: memory pressure, parking, CPU contention,
  cached restart under a temporary one-arena budget, recovery and explicit
  opt-out. Allow 1,350 seconds for this phase within a four-hour controller limit.

Do not overlap package-energy samples with builds, archive compression or other
CPU-heavy work on the measured host. Keep original and follow-up phases separate.

## Reporting

After the native controller stops, run `/usr/bin/python3 collect.py --ssh-config
<campaign-ssh-config> --output <fresh-evidence-directory>` from this directory.
The collector exits 75 without archiving while measurements are active. Once
inactive, it preserves raw results, frozen executables and protocol files, checks
both manifests locally and records the archive checksum. Failed runs are still
collected; only complete runs with restored settings are marked ready for a
follow-up experiment. The analysis and landing gates remain separate.

`frozen-builds.json` records the measured revisions, build settings and binary
checksums. To reconstruct the measured candidate after branch rebases, check out
its recorded control revision and apply `candidate-runtime.patch`. The patch
checksum is recorded in the same JSON; applying it to the control reproduces
every runtime/library/build-file difference in the measured candidate.

Export machine-readable records with exact hardware/memory settings, source and
binary identities, worker/kernel/page configuration, metric scope, repetitions,
variability and raw evidence checksums. CPU package watts exclude unmeasured DRAM
and wall losses. Preserve unsuccessful attempts and partial runs as such. Public
graphs must retain the configuration and measurement scope of the source data.

Further experiments should follow observed bottlenecks. AMD GPU work requires an
available supported wave32 device and full correctness bring-up before tuning;
do not rent a wave64-only GPU as a substitute. No production restart or release
is authorized by this campaign.
