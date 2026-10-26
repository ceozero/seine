# AMD CPU efficiency campaign

Updated 2026-10-25 after the first qualified bare-metal measurements. This
campaign measures the current legacy 2 GiB Argon2id workload; conclusions apply
to that algorithm and the measured configuration.

## Measured EPYC 9355P efficiency

On a 32-core/64-thread EPYC 9355P with twelve populated DDR5-4800 channels,
64 streaming workers measured **66.56 H/s at 213.03 W of CPU package power**
with a 240 W cap. Four alternating pairs against the stock 280 W cap retained
**98.42% of throughput** while reducing **package energy per hash by 13.41%**.
All measurements include startup, allocation, work and teardown. Power is from
the CPU package counter; wall-plug and separate DRAM energy are unmeasured.

The [complete report](../experiments/cherry-epyc-energy-20261025/RESULTS.md)
separates worker scaling from the longer power comparison. Its
[JSON records](../experiments/cherry-epyc-energy-20261025/benchmark-records.json)
and [CSV records](../experiments/cherry-epyc-energy-20261025/benchmark-records.csv)
carry hardware, settings, duration, repetitions, variation and evidence hashes
for future README/website graphs. These are manual fixed-configuration results;
productive automatic-tuning follow-ups are a separate campaign.

## Measured explicit 1 GiB pages

On the same qualified EPYC 9355P at the stock 280 W cap, four alternating
same-binary pairs measured **68.256 H/s with 1 GiB pages**, versus **67.642 H/s
with 2 MiB pages**, using 64 streaming workers. The paired gain was **0.908%**;
package energy per hash improved **0.330%**. Both throughput and energy cover
the whole invocation, including startup and teardown. Pool preparation occurs
outside that interval. All 128 required one-GiB pages allocated successfully.

The [complete page-size report](../experiments/amd-page-size-20261025/RESULTS.md)
and [graph records](../experiments/amd-page-size-20261025/benchmark-records.json)
retain actual package watts, paired uncertainty and reference/backing checks.
This is the existing explicit `large-1g` configuration; automatic page selection
is unchanged. The combination of 1 GiB pages and a 240 W cap remains a separate,
unmeasured configuration.

## Current baseline

Use current `master`, not the older `codex/linux-numa-defaults` checkout. The
streaming kernel and productive joint count/kernel tuning have already landed.
[Performance](PERFORMANCE.md) records 49.39 H/s on a 32-worker Turin VM and
10.31 H/s on the native Windows 9950X3D streaming test. Neither establishes
package or wall energy efficiency, and the VM result is not a full-socket rate.
The [energy harness](CPU_ENERGY.md) already measures package joules over a full
invocation; its worker sweep now includes explicit streaming-kernel selection.

## Throughput work independent of energy-counter access

**Genoa EPYC 9R14 automatic streaming trials are now validated.** On the tested
32-vCPU c7a.8xlarge VM, family 25/model 17, two paired productive windows gained
**2.85% during cold discovery and 7.99% on cached restarts** with automatic worker
and kernel selection, a 24-worker ceiling and explicit 2 MiB HugeTLB. The runtime
ISA check, two-confirmation gate and safe starting kernel remain intact.
[The complete report](../experiments/genoa-streaming-20261025/RESULTS.md) includes
reference parity, restart/resource behavior, measured source identities and
[graph-ready records](../experiments/genoa-streaming-20261025/benchmark-records.json).
This is VM throughput evidence; physical memory-channel population and power
were unmeasured. The earlier +27.19% fixed-kernel result is a separate comparison
and must not be presented as the automatic-mining gain.

The native tuner constructor now uses real CPU identity even in a test binary.
Synthetic fixtures explicitly request a neutral identity. Previously,
`cfg!(test)` removed streaming from the native EPYC test's candidates, making
its eligibility assertion impossible to pass. The ignored 24-worker EPYC test
is restricted to the validated Turin identity and still requires an owned host
with reserved HugeTLB memory; it is not a Genoa validation substitute.

**Turin challenger ordering is now validated on the EPYC 9355P.** Trying
streaming before AVX2 confirmed it roughly 90 seconds earlier and improved
four paired 20-minute cold productive windows by **0.685%**; cached restarts
were effectively unchanged. Both confirmation cycles and all challengers remain.
The [complete report](../experiments/amd-overnight-20261025/RESULTS.md) separates
these automatic results from fixed-kernel energy measurements and retains the
original failed resource fixture plus its successful, identical-binary retest.
The [buffer-size experiment](../experiments/amd-ring-locality-20261025/RESULTS.md)
retained the shipping 64-block implementation: a 0.367% fresh gain at 64 workers
did not meet its predeclared +1% lower-bound adoption gate. Explicit 1 GiB page
results are reported above. A full productive comparison of shorter, high-count
kernel samples is the next automatic-tuning experiment; its outcome is pending.

