# Benchmarking and confirmations — October 26, 2026

## Intent and boundaries

- `benchmark-seine-miner`: repeatable local measurements, warmup, saved JSON,
  paired comparisons and matching measurement scopes. Existing setup, RAM,
  huge-pages, hardware-result and autotuning guides retain their separate intent.
- `block-confirmations-mining-rewards`: depth, maturity, identity checks and the
  distinction between a block reward, account balance and payment transaction.
  Existing PPLNS, difficulty, luck and tracking guides retain detailed ownership.
- No mining, GPU jobs, hardware rentals, new performance measurements or competitor
  comparisons were needed. Shell examples were source-checked, not executed.

## Primary evidence

Public seine release verified against GitHub: v0.2.36, published October 26, 2026
at 11:34:54 AM EDT, commit `f3c8175eac0e01cd31870372b2c4989a598044d3`.
The guide documents that release, not unreleased tuning work.

- `seine@v0.2.36:docs/MINER_FLAGS.md:148–157`, `src/config.rs:700–740`:
  local --bench, modes, duration, measured rounds, warmup rounds, JSON output
  and baseline compatibility options.
- `src/miner/bench.rs`: Bench runtime preparation, warmup exclusion, actual
  elapsed-time accounting, report configuration/environment and avg_hps,
  median_hps, min_hps, max_hps, runs. A requested interval is not total runtime.
- `docs/PERFORMANCE.md`, `docs/benchmarks.md`: offline CPU example, paired
  measurements, cache policy, mode semantics and full environment records.
- https://github.com/zpalmtree/seine/blob/v0.2.36/docs/MINER_FLAGS.md
- https://github.com/zpalmtree/seine/blob/v0.2.36/docs/benchmarks.md
- `blocknet-pool@b002c96:crates/pool-runtime/src/payout.rs:605–668`:
  depth = current_height.saturating_sub(block.height); verify the recorded
  block hash against the node; mark confirmed only when depth is sufficient
  and identity matches. Orphan handling is separate; no instantaneous orphan
  detection claim is made.
- https://github.com/zpalmtree/blocknet-pool/blob/b002c96/crates/pool-runtime/src/payout.rs
- https://bntpool.com/api/info checked October 26: blocks_before_payout=60,
  min_payout_amount=0.1. These are dated observations, not immutable promises.
- `blocknet-core@c646196a2a7ae69c4a9b35f2489fbb7192e41d2f:block.go`:
  300-second target; `wallet/wallet.go:720–744`: wallet CoinbaseMaturity=60
  with currentHeight - output.BlockHeight. The article describes the wallet
  rule and does not claim a separate consensus-enforcement audit.
- A newly found block is depth zero under the pool's calculation. The example
  70,000 / 70,001 / 70,060 is illustrative, not a live block record. Five hours
  is target arithmetic, not a deadline.
- Payment transaction confirmation/spendability is separate from pool block
  maturity. No unverified live payout interval or regular-output rule is claimed.
- `frontend/src/pages/BlocksPage.tsx`: displayed height, hash link and status.
  The article does not claim a live depth counter exists in that page.

## Graphics and translations

Original benchmark SVG shows warmup, three measured rounds, report storage and
paired A/B order. Original pool cover shows depth 0, 1, …, 60, then accounting
and a separate payment. Both are explanatory diagrams, not measured charts or
fabricated screenshots. Existing blog list layouts are retained.

The active model authored English plus 19 translations for each article.
Translation metadata remains `draft`; independent linguistic review is optional
and is not claimed. Code blocks and inline literals match the source exactly.

## Verification and publication

Strict checks pass for both complete language sets. English eight-word phrase
overlap is 0.0% with existing articles. Seine's 5 tests and the pool frontend's
21 tests pass. The public-release live check confirms v0.2.36.

Build results, real shared Windows Chrome desktop/mobile captures, final revisions
and live verification are recorded in the stable showcase:
http://localhost:8874/benchmarks-and-confirmations/

Pool publication uses `--api-only`; before/after service identities verify that
Stratum, monitor and recovery stay running. This batch does not change miner
runtime code or upgrade running miners.

