# Fresh CPU trial placement observations — October 26, 2026

Scope: schema-6 CPU-kernel trial context. No hashing kernel, tuning acceptance,
startup/cache policy, throughput default or efficiency opt-in behavior changes.
Worker-count/joint producers and measured switching/idle costs remain separate work.
This source change does not deploy the collector or release a miner.

## Observations and limits

- Linux reuses the existing NUMA/physical-core/L3 parser, requiring complete L3
  evidence instead of accepting its runtime placement fallback. Current controller
  thread CPU and memory masks are checked before/after the metadata read.
- Windows uses the current process CPU mask and complete physical-core/NUMA/L3
  partitions. Multiple processor groups remain unknown. Both platform paths hash
  only typed topology/mask inputs with SHA3-256, not Config, host identity or paths.
- The digest describes allowed topology inputs; it does not establish actual
  per-worker residency. OS/environment, requested affinity, allocator-observed
  backing, resource limits and source identity remain separate cohort inputs.
- Trial start and active controller ticks use fresh observations; no startup
  cache is substituted. Idle tuners do no metadata reads. A change observed inside
  or between windows remains latched through final acknowledgment, even if the
  original context returns. Gaps over three seconds disqualify the observations.
  Changes entirely between observations cannot be detected.
- Unsupported OSes, incomplete/inconsistent topology and masks over 512 CPUs stay
  unknown. Windows topology buffers are capped at 1 MiB. A read over 25 ms is
  discarded and produces 30 seconds of unknown context without another read.
  This is backoff, not a hard OS-call timeout: the first slow read can exceed it.
- Worker-observed opt-out or worker exit disables further probes and empties the
  trial queue. The existing preference polling interval still applies. No new
  background polling thread or network call was added to tuning control.

Twenty metadata-only observations on the development machine (no mining/GPU work):

| Environment | Complete reads | Median | p95 | Maximum |
|---|---:|---:|---:|---:|
| WSL Linux | 20/20 | 4.346 ms | 4.874 ms | 5.633 ms |
| Native Windows | 20/20 | 0.157 ms | 0.249 ms | 45.469 ms |

The Windows cold outlier would be discarded and trigger backoff in the production
sampler. Measurements exercised the raw probe to expose this outlier. These are
small metadata timing samples, not mining throughput benchmarks or a fleet-wide
latency guarantee. Large and unsupported hosts need separate coverage validation.

## Verification

- 119 adaptive controller tests passed; three existing real-arena/mining tests
  remained ignored. Existing producer tests inject an unknown placement provider
  so host metadata cannot influence deterministic tuning tests.
- 13 Linux topology tests, three placement tests and 11 recorder tests passed.
  New tests cover strict completeness, same-count mask changes, temporary unknowns,
  changes between windows, missed observations, acknowledgment, slow-read backoff,
  idle suppression, opt-out/exit and queued-evidence disposal.
- Cross-built the CPU-only Windows test binary and ran all nine placement/monitor
  tests natively on Windows. No GPU or proof-of-work benchmark was launched.
- Workspace/all-target check with `seine-telemetry/server,amd` passed.
- 22 SQL tests and seven agent-report tests passed. Collector package tests and
  schema 1–6 HTTP integration checks passed against disposable PostgreSQL 16.
- A full report produced by `Monitor` using synthetic counters/placement was sent
  through the real collector. Five synthetic installations qualified one 10% gain
  research hint; changed/unknown samples were accepted as coverage but excluded
  from qualified comparisons. Idle cost remained null and automatic-default
  eligibility remained false. This validates plumbing, not a measured speedup.

Reproduce runtime artifact generation:

```sh
SEINE_TRIAL_TEST_OUTPUT=/tmp/seine-measured-trial-fixture.json \
  cargo +1.93.0 test --bin seine --no-default-features \
  fresh_known_context_survives_real_report_contract_without_changing_decision
```

With the local collector running against a disposable database (never production),
run the existing integration suite plus the generated runtime contract:

```sh
TELEMETRY_TEST_URL=http://127.0.0.1:9080 \
TELEMETRY_TEST_DATABASE='host=/path/to/disposable-pg-socket port=55448 dbname=postgres' \
TELEMETRY_TEST_TRIAL_FIXTURE=/tmp/seine-measured-trial-fixture.json \
  python3 telemetry/test_integration.py
```

## Showcase and rollout

Reviewed desktop/mobile full-page captures reflect supported placement contexts.
The 14 existing control-state crops remain applicable; no controls changed.
Stable gallery: `/home/zp/Code/blocknet/showcases/seine-paired-trial-telemetry/index.html`.
From the workspace root, serve it with:

```sh
python3 -m http.server 9081 --directory showcases/seine-paired-trial-telemetry
```

Open <http://localhost:9081>. Fixture server and task browser tabs were closed.
The captured page's unrelated browser extension error did not affect the fixture.
Collector schema 6 must deploy before the next schema-6 miner release. See the
[production runbook](../../telemetry/deploy/PRODUCTION.md); no deployment, restart,
release, production fixture upload or Discord message was performed here.
