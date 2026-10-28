# EPYC 9375F headline benchmark

The official Seine v0.2.39 Linux x86-64 release measured **85.10 H/s** on a
single EPYC 9375F: 32 physical cores, 64 logical CPUs and twelve 32 GiB
DDR5-6000 DIMMs. Native Ubuntu Linux, unchanged power settings; no package or
wall-power measurement. The headline rounds the confirmation mean to **85.1 H/s**.

The fixed manual configuration uses **64 mining threads**, `avx512-256-stream`
and explicit **1 GiB HugeTLB pages**, with 128 GiB of hash arenas. It does not
measure automatic tuning, pool-credited work, or a software gain over another CPU.
Measured October 27, 2026, with the screen and confirmations starting shortly
after 5:11 a.m. EDT.

## Predeclared selection and fresh confirmation

The protocol specified 60-second screens at 16, 32, 48 and 64 workers, followed
by three fresh 120-second invocations at the best screened count. Every rate
uses **all completed hashes divided by monotonic elapsed time around the entire
process invocation**, including allocation, work, fences and shutdown. There
were no warmup rounds. The report's narrower `avg_hps` is not the headline metric.

| Workers | Screen H/s |
|---|---:|
| 16 | 39.39635 |
| 32 | 63.32928 |
| 48 | 72.68263 |
| 64 | 81.78022 |

The confirmations at 64 workers measured **85.17883, 85.13616 and 84.97383 H/s**,
for an arithmetic mean of **85.0962754675205 H/s**. Their longer window amortizes
startup differently; screen and confirmation rates are not pooled.

All seven benchmark reports verified full 1 GiB backing for every arena and
zero allocation failures. Before timing, the independent 1 GiB streaming-kernel
verifier passed all 21 reference-parity cases. This verifies those test cases;
it does not claim independent verification of every timed hash.

## Evidence and reproduction

[summary.json](summary.json) binds every measurement to its original and published
SHA-256. Published benchmark JSON removes only `environment.hostname`; DIMM serial
numbers and rental access details are excluded. The release executable SHA-256 is
`decf8613f8f900932b0fa88bd269f5fca15267dc51f3b65aa66bdfeb664cf094`.
Its release archive was checked against the published checksum.

Prepare 128 free 1 GiB HugeTLB pages on an otherwise idle matching machine, then
run each confirmation in a fresh process:

```sh
seine --bench --bench-kind end-to-end --backend cpu --threads 64 \
  --disable-cpu-autotune-threads --bench-cpu-kernel avx512-256-stream \
  --cpu-page-mode large-1g --bench-secs 120 --bench-rounds 1 \
  --bench-warmup-rounds 0 --bench-output result.json \
  --data-dir ./benchmark-data --telemetry off --ui plain
```

Time the complete process externally and divide `total_hashes` by those seconds.
Restore the original huge-page reservation afterward. The
[reproduction runner](remote_measure.py) retains the executed measurement and
validation code, with the later, separate startup experiment removed. The summary
records hashes of both the executed campaign runner and this reproduction runner.

An earlier EPYC 9575F rental was deleted after a controller error before its
files were collected. Its interim readings are not used here. A replacement
9575F order was out of stock; this 9375F protocol was declared before its results.
The completed headline files were collected locally while the separate startup
experiment was running. [Cleanup verification](cleanup.json) confirms provider deletion, SSH-key removal
and stopped watchdog at 5:45 a.m. EDT after the startup experiment. The original
huge-page reservation was restored. These headline reports remain unchanged.
