# CPU usage and fee stages — October 26, 2026

## Intent and scope

- `miner-cpu-usage` owns the diagnostic sequence for an OS utilization reading.
  Existing automatic-tuning, RAM, benchmark and dashboard guides retain their
  implementation, capacity, measurement and interface detail.
- `mining-pool-fees-vs-miner-fees` owns the two fee stages and input provenance.
  Existing calculator and PPLNS guides retain estimation and allocation detail.
  The owner explicitly approved this fee topic in the current article batch.
- No hardware rental, mining, GPU workload, competitor comparison or new measured
  performance claim. The diagrams are explanatory, not benchmark charts.

## Primary sources

Public release v0.2.36, published October 26 at 11:34:54 AM EDT, resolves to
`f3c8175eac0e01cd31870372b2c4989a598044d3`. The live release check passed.
The guides describe that version, not concurrent unreleased optimization work.

- `seine@v0.2.36:docs/MINER_FLAGS.md`, `src/config.rs`,
  `src/miner/adaptive_cpu.rs`: CPU backend selection, explicit thread settings,
  measured automatic choices, cache, memory availability and pressure. Each
  active CPU mining thread needs a 2 GiB arena; installed RAM is not a promise
  of that many simultaneous allocations. Profiles and limits affect selection.
- `src/miner/mining.rs`: supporting networking/control/reporting tasks are not
  all active CPU hashing threads. Compare a device row, not combined GPU/CPU H/s.
- https://learn.microsoft.com/en-us/troubleshoot/windows-server/support-tools/support-tools-task-manager
  Process and machine scope, Performance CPU and logical-processor graphs.
- https://man7.org/linux/man-pages/man1/top.1.html
  procps top Irix/Solaris CPU scaling and thread display. A process can exceed
  100% in Irix mode; Solaris divides by processor count. Scale changes do not
  establish mining speed changes. No screenshots or prose are reproduced.
- Memory capacity and bandwidth are distinct. A thread may count as busy while
  waiting on memory; low utilization alone does not prove a bandwidth limit.
- `seine@v0.2.36:src/dev_fee.rs`, `docs/guides/configuration.md:90–93`,
  `src/miner/mining.rs`: 2% development mining-time policy across pools and solo,
  first 10 minutes excluded from billed time, round-based scheduling. This is
  work to the developer address, not a later withdrawal from a user's wallet.
  Short windows need not equal exactly 2%; the arithmetic example is steady-state.
- https://github.com/zpalmtree/seine/blob/v0.2.36/docs/guides/configuration.md
- https://bntpool.com/api/info checked October 26: pool_fee_pct=0.0,
  min_payout_amount=0.1, blocks_before_payout=60. These are dated observations.
- `blocknet-pool@e4572ca2d64173fbc4d7af9d170a572876e6d7c2:crates/pool-runtime/src/payout.rs:662–735`:
  calculate fee from recorded block reward, then allocate the distributable
  remainder through PPLNS. Confirmation, payout threshold and transaction fees
  are distinct; no unverified transaction-fee amount is stated.
- `frontend/blog/rewards-math.js:47–57`, `frontend/scripts/rewards-calculator.mjs`:
  retained fraction (1 - minerFee/100) * (1 - poolFee/100). Pool-reported address
  hashrate can already reflect developer time; zeroing that additional calculator
  adjustment avoids duplicate deduction and does not change software policy.
  Confirmed balances/payments are accounting results, not gross estimate inputs.
- Hypothetical 100 BNT × 0.98 × 1.00 = 98 BNT is arithmetic, not a hardware
  result, payout promise, profitability claim or short-session grace simulation.

## Graphics, translations and verification

Original CPU diagram separates an activity grid from a completed-work counter.
The pool cover depicts miner-time and pool-reward adjustments with symbolic
factors. Existing article-list layouts are retained. Both have localized text
descriptions; no invented dashboard screenshots are used.

The active model wrote English and 19 translations per article without subagents
or external translation services. Translation metadata remains `draft` because
there was no independent linguistic review. The owner's optional-review policy
applies. Strict checks pass, all inline literals and source links match, and
English eight-word phrase overlap with existing posts is 0.0%.

Seine's 5 tests and the pool frontend's 21 tests pass. Final build revisions,
Windows shared-Chrome desktop/mobile captures, metadata/link/image/sitemap
audits and production service evidence are recorded in the stable showcase:
http://localhost:8874/cpu-usage-and-fees/

Publication uses the normal Seine site pipeline and pool `--api-only` deployment.
Before/after identities check that Stratum, monitor and recovery remain running.
