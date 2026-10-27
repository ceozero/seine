# Hardware-specific tuning evidence roadmap

This tracks telemetry readiness, not authorization to deploy or release. The
runtime and benchmark work owns startup behavior and defaults; telemetry supplies
bounded observations and research priorities. There is no remote override path.

## Current state — October 26, 2026

| Capability | State | Practical limit |
|---|---|---|
| Schema 6, bounded FIFO/spooling, strict collector | Landed in `6efb85b`, alternative window rules in `d770a46` | Collector must deploy before schema-6 miners release. |
| Productive CPU kernel trial producer | Landed in `334b827`; fresh context added | Complete stable Linux / single-group Windows observations can qualify; unsupported or incomplete topology remains unknown. |
| Paired CPU-kernel cohort analysis | Landed; same-installation A/B/A, exact context, one installation per vote | Requires complete measured context and two resolved cycles for gain support. |
| Worker-count and joint producers | Pending | Their records remain coverage-only; objective and confirmation policy need explicit validation. |
| Switching/settling/no-job idle measurements | Typed contract exists; current producer leaves them unknown | Wall duration is available; it is not lost productive time. |
| Energy/efficiency evidence | Pending | No power measurements; cannot infer H/J or efficiency from worker count or RAM. |
| Fleet-derived candidate defaults | Not enabled | Hints need correctness, native benchmarks and independent-host confirmation before shipping. |

Read-only production health checks show whether collection is working separately
from miner reliability and sample quality. An empty paired report window is not
evidence of no gain; coverage-only records are not eligible benchmark comparisons.

## Next evidence gates

1. **Validate context coverage on matching hosts.** Fresh allowed-mask/NUMA/core/L3
   observations now cover supported Linux and single-group Windows. Keep unknowns
   on incomplete topology, slow reads or unsupported hosts; record overhead before
   broadening support. The digest measures topology inputs, not per-worker residency.
   Keep OS/native-vs-WSL, runtime ISA, exact CPU identity, page backing, resource
   limits, source/build and settings separate. See [validation](../docs/validation/trial-placement-20261026.md).
2. **Complete producer coverage.** Add worker-count and joint trials with actual
   settings per window, unsuccessful and incomplete outcomes, cache invalidation
   context, and the full acceptance/confirmation rule. Encode throughput versus
   an explicitly selected efficiency objective before combining these policies.
3. **Measure tuning cost.** Separate counted productive windows, measured switching,
   settling and observed no-job idle, without double-counting. Keep unknown costs
   null and show measurement coverage. Retain failed attempts in cost summaries;
   do not report elapsed tuning time as an idle penalty.
4. **Validate hints on matching native hosts.** Fleet H/s does not choose winners.
   Use interleaved within-machine comparisons, hash parity, drift/resolution gates,
   independently verified hosts and a cold-start check. Repeated reports or reset
   installation IDs are not additional independent machines. Keep losing and
   inconclusive candidates visible in engineering evidence.
5. **Ship bounded local choices.** Intended behavior is immediate startup from a
   compatible cache or validated hardware hint, followed by bounded productive
   tuning when needed. Optimize repeatable H/s by default; efficiency is opt-in
   and requires its own measurements. A hint's hardware identity never bypasses
   runtime ISA/OS capability checks, resource limits or safe fallbacks.

The last step is a runtime requirement, not behavior implemented by SQL. Research
ranking is based on paired relative gains in an exact context; it cannot establish
the fastest absolute configuration across different baselines or hardware cohorts.

## Confidence policy

Ranked candidates need five qualified installations. A reported kernel gain must
have two resolved A/B/A cycles; each installation needs a majority of its observed
trials to support the gain. Cohorts get `observational_support` only with support
from at least 60% of all observed installations and an acknowledged, resolved gain
within 48 hours. Otherwise they are labelled `mixed_or_limited_evidence`. The seven-day
window, counts, outcome coverage, cost coverage, spread and source provenance are
retained so this label is reviewable. It is not a statistical confidence interval
or a guarantee that hosts are independent. All hints require native validation;
none is eligible for an automatic remote default.
