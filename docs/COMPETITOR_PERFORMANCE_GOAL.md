# Competitor performance optimization goal

Use this objective when continuing Seine performance work in a future session.
Read the repository's `AGENTS.md` first, then inspect the active campaign's
handoff, evidence and live jobs before choosing the next experiment. This is a
reusable objective, not a claim that the work is complete or authorization to
release, deploy or spend money beyond explicit campaign authorization.

Short goal to paste from the workspace root:

> Read and pursue `seine/docs/COMPETITOR_PERFORMANCE_GOAL.md`. Resume from current campaign evidence and live jobs; preserve existing budget limits and authorization.

The campaign begun on October 25, 2026 has an approved **$120 cumulative cap**,
including all spending so far. Its evidence and budget ledger are under the
workspace's `benchmark-evidence/longhorn-20261025/`; those local records are not
part of this repository. The cap belongs to that campaign, not each new session.

## Objective

Improve Seine to match or beat independently verified Longhorn and NTMminer performance across supported platforms. Prioritize AMD CPUs, then AMD GPUs. Maximize validated performance gains per hour of engineering and rental time.

Work in short, evidence-driven loops:
1. Identify the largest measured gap and a specific, testable cause.
2. Make the smallest change that tests that cause.
3. Run the shortest meaningful native baseline/candidate comparison.
4. Inspect correctness, actual useful throughput, tuning behavior and measurement noise.
5. Confirm promising changes, revise inconclusive experiments, and promptly abandon demonstrated regressions.

Use separate validation stages:
- Screen: targeted correctness checks and short paired measurements.
- Confirm: repeated, interleaved measurements only for promising or unresolved candidates.
- Integrate: relevant regression checks, then commit and push.
- Publish: reproducible comparisons with independent verification, confidence intervals and clearly stated scope.

Use the existing benchmark automation instead of building another orchestration system:
- For new compatible experiments, use `python3 scripts/benchctl.py campaign PLAN --output-dir DIR`, following `docs/benchmarks.md` and `docs/examples/bench-campaign-cpu.json`. Inspect the current implementation before relying on its decisions.
- Configure hardware-appropriate sample lengths, fixed phase budgets, separate frozen baseline/candidate binaries, correctness checks and independent confirmation evidence. The example's one-worker setup and numerical thresholds are examples, not universal policy.
- Reuse completed stages through supported resume/status operations. Preserve existing remote isolation, independent hash verification, rental deadlines and cleanup; the runner does not replace those safeguards.
- Do not migrate or restart active benchmarks merely to adopt the runner. An SSH observation timeout is not proof that a remote job stopped: inspect that original job before considering a restart.
- Distinguish an execution/correctness failure, a demonstrated regression, and insufficient evidence for a gain. A runner result labeled “rejected” because the confirmation lower bound missed a threshold may still be inconclusive. Inspect the interval and measured effect before discarding the hypothesis.
- Do not repeatedly resume or rerun until a candidate passes. When uncertainty warrants more work, create a separately recorded follow-up with a justified fixed budget and fresh evidence; retain earlier results and account for selection when making final claims.

Do not require the entire platform matrix or publication-quality benchmark suite for every edit. Do not schedule multi-hour confirmation batches by default. Explain what uncertainty each additional run will resolve, and use existing rentals efficiently within their deadlines.

Do not miss small or conditional gains:
- Classify results as promising, inconclusive or rejected.
- Never treat “not statistically significant” as proof of no benefit.
- Follow up when measurement noise could hide a worthwhile gain.
- Investigate interactions between successful changes.
- Preserve gains limited to particular hardware, operating systems, memory configurations or worker counts through appropriately scoped automatic selection.
- Maintain a ranked experiment backlog and revisit deferred hypotheses when new evidence changes their value.

Start mining immediately from the best trustworthy local cache or validated hardware default, then continue productive autotuning when needed. Highest hashrate remains the default objective; efficiency modes are opt-in.

Freeze binaries within each comparison. Preserve exact revisions, commands, hardware details, raw logs and JSON/CSV, including failed experiments. Finish each predeclared comparison; adapt the next experiment rather than cherry-picking favorable samples. Separate startup, sustained, fee-adjusted and energy results.

Keep the full platform coverage matrix and competitor inventory current, but prioritize work that can change the next implementation decision. Avoid repeated status checks, inventory refreshes, documentation churn or infrastructure work without a concrete need.

Independently verify correctness before landing changes and verify published throughput claims. Update README/site evidence when a confirmed result materially changes them. Push finished work without accumulating unlanded improvements. For this campaign, the user has authorized creating and publishing new releases for validated gains. Batch several validated improvements into fewer releases; continue landing finished work, but do not publish a release for every small gain. Never mention competitors in release notes: describe Seine improvements and supported hardware only. Production deployments still require explicit authorization.

Remain within the explicitly approved cumulative budget for the active campaign, including spending already incurred. Reusing this goal does not authorize a new rental budget: obtain fresh authorization for a new campaign or a higher cap. Terminate rentals promptly and preserve all existing isolation and host-restoration requirements. Report remaining gaps and unavailable platforms honestly. Do not declare completion while required coverage or reproducible performance deficits remain unresolved.
