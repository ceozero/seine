# Paired trial telemetry validation — October 26, 2026

Schema 6 adds a shared typed CPU trial outcome, bounded nonblocking recorder,
strict collector ingestion and per-installation paired research screening. The
runtime producer hooks are staged; tuner integration and a miner release are
needed before fleet trials arrive. No collector deployment or release was made.

## Checks

After rebasing onto master `3d2755c`:

- `cargo test --bin seine --no-default-features hardware_telemetry`: 10 tests.
- `cargo test -p seine-telemetry --features server`: 10 schema tests and one server test.
- From `telemetry/`, `python3 -m unittest test_agent_report test_alerts test_alerts_sql test_diagnostics_sql test_performance_sql test_tuning_sql`: 38 tests.
- `cargo check --workspace --all-targets --features seine-telemetry/server,amd`.
- `git diff --check`.

The SQL tests create and remove disposable PostgreSQL 16 databases. They check
short-window coverage, deduplication and conflicting IDs, one vote per installation,
actual arm/context matching, unknown context, drift and minimum sample rejection,
inconclusive/aborted/no-confirmed-gain coverage, exact source/environment/policy
cohorts, version provenance and unknown-cost measurement coverage. No GPU workloads
or hardware performance claims are part of this change.

The real HTTP integration script ran against a local built collector and a separate
disposable PostgreSQL database with `TELEMETRY_TEST_DATABASE` set. It verified
schemas 1–6, successful paired raw-sample/policy persistence, analysis, strict
private-field and downgrade rejection, rate limiting and body limits. It is a
standalone integration script, not a unittest discovery module. The collector
and database were stopped and removed afterward.

## Browser showcase

Stable gallery path:
`/home/zp/Code/blocknet/showcases/seine-paired-trial-telemetry/index.html`.
From the workspace root:

```sh
python3 -m http.server 9081 --directory showcases/seine-paired-trial-telemetry
```

Open <http://localhost:9081>. Sixteen screenshots cover disabled, ready, loading,
success, invalid-field, empty-payload, rate-limit and unavailable states at desktop
1280×1000 and mobile 390×844 viewport sizes. Captures use the configured Windows
Chrome Playwright MCP, synthetic fixtures and the real local collector. Loading
holds the real request until capture; unavailable stops the collector. All images
were reviewed. Source is labelled `3e00b81` plus this change; the later rebase did
not change showcase code. The only browser console error came from an unrelated
installed wallet extension. All task-owned tabs were closed and verified absent.

## Production evidence and rollout

Read-only `python3 telemetry/agent_report.py` at 1:40 PM EDT on October 26 returned
healthy HTTPS, database, retention, disk and backups. The paired SQL succeeded,
with zero trials and `unavailable` coverage as expected before producer rollout.
The overall briefing returned nonzero because existing inventory-only and miner
reliability alerts remain active; these are not collector health failures and
were not cleared by this change.

Deploy the rebuilt schema-6 collector and updated SQL/scripts before releasing
schema-6 miners. It accepts older schemas without a database migration or a pool/
daemon restart. Runtime integration must record actual measured context and costs,
not reconstruct desired settings. Research hints require matching native validation
and independently verified host evidence; none is eligible as an automatic default.

## Alternative window policy follow-up

Runtime integration identified an acceptance rule that is an OR of two complete
duration/hash pairs: 10 seconds/256 hashes or 30 seconds/32 hashes. Added optional
paired `short_sample_ms` / `short_minimum_hashes` fields while preserving existing
single-rule schema-6 payloads. SQL now checks each window against either complete
rule, removing the unrelated 128-hash floor. Quantization and native validation
requirements remain; this is faithful policy evidence, not a weaker runtime rule.

Validated on master `30ece1c`: 11 schema tests, one server test, 10 hardware
recorder tests and seven paired SQL tests passed. The disposable real collector
integration also passed, including mixed 10-second/300-hash baseline and 30-second/
64-hash candidate windows and rejection of a partially specified alternative.
SQL tests reject crossed thresholds, insufficient hashes and insufficient time,
and keep distinct alternative policies in separate cohorts. The collector and
temporary database were cleaned up. No UI flow, deployment or release changed.
