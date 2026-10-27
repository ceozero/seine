# Trial telemetry contract review and confidence — October 26, 2026

Reviewed the kernel-producer worktree read-only while the runtime owner completed
it. Kernel producer `334b827` is now landed; this review does not deploy or release
it. Runtime files were not edited in this task.

## Findings and disposition

- **Missing measured context:** the producer deliberately leaves allowed CPU mask
  count and topology/placement fingerprint unknown. All current producer records
  are coverage-only under the analysis contract. Preserve this constraint until
  measured context is available. Worker-count/joint producers and measured
  switching/settling/idle costs remain pending.
- **Partial switch failures:** a failure after changing another CPU backend could
  report the pre-switch settings as applied. The runtime owner fixed this with a
  fresh all-backend snapshot while holding pending acknowledgment, and added a
  two-backend regression. Inspected the landed `abort_observed` path.
- **Confirmation hidden by an average:** a strong first A/B/A cycle and a failed
  second cycle could previously contribute gain support through their median.
  The analysis now requires two separately resolved cycles, a reported gain and
  acknowledged candidate settings. Positive ratios remain descriptive data.
- **Success-only coverage/costs:** confidence now includes unsuccessful trials in
  per-installation and per-cohort denominators, and nested cost summaries include
  all outcomes. Unknown measurements are not zeros. Recent losses cannot refresh
  the last confirmed-gain timestamp.

CPU-list slot mapping, OR window rules, Turin resolution rules, run-relative
whole-second timing, strict schema boundaries, failed/inconclusive retention and
unknown costs match the inspected producer contract. No further blocker was
identified in the inspected kernel-producer diff. This is not independent native
performance validation or approval of worker/joint producer designs.

## Verification

The Python telemetry suites run with disposable PostgreSQL 16 databases:

```sh
cd telemetry
python3 -m unittest test_agent_report test_alerts test_alerts_sql test_diagnostics_sql test_performance_sql test_tuning_sql
```

Coverage includes two-cycle confirmation, pending acknowledgment, failure-heavy
installations/cohorts, all-outcome cost medians, stale gain evidence, explicit
missing-context/staged-kind counts, duplicate/conflicting trial IDs, policy
alternatives and legacy reporting/alert behavior. There are 43 tests. No Rust or
collector schema changes were made in this follow-up.

The updated SQL also ran read-only against production at 2:08 PM EDT: collection
health was good, paired queries succeeded and returned zero trials. Existing
sample-quality/reliability incidents keep the whole briefing nonzero; an empty
paired window does not indicate no gain or a query failure.

Updated the existing showcase's stale producer-status text and replaced its
desktop/mobile full-page captures using the configured Windows Chrome MCP at
2:09 PM EDT. Both were reviewed. The other 14 collector-control captures remain
valid because those controls are unchanged; the manifest preserves their earlier
source and time. All task-owned tabs and the fixture server were closed. The only
console error was from an unrelated wallet extension.

Stable gallery: `/home/zp/Code/blocknet/showcases/seine-paired-trial-telemetry/index.html`.
Serve from the workspace root with
`python3 -m http.server 9081 --directory showcases/seine-paired-trial-telemetry`,
then open <http://localhost:9081>.

See [the roadmap](../../telemetry/ROADMAP.md) for remaining evidence gates and the
distinction between throughput defaults, opt-in efficiency and research hints.
