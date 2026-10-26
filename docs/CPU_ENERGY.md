# CPU package energy experiments

`scripts/bench_cpu_energy.py` records Linux powercap package-energy counters and
compares fixed-worker CPU benchmark invocations. It reads counters and current
power/frequency settings. It never resets counters, reserves pages, changes a
governor or power limit, or queries a GPU.

The WSL development host exposes no package counters (rechecked 2026-10-25).
An empty probe is an availability result,
not zero power consumption. The tool refuses to launch a benchmark without
usable counters.

## Measurement contract

The metric is **whole-invocation package joules per reported completed hash**.
The counter interval brackets process launch and exit, including allocation,
startup probes, reported work, fences, and teardown. Warmup rounds are disabled
so an extra unreported warmup workload is not mixed into the denominator.
Hashes completed during the fence are counted. Unreported startup work remains
part of invocation overhead. This is not steady-state kernel energy per hash.

Package counters include other processes running on those packages. They do
not establish wall-plug consumption or separately unmeasured DRAM energy.
Use a quiet dedicated host and long samples; short runs are only plumbing
checks. Compare equal durations and round counts. Do not translate this metric
into a production electricity saving without a sustained mining measurement.

The Linux [powercap interface](https://www.kernel.org/doc/html/latest/power/powercap/powercap.html)
reports accumulated microjoules and a counter range. Package domains are summed;
core/uncore child domains are excluded to avoid double counting. Duplicate
drivers exposing the same package require explicit `--zone` selection, with one
source for every available package so a second socket cannot be silently omitted. Raw
timestamped samples are retained. A conservative `--max-domain-watts` bound
rejects sampling gaps that could hide multiple counter wraps and increments
inconsistent with that bound. Do not reset counters during a run; a reset whose
apparent increment is physically plausible cannot be distinguished from a wrap.

## Capture a point

```bash
python3 -B scripts/bench_cpu_energy.py probe
python3 -B scripts/bench_cpu_energy.py run \
  --binary target/release/seine --threads 8 --kernel avx2 \
  --page-mode large --seconds 60 --rounds 3 \
  --label current-power-policy --output-dir data/energy/a1
```

The tool checks available host/cgroup RAM and required huge-page pools before
launch. It validates actual arena backing, fixed worker/kernel settings,
completed-hash accounting and zero backend error counters. Changed power or
frequency policies, swap/OOM activity, modified binaries, missing counters and
partial benchmark reports reject the measurement. Timeout, Ctrl-C and SIGTERM
stop only the process group launched by the tool and retain a failed record.

The default timeout is 600 seconds; increase it for longer experiments. The
default 1000-watt bound applies to each measured package, not the whole host;
use a conservative physical bound appropriate to the machine. This option
does not set or modify a power limit. `--zone` takes a package-zone path from
`probe`, for example `/sys/class/powercap/intel-rapl:0`.

Each output directory is new and contains `energy.json`, `bench.json`, stdout
and stderr. The record preserves the binary/report checksums, raw energy
samples, domain identities and before/after CPU settings.

## Compare workers or a supported power setting

First find the useful worker-count plateau. Keep the binary, kernel, page
backing, affinity and host fixed, and compare neighboring worker counts. For a
power-limit experiment, keep worker count fixed and arrange the supported power
setting outside this tool, recording and restoring the original setting.

Run at least three interleaved pairs in A/B, B/A, A/B order, allowing the same
thermal settling time between legs. Use separate directories for every leg.
The comparison consumes those pairs in matching order:

```bash
python3 -B scripts/bench_cpu_energy.py compare \
  --baseline data/energy/a1 data/energy/a2 data/energy/a3 \
  --candidate data/energy/b1 data/energy/b2 data/energy/b3 \
  --output data/energy/comparison.json
```

It re-derives energy from raw samples, verifies benchmark checksums, rejects
incompatible configurations and reports paired changes with bootstrap
intervals for joules/hash, completed hashes/second and package watts. Lower
joules/hash is preferable; lower watts alone does not establish better mining
efficiency. Pair order and host exclusivity remain the runner's responsibility.
The same host/boot, binary, kernel, page mode, affinity and allowed CPU mask must
hold across every pair. Differences in worker count and recorded power settings
are allowed; kernel/page/affinity changes require separate experiments.

## Automate a worker-count sweep

The `sweep` command runs each challenger next to its own baseline, alternating
A/B and B/A order across pairs and rotating challengers. It settles before every
invocation, including the first. It keeps the same binary, kernel, page mode,
CPU mask and power policies throughout, and stops if those conditions change.
Every sample uses the same whole-invocation measurement contract described above.

Example for a qualified 32-core EPYC host, after establishing kernel correctness
and reserving enough explicit pages for 32 workers:

```bash
python3 -B scripts/bench_cpu_energy.py sweep \
  --binary target/release/seine --kernel avx512-256-stream \
  --threads 8 16 24 32 --baseline-threads 24 \
  --page-mode large --seconds 60 --rounds 1 --pairs 4 \
  --settle-secs 10 --max-seconds 2400 --retain-throughput .95 \
  --label epyc-stock-power --output-dir data/energy/epyc-workers
```

This schedules 24 invocations: 24 minutes of configured work plus four minutes
of settling, allocation, probes, fences and teardown. The 40-minute campaign
budget bounds measurement execution; it does not terminate a rental or cap
provider billing. `--timeout` bounds each invocation separately. Interruption
stops the owned child, preserves completed and partial samples, and marks the
campaign failed. Use a new output directory for a retry; evidence is never
overwritten. No summary is produced for incomplete campaigns.

`sweep.json` records the schedule and completed legs. Each leg contains the
usual raw samples, benchmark report and logs. `summary.json` rechecks those
observations and includes paired bootstrap comparisons against the baseline,
pooled completed H/s, package watts, joules/hash, hashes/joule and variability.
The observed frontier contains points where no other tested count achieves both
at least as much throughput and at most as many joules/hash, with one strict
improvement. The shortlist minimizes joules/hash among counts retaining the
requested fraction of observed peak throughput. The baseline has more samples
because it is repeated beside every challenger.

This is an exploratory shortlist, **not a confirmed efficiency winner**. Repeat
the shortlist versus peak-throughput count with fresh alternating pairs and
longer windows before making a recommendation. Power-limit experiments remain
separate: change only one supported setting outside the harness, preserve the
original setting, and use `compare` to analyze the resulting paired samples.
The harness does not change mining defaults or tune package power itself.

For AMD research, `--kernel avx512-256-stream` explicitly selects the streaming
variant; the miner still checks ISA support. Run separate sweeps for different
kernels. `auto` uses the benchmark's selected kernel and does not reproduce the
productive mining tuner's joint count/kernel search. Check that zero-config
mining chooses well as a separate experiment after measuring the hardware.

The current hardware qualification and rental sequence is in
[AMD CPU efficiency campaign](AMD_CPU_EFFICIENCY.md).
