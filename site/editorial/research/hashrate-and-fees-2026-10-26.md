# Falling hashrate and transaction fees — October 26, 2026

The user approved the running-miner diagnostic article, then explicitly asked for broader Blocknet coverage and selected a transaction-fee explainer. Both publish on seineminer.com in English and 19 translations, with original diagrams and the established list layout. One translation subagent; no separate reviewer. Translation status remains draft. No hardware rental, mining, GPU probes, wallet transaction, daemon change or pool restart is part of this batch.

## Distinct reader tasks

- `mining-hashrate-dropping`: locate a sustained change in a still-running session by comparing the same field, time window and device before checking resources. CPU usage owns OS utilization; stopping owns process/backend failure; benchmarks own the harness; bntpool's hashrate guide owns units and share-estimation fundamentals. This adds a sequential decision path and a matched observation record, not another setup or benchmark guide.
- `blocknet-transaction-fees`: understand size-based estimation and review amount, fee and change before confirming a send. Wallet setup owns creation/restoration; payment links own URI fields; mining fees belong to bntpool. This owns transaction input/change arithmetic and CLI preview semantics. Fees were explicitly requested, overriding the house preference not to volunteer fee topics.

English prose passes strict checks with no warnings. Eight-word overlap is 0.0%; the intent boundaries above are the substantive overlap assessment.

## Hashrate sources

Published release checked: v0.2.38, commit e4f05927df3f2537679c2db17695eefb44e8ece6. Its relevant config, miner, adaptive CPU and hashrate-tracker files match the checked working source. Do not apply unrelated unreleased optimization claims.

- `src/miner/hashrate_tracker.rs:6–11,154–185,255–320`: current and session rates are distinct; per-device windows can extend for bursty reporting. The article deliberately gives no single universal averaging duration.
- `src/miner/adaptive_cpu.rs:286–340,1090–1176,1256`: productive tuning, reusable compatible results, available-memory caps and OS pressure signals. Pressure support differs by platform; prose says some operating systems, not all.
- Existing dashboard, tuning, RAM, configuration, benchmark and stopping articles provide the linked procedures. Pool hashrate/tracking own share estimation and account/rig selection. A low pool estimate alone does not diagnose hardware.
- Intel, https://www.intel.com/content/www/us/en/support/articles/000088048.html (read October 26, 2026): thermal protection can reduce clock speed; cooling and platform policy depend on the model/OEM. No universal temperature threshold, voltage or clock-limit change is prescribed.
- NVIDIA, https://docs.nvidia.com/deploy/nvidia-smi/index.html (read October 26, 2026): monitoring distinguishes clock event reasons (thermal/power etc.) and unsupported readings. No command or probe was run on the user's GPU. Article asks to record supported evidence rather than assuming every card exposes all fields.
- Matched intervals, one changed condition, consistent workload/power source and new accepted work form the diagnostic method. This is a proposed procedure, not a measured improvement. The graphic is schematic, with no numeric benchmark trace.

## Wallet sources and semantics

Public CLI release v1.2.0 resolves to `blocknetprivacy/blocknet` commit 948af4de8b7a3e3cddc86a329c7d2d003cb3fd6b (confirmed via GitHub tag and latest release). The pinned `attach_wallet.go` was fetched and read. Public core master is 514a8cf4c686728147ac4756a9fc7bc9a48552b1. Local production `pool` at c646196a2a7ae69c4a9b35f2489fbb7192e41d2f has the same relevant fee defaults and estimator. Source links use the public pinned commits, not an unqualified claim that every wallet uses these settings.

- Core `api_handlers.go:25–27`: standard send minimum 1000 atomic units, 10 atomic units per estimated byte.
- CLI `format.go:119–128`: 100000000 atomic units per BNT.
- Core `wallet/builder.go:140–207`: select mature inputs sufficient for amount plus fee; conservative size estimate; iterate selection/fee as needed. `estimateTxSizeBytes` at605–626 depends on inputs, outputs, ring size and proof allowances. It is not actual serialized byte count or a percentage of the amount.
- Core builder fixed-input path and `TransferAll` (455–487): fee accounting and send-all subtracts fee from selected spendable input total. Ordinary fixed-amount sends preserve recipient amount and return remainder as change. No claim that all wallet outputs are selected or that all total balance is spendable.
- CLI `attach_wallet.go:452–544`: dry_run request, display recipient/fee/change/memo, then exact `Confirm [y/N]:`. Only a normalized y proceeds; Enter/no cancels before the send request. This describes the CLI, not every GUI.
- Core dry-run input leases are released and final send builds separately. A preview is not a permanent quote/reservation; changing wallet state or inputs can change the fee. No promise of byte-identical preview/final fee.
- Illustrative assumed size 5000 bytes ×10 =50000atomic =0.0005BNT, above minimum0.00001. Example inputs10 minus recipient3 minus fee0.0005 =change6.9995BNT. Both are explicitly illustrative, not transactions performed or universal fee quotes.
- Network transaction fee, mining software fee, pool accounting fee and payout minimum have distinct bases. The article links to existing owners instead of copying mining fee rates.

## Art and verification

Original code-native SVGs: hashrate/device/resource comparison and input-to-recipient/fee/change flow. No screenshot is fabricated; the showcase captures the rendered articles in shared Windows Chrome. Verify strict content, protected tokens, arithmetic, release facts, existing tests, complete build, all40 localized pages, mobile/desktop/RTL, schemas, hreflang, sitemap and incoming links. No independent linguistic review is claimed.