## Rental shortlist

Original public shortlist, checked on 2026-10-25; recheck prices and inventory
before a new order. The Cherry configuration was subsequently rented and
qualified as EPYC 9355P, with all twelve channels populated and readable package
counters. Its authenticated hourly rate is USD 1.20.

| Provider / configuration | Listed rate | Fit |
| --- | --- | --- |
| [Cherry EPYC 9355](https://www.cherryservers.com/pricing/dedicated-servers/amd-epyc-9355?billing=3), 32 cores, 192 GB DDR5 | EUR 1.026/hour listed; USD 1.20/hour authenticated | Measured 9355P host: twelve populated DDR5-4800 channels, readable package counters and HSMP cap |
| [Latitude f4.metal.large](https://www.latitude.sh/pricing), EPYC 9275F, 24 cores, 768 GB | From USD 2.62/hour | Alternative Zen 5 host; installed channels and energy counters also need verification |
| [Latitude m4.metal.xlarge](https://www.latitude.sh/pricing), EPYC 9455P, 48 cores, 768 GB | From USD 4.76/hour | Larger Zen 5 comparison at higher rental cost |
| [Scaleway EM-I520E](https://www.scaleway.com/en/pricing/elastic-metal/), EPYC 8434P | EUR 1.562/hour before tax in PAR-1 | Revisit for energy on the previously measured family; does not answer the 12-channel Turin question |

The authenticated checkout required eight hours of available credit (USD 9.60)
before deployment, even for a shorter planned rental. Identity verification and
funding subsequently completed, and the host was deployed. Available credit is
separate from actual expenditure. Plan collection and server deletion as part of
the rental window; shutting down a dedicated server is not the same as deleting
its billable resource. Keep funding/access details in the private operational
ledger rather than benchmark records.

The original two-hour measurement campaign completed within its window. A
separately authorized follow-up retains the host for productive automatic-tuner
validation. Its operational ledger owns the extended cleanup deadline.

## Host qualification

Required when repeating these measurements on another host:

- Exclusive Linux bare-metal access with host root, an exact CPU identity and
  all 12 channels populated for the memory-scaling comparison. Record DIMM
  locators, configured speeds, socket/NUMA/L3 topology and allowed CPU masks.
- Readable, advancing package counters via Linux powercap. Check all sockets;
  record counter range and ensure the sample interval bounds wraps. If these
  counters are absent, this harness cannot establish H/W on that host.
- Provider permission for sustained offline Argon2 benchmarking, and access to
  supported package-power controls if a power-limit experiment is planned.
- For whole-system H/W, a separate calibrated wall/PDU energy source covering
  the same interval. Package counters exclude unmeasured DRAM and supply losses.

Useful read-only checks, saving their output with the experiment:

```bash
lscpu -e=CPU,CORE,SOCKET,NODE,CACHE,ONLINE
numactl --hardware
sudo dmidecode --type memory
python3 -B scripts/bench_cpu_energy.py probe
```

DIMM serial numbers and remote host identifiers should stay in private evidence.
Record and later restore any changed huge-page, governor, power or BIOS settings.
Use the host's `gpuq` policy where present. Keep other agents' workloads off the
measurement host. Do not run monitoring or miner workloads on the desktop merely
to fill the lack of a qualified remote sensor.

## Measurement order

1. Freeze the source revision and binary SHA-256. Confirm the requested kernels
   match full-size reference hashes on the host before collecting performance.
   Build host-native variants on that host if needed, in separate output trees.
2. Capture a short one-worker energy point to qualify the counter and report
   pipeline. It is a plumbing check, not an efficiency claim.
3. On the 32-core host, run the documented 8/16/24/32-worker sweep with fixed
   streaming kernel and verified page backing. Use four alternating pairs and
   a fresh output directory. Reserve at least 64 GiB of arenas plus headroom.
4. Confirm the efficiency shortlist against the observed peak using longer,
   fresh paired runs. If the plateau is between coarse points, test neighboring
   counts before confirmation. Repeat with another supported kernel separately
   where the throughput evidence warrants it.
5. At a fixed shortlisted count, compare stock package limits with a supported
   lower limit in alternating runs. Record the exact effective limits. Do not
   use TDP as measured watts. Restore the original setting afterward.
6. Validate cold and cached productive mining selection using a local fixture
   pool with the existing evidence harness; keep its throughput and latency
   results distinct from the invocation energy metric. Offline fixed-kernel
   wins alone do not justify an automatic policy change.
7. Copy the raw measurements and checksums off-host, restore settings, stop
   owned processes, delete the rental, and verify billing resources are gone.

Stop a campaign on reference mismatch, counter/report failure, swap/OOM,
backend errors, changed measurement conditions or exhaustion of its time
budget. Preserve the rejected evidence with its reason. Publish no H/W ranking
until a qualified host supplies real energy measurements.
