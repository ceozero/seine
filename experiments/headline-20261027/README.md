# EPYC headline benchmarks

The current headline results are **77.07 H/s on EPYC 9355P** and **75.04 H/s
on EPYC 9554P**, both with the official v0.2.39 release and 64 mining threads.

## EPYC 9554P

The official Seine v0.2.39 Linux x86-64 release measured **75.04 H/s** on a
single EPYC 9554P (64 physical cores, 128 logical CPUs), using 64 mining
threads and explicit 1 GiB HugeTLB pages. The machine had twelve 32 GiB
DDR5-4800 DIMMs, one per channel. Native Ubuntu Linux; power settings were
left unchanged. No package or wall-power measurement was made.

Measured October 27, 2026, starting at 3:03 a.m. EDT. This is a fixed manual
configuration, not a measurement of automatic tuning or pool-credited work.

## Selection and confirmation

Before collecting results, the experiment specified a 60-second screen at
32, 64, 96 and 128 threads, followed by three fresh 120-second invocations at
the best screened thread count. All screening results are retained:

| Mining threads | Screen H/s |
|---|---:|
| 32 | 51.11 |
| 64 | 72.00 |
| 96 | 71.17 |
| 128 | 70.23 |

The three confirmations at 64 threads measured **75.03285, 75.05483 and
75.02493 H/s**, for an arithmetic mean of **75.03753 H/s**. The longer
confirmation interval amortizes allocation and shutdown differently from the
screen; the screen and confirmation rates are not pooled.

Every rate here divides **all completed hashes** by monotonic elapsed time
around the complete process invocation, including allocation, work, fences and
shutdown. The benchmark JSON's `avg_hps` is a different, narrower interval and
is not the chart metric. There are no warmup rounds. All runs verified full
1 GiB backing for every arena and zero allocation failures. The independent
reference verifier passed all 21 1 GiB kernel parity cases before measurement.

## Reproduction and evidence

Download the official v0.2.39 `seine-linux-x86_64.tar.gz` release and verify
its published archive checksum. The extracted binary's SHA-256 is
`decf8613f8f900932b0fa88bd269f5fca15267dc51f3b65aa66bdfeb664cf094`.
Prepare 128 free 1 GiB HugeTLB pages on an otherwise idle matching machine,
then run each confirmation separately:

```sh
seine --bench --bench-kind end-to-end --backend cpu \
  --threads 64 --disable-cpu-autotune-threads \
  --bench-cpu-kernel avx512-256-stream --cpu-page-mode large-1g \
  --bench-secs 120 --bench-rounds 1 --bench-warmup-rounds 0 \
  --bench-output result.json --data-dir ./benchmark-data \
  --telemetry off --ui plain
```

Time the complete invocation externally and divide `total_hashes` by those
seconds. Restore the previous huge-page reservation afterward. The original
[runner](remote_measure.py) also isolates the process network namespace and
records exact timing, hardware, page backing and correctness checks.

[summary.json](summary.json) contains all confirmation measurements and their
checksums, plus the complete screening table. Per-invocation measurement files
retain the original benchmark-report checksum. Published benchmark JSON files
remove only `environment.hostname`; the summary records both original and
published checksums. Hardware serial numbers and rental access details are not
published. The kernel verifier log, CPU topology and cleanup outcome are included.

The rented server was deleted after collection. An earlier, separate 9355P
attempt ended after a controller timeout and produced no complete timed result;
it is not used in this 9554P result.

## EPYC 9355P rebenchmark

A fresh 32-core/64-thread EPYC 9355P rental had twelve 16 GiB DDR5-4800 DIMMs,
one per channel, and native Ubuntu Linux. The same 64-thread, streaming-kernel,
1 GiB-page configuration above was used. Power settings were left unchanged;
no package or wall-power measurement was made.

The exact v0.2.24 executable from the original page-size experiment was compared
with the official v0.2.39 release. Its SHA-256 is
`a4d3bd3b1091102b9d50b8d5c80aed057e8d30534ddcfee742b1d69ec137f6dc`.
The predeclared order was baseline/current/current/baseline, with one fresh
120-second invocation per run and no warmup rounds:

| Order | Version | Whole-invocation H/s |
|---|---|---:|
| 1 | v0.2.24 | 66.48332 |
| 2 | v0.2.39 | 77.12782 |
| 3 | v0.2.39 | 77.01533 |
| 4 | v0.2.24 | 66.58857 |

The two current runs average **77.07157 H/s**, versus **66.53595 H/s** for
the paired baseline. The geometric mean of the adjacent paired ratios is
**+15.83449%**. This is a same-machine, fixed-configuration comparison between
these executable versions. It does not attribute the gain to one optimization
or measure automatic cold-start tuning. Two paired observations do not establish
a cross-host confidence interval.

Both executables passed all 21 independent 1 GiB reference-parity cases before
measurement. All four reports verified full 1 GiB backing and zero allocation
failures. The exact reports, timing measurements and hashes are retained in
`9355p/` and [summary.json](summary.json). The headline uses the new pair's mean;
the older 68.26 H/s page-size experiment and its power measurements remain
separate historical results. The replacement rental was deleted after collection.
