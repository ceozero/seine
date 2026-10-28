# EPYC 9375F cached-start memory accounting

On October 27, 2026, a one-change candidate based on v0.2.39 improved the
first three minutes after a cached restart by **5.71%** in two interleaved
pairs. This is a startup result on the tested configuration, not a sustained
hashrate claim or the separate [85.1 H/s manual headline](../9375f-headline-20261027/).

## Cause and change

The CPU controller starts after hash arenas have been allocated. Its initial
capacity observation used zero owned bytes, while later observations counted
those arenas. A large cached worker count therefore appeared to recover memory
capacity on the next tick. That recovery delayed kernel selection and began a
new worker-count probe before restoring the cached kernel.

The patch includes running backends' committed bytes in that first observation,
matching subsequent ticks. It changes no kernel, identity gate, tuning window,
pressure threshold, or cached score. Existing memory limits remain enforced.

## Protocol and results

Native Linux EPYC 9375F, 32 physical cores / 64 logical CPUs, 384 GiB host RAM.
The experiment intentionally used a **192 GiB MemoryMax cgroup**; it is not a
measurement of unconstrained startup on the full host. The 1 GiB page reservation
from the earlier manual benchmark was restored before this experiment.

An unprivileged miner ran against a loopback Stratum fixture in a private network
namespace, with an impossible target. There were no production shares or network
traffic. CPU thread count, kernel, page mode and profile used shipping defaults;
telemetry was off and progress was logged every five seconds. Automatic page mode
used THP. Memory samples show allocation/THP promotion during startup and full
THP arena backing later; this was not explicit HugeTLB allocation.

Each binary first ran for 300 seconds from its own empty data directory. Both
naturally saved a 48-worker starting point. Each cached run copied its binary's
entire natural cold directory into a fresh directory, without changing cache
identities, scores, or settings. Cached order was baseline/candidate/candidate/
baseline, 180 seconds per run. See the predeclared [protocol](protocol.md).

The metric is the last logged cumulative completed-hash count divided by elapsed
monotonic time around the whole invocation, including startup and shutdown. It is
a **lower bound**, because work after the final counter can be omitted. It is not
pool-credited work and is not interchangeable with the offline headline metric.

| Run | Logged hashes | Invocation seconds | H/s lower bound |
|---|---:|---:|---:|
| Cold baseline | 19,971 | 301.61719 | 66.21307 |
| Cold candidate | 20,019 | 302.41647 | 66.19679 |
| Cached baseline 1 | 12,465 | 180.66468 | 68.99522 |
| Cached candidate 2 | 13,176 | 180.71671 | 72.90969 |
| Cached candidate 3 | 13,192 | 180.71469 | 72.99905 |
| Cached baseline 4 | 12,464 | 180.56450 | 69.02797 |

Adjacent paired gains were **5.674% and 5.753%**; geometric mean **5.713%**.
Cold candidate/baseline was **0.999754** (-0.025%). Both cached gains exceed zero,
their geometric gain exceeds the predeclared 3% gate, and cold performance exceeds
97% of baseline. Two pairs and one cold pair do not establish a confidence
interval or portability to other machines.

Baseline started streaming at **62.0 / 61.1 seconds**, after an unnecessary
capacity-recovery path; candidate restored the confirmed streaming kernel at
**16.7 / 16.2 seconds**, immediately after allocation. Candidate naturally retained
64 workers by the end; baseline was checking 48 workers again. Cold selection
started streaming at 10.7 seconds on both binaries. All six runs exited cleanly,
with zero system swap/OOM counter deltas and no backend faults.

## Provenance, reproduction and cleanup

[candidate-inputs.json](candidate-inputs.json) records the exact base, patch and
binary SHA-256, build command and pre-rental tests. The baseline is the official
v0.2.39 Linux x86-64 release. The source patch is [candidate.patch](candidate.patch).
All 21 full-size streaming reference cases passed before the separate manual
benchmark; the candidate does not change hashing code.

[followup_measure.py](followup_measure.py) and [fixture.py](fixture.py) are the
executed runner and loopback fixture. On a disposable matching host, place the two
binaries in `/opt/seine-headline/{current,candidate}/seine`, install the scripts
there, create the unprivileged `seinebench` account, ensure the original 1 GiB page
reservation is zero, and run the script in a private-network systemd service with
`MemoryMax=192G`, `RuntimeMaxSec=1400` and that working directory. Bind the included `hosts` file over `/etc/hosts` in that service, as the campaign
did, to keep any fee-pool connection loopback-only; no public endpoint was used.

Measurement JSON, startup commands, logs, memory samples, natural CPU/kernel caches,
fixture events and [verified-result.json](verified-result.json) are retained here.
The fixture address and generated worker names are synthetic. Telemetry seed files
are excluded; no installation IDs or rental credentials are published. Published
file hashes and the original collection-manifest hash are in [manifest.json](manifest.json).

The final source passed 53 adaptive CPU, 66 configuration and 65 kernel-policy
unit tests. Three ignored native tests were not run on the development desktop;
the rental exercised the relevant startup behavior. [cleanup.json](cleanup.json)
confirms collection, restored page reservation, provider deletion, SSH-key removal
and stopped deletion watchdog at 5:45 a.m. EDT. No miner release was published.
