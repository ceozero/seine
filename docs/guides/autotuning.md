# How automatic tuning works

Seine starts mining immediately and keeps tuning while it works: it compares thread
counts and CPU kernels using real mining work, and backs off when RAM gets tight.
Nothing here needs configuring; this page explains what it does.

`--disable-cpu-autotune-threads` turns off both thread and kernel tuning, and an
explicit `--threads` count keeps the default kernel unless tuning is requested.

## Thread count

CPU autotuning during mining starts from a compatible cached count, limited by
current RAM, or an initial estimate of half the automatic capacity. Mining begins
without an offline thread-count sweep. The miner then compares settings using
real mining work: baseline, candidate, and baseline again. Every arena completes
one hash before its measurement window starts. Windows last at least 30 seconds
(or five times `--cpu-autotune-secs`) and collect at least 20 completed hashes.
Brief gaps between jobs remain part of measured wall time. Sustained work loss,
changing RAM limits, or substantial baseline drift discard the comparison.
Balanced/efficiency profiles retain their 99%/75% peak floors;
upward changes additionally require a gain above a conservative noise margin.
After exploring the peak, a lower count that meets the profile's floor stays
selected between probes. New peak measurements can extend exploration without
repeatedly committing higher counts that are already known to be unnecessary.

## CPU kernels

On CPUs supporting both AVX2 and AVX-512, automatic mining tuning also compares
those paths at the current worker count. On AArch64 with runtime SHA3 support,
it compares baseline NEON with `neon-sha3`, which combines XOR/rotate instructions
and 64-byte prefetch coverage. Startup keeps the existing portable NEON path.
Two baseline/candidate/baseline cycles
must confirm a gain above 2% plus the hash-count uncertainty before changing the
path. Kernel and thread-count trials run in turn; memory-pressure handling remains
active throughout. Kernel windows last 30–60 seconds and require 32 hashes, with
a ten-minute limit for each trial. Interrupted or noisy trials retain the previous
path. Workers switch between complete hashes without reallocating their arenas.

On validated Zen 5 EPYC processors (AMD family 26, model 2), tuning also compares
`avx512-256-stream`: a 256-bit AVX-512 kernel that keeps recent blocks cached and
streams outputs into the normal 2 GiB arena. It requires AVX2 and AVX-512F/VL.
Every eligible path is considered before caching the result; slower paths are
rejected using the same repeated comparisons. No worker-count cutoff forces
this kernel. A 24-worker EPYC 9R45 test improved 27.78% over AVX2, while the
one-worker screen regressed 3.53%, so selection remains specific to the measured
worker count and memory backing. Other CPU families retain their existing
automatic candidates. See the [integrated validation report](../../experiments/epyc-investigation/INTEGRATED_VALIDATION.md)
for native comparisons and automatic-selection evidence.

## Cached choices

Confirmed kernel choices are cached alongside the thread cache in
`seine.cpu-autotune.json.kernels.json`, keyed by worker counts, observed page
backing, CPU/build identity, eligible kernels, placement and tuning settings. Known contexts reuse
that choice; stable contexts are reconsidered after 30 minutes. Experimental
`avx512-256` remains benchmark-only. AVX2-only CPUs and ARM hosts without SHA3
keep their existing paths. No extra configuration is needed: `--disable-cpu-autotune-threads` disables
both automatic count and kernel tuning, and explicit fixed thread counts retain
the default ISA unless autotuning is explicitly enabled.

## Memory pressure and recovery

Available RAM is checked once per second. Workers finish their current hash before
parking and releasing their arenas and reference tables. Linux budgets honor nested
cgroup limits, including `memory.high`, and credit clean inactive file cache that
can be reclaimed. Linux pressure checks prefer the miner's own cgroup so unrelated
host stalls do not cause false reductions. Sustained memory stalls or Windows
low-memory notifications reduce the operating count when arena headroom is also
tight; brief reclaim spikes do not force a reduction.
The CPU backend can pause at zero workers when no complete arena fits, then retry
after 30 seconds of sustained headroom. Released Linux HugeTLB arenas return to the
reserved hugepage pool; the miner does not resize that OS pool. Parked worker slots
follow the CPU and configured worker ceiling, with a startup cap for Linux
cgroup-v2 task limits that leaves room for control and networking threads. If
automatic worker creation still runs out of resources, startup cleans up and
retries with fewer slots; explicit fixed counts report failure instead. The nonce
stride remains fixed. Raising a RAM limit can activate more provisioned workers;
raising a task limit requires restarting to provision additional slots. A task
budget too small for the CPU and supporting threads reports a startup error.
Only active arenas count against the refreshed memory allowance. Returning capacity
and sustained throughput changes prompt new probes. Stable settings are revisited
periodically; failed allocation attempts back off for five minutes.

## What tuning never interrupts

Tuning does not reconnect to the pool or restart GPU backends. Surviving CPU
workers keep their arenas; parked lanes retain their nonce positions and resume
within the same disjoint nonce allocation. Manual thread changes disable automatic
adjustment for that run. The tuner preserves a previously learned higher count when
a later run is temporarily limited by RAM or worker slots. Cache schema 10 records remain usable
as starting points; schema 11 also stores measurements and the resource-limit flag.
Hardware, build, affinity/topology, and page-mode mismatches discard the seed.

## Offline benchmarks

Offline `--bench` runs retain the warmed kernel autotune sweep and finalist
confirmation. Their measurements are kept distinct from productive mining samples.
Live tuning improves its estimate over time; it does not guarantee the global
optimum immediately on an unfamiliar machine.

See also [large servers](large-servers.md) for CPU placement and memory headroom, and the
[performance results](../PERFORMANCE.md) for measured kernel comparisons.
