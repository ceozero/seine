# Reliability investigation — October 26, 2026

Read-only production briefings at 12:35 and 12:56 EDT found healthy collector,
database, retention, disk and backups. The supplied Discord alerts count
unfinished-run markers, not confirmed process crashes. No production services
were changed, no messages sent, and no release published during this investigation.

## Findings

| Evidence | Interpretation / action |
| --- | --- |
| v0.2.29 Linux EPYC 7C13, 117 requested workers, mandatory `large` pages: 117 failed 2 GiB allocations, `huge_pages_unavailable`, OS error 12, then no backend available | The explicit HugeTLB requirement could not be met. Ordinary reported free RAM (245 GiB) does not establish a suitable reserved huge-page pool. This is a startup/configuration failure; do not silently override mandatory page policy. |
| v0.2.29 Linux Threadripper 3990X, 8 workers: CPU startup failure classified as timeout, then no backend available | Existing reports lack readiness counts and an exact timeout origin. Do not change timeout defaults from this alone. New instrumentation identifies readiness timeout at its source and records ready/expected counts. |
| v0.2.29 Windows NVIDIA-only panic at unknown source line 21887 | Matches cudarc 0.19.2's eagerly loaded `cuEventElapsedTime_v2` symbol. The existing synthetic Windows/Linux loader reproduction is documented in `NVIDIA_OPTIMIZATION_LOG.md`; commit `5fd238d` selected CUDA 12.0 driver bindings, shipped in v0.2.31. No new kernel or ABI change is warranted here. |
| v0.2.29 Linux NVIDIA-requesting configurations panic at unknown source line 181 | Matches cudarc 0.19.2 `panic_no_lib_found`. Missing/unloadable CUDA driver or NVRTC library is a strong lead, not proven from a line number alone. Existing reports cannot distinguish which library or dependency was unavailable. New fixed dependency source IDs remove the filename ambiguity; raw panic contents stay excluded. |
| v0.2.36 unclean marker on Linux Xeon Platinum 8582C | Previous build is `03e1434729ba` (v0.2.35), detected by restarting build `f3c8175eac0e` (v0.2.36). Original alert grouped by the restart release and misattributed this observation. |
| Three actual v0.2.36 previous-build observations | Windows Ryzen 7950X checkpoint at 10 s, Windows Xeon E5-2666 v3 at 240–300 s, Linux AMD EPYC at 831 s; all last saved in phase `mining`. No recorded current-run error/panic/quarantine for this version at the first briefing. Two show hashes in restart reports; the Ryzen report shows pool connection timeouts without hashes. None establishes the prior termination cause. |

v0.2.29 had four installations with unclean markers by 12:35 EDT (the screenshot
showed three earlier). Its error clusters and unclean clusters are separate evidence;
one cannot assume a startup failure caused every interrupted run on matching hardware.
The corrected 12:56 EDT query attributes three interrupted installations to v0.2.36,
with the upgraded Xeon counted under v0.2.35. Legacy checkpoints without a release
or an unambiguous observed build mapping remain explicitly unknown.

## Implemented collection changes

- Schema 5 retains the previous release and up to eight diagnostic groups in the
  existing five-second checkpoint. Panics/errors and typed causes take priority;
  truncation is explicit. Context survives normal report-window draining.
- The identity-bound sidecar is capped at 8 KiB, expires after 24 hours, and clears
  on clean shutdown/opt-out. Previous events are checked against previous uptime.
- Three fixed cudarc 0.19.2 source identifiers replace `unknown` for its library
  loader and driver/NVRTC generated bindings. No local path, message or backtrace
  crosses this boundary.
- CPU readiness timeout details include ready/expected workers. Runtime behavior,
  page policy, allocation limits, kernels and timeout defaults are unchanged.
- Analysis/alerts use the interrupted release, falling back to an unambiguous
  build mapping for schema-4 history. Restart versions remain visible separately.
  Recovered events are context only and cannot inflate current-run error counts.

Abrupt native aborts, OOM kills, forced stops and power loss still need affected-host
evidence for a definite cause. Checkpoints can lag and events after the last save
can be lost. No synchronous panic-hook disk/network operation was introduced.

## Validation

- Miner diagnostics, persistence/replay/opt-out, hardware telemetry and the actual
  CPU readiness-timeout path tested without starting hashing workers.
- Collector schema tests cover legacy schemas, downgrade rejection, private path
  rejection, prior-run timing, bounded payloads and readiness counts.
- Disposable PostgreSQL tests cover upgrade attribution, missing/ambiguous builds,
  explicit previous versions, installation weighting and recovered-event separation.
- Real disposable collector HTTP integration covers schemas 1–5, storage,
  throttling, strict rejection and diagnostic/performance separation.
- Workspace/all-target compilation checked with NVIDIA, AMD and collector features.
- Configured shared Windows Playwright MCP checked desktop 1280×1000 and mobile
  390×844. All 24 captures were inspected: disabled, ready, loading, success,
  invalid, empty, rate-limited, unavailable, upgrade/unknown alerts, reminder and
  clearing. Only synthetic data was used. Browser tab, collector and disposable
  database were cleaned up. An unrelated wallet browser extension logged an
  injection error; the showcase itself had no application console errors.

Showcase: <http://localhost:9081>. Start from a current Seine checkout with
`python3 telemetry/showcase/serve.py`; submission states need a disposable local
collector as described in `telemetry/README.md`. Alert payload previews need no
collector and send nothing. These are actual sender JSON, not native Discord renders.
Reviewed captures and source hashes are in workspace
`showcases/seine-telemetry-reliability/manifest.json` beside the PNGs; captures
identify base `3b0f277` plus the reliability working changes.

## Rollout requirement

Deploy the schema-5 collector and updated analysis/alert scripts before publishing
any miner built with this schema. Schemas 1–4 remain accepted; no database migration
or pool/daemon restart is needed. Collector-side attribution can improve historical
reports immediately; previous-release/event checkpoint fields require upgraded
miners and cannot be reconstructed retroactively. Deployment and miner release are
separate authorized operations, not part of landing this code.
