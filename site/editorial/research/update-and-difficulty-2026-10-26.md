# Miner updates and difficulty — October 26, 2026

## Intent and boundaries

- `update-seine-miner`: maintain an existing installation while retaining its data path,
  working directory and launch arguments. Platform guides own first installation;
  antivirus/download guide owns checksum walkthrough and warnings; server guide owns
  service configuration. The new procedure adds replacement and post-update checks.
- `mining-difficulty-explained`: understand target thresholds and difficulty adjustment.
  Hashrate owns speed/units; luck owns round variance; share outcomes owns rejection
  troubleshooting; calculator owns reward amounts. No competitor comparison or hardware rental.

## Evidence

Release checked against GitHub's public API: v0.2.36, published October 26, 2026,
11:34:54 AM EDT. This guide concerns the public release, not pending master behavior.

- `seine@v0.2.36:src/config.rs:369-371,860-880`: default data directory is
  `./seine-data`; configuration is read from that directory and first-run bootstrap
  happens if absent. Relative paths resolve against process working directory.
- `seine@v0.2.36:src/user_config.rs:8-18`: saved schema includes mode, address,
  pool_url, pool_worker and dev_fee_pool_worker; backend/thread flags are separate.
- `seine@v0.2.36:docs/guides/configuration.md`: q/Ctrl+C exit, saved configuration,
  runtime behavior, tuning files and flags. Preserving app+data before replacement
  and explicit service paths are editorial operating procedures, not an auto-updater.
- `seine@v0.2.36:src/update_check.rs:16-19,45-60`: release notification at startup
  and every 12 hours. It fetches release metadata, announces a link and does not
  replace binaries. `src/config.rs` clap command exposes --version.
- `seine@v0.2.36:.github/workflows/release.yml` and `docs/guides/nvidia.md`:
  five platform archives, Windows runtime libraries bundled with executable,
  release checksum asset. No claim that this batch performed a miner upgrade
  on the user's running optimization machines.
- Official release: https://github.com/zpalmtree/seine/releases/tag/v0.2.36
- Pinned reference: https://github.com/zpalmtree/seine/blob/v0.2.36/docs/guides/configuration.md
- `blocknet-core@c646196a2a7ae69c4a9b35f2489fbb7192e41d2f:block.go:56-78`:
  300-second target, LWMAWindow=60, bounded solve times and minimum difficulty.
- Same revision `block.go:2047-2103,2307-2349`: next difficulty derived per block
  from 61 timestamps forming 60 intervals, newer intervals weighted more heavily.
  Article describes directional response, not a guarantee after any single block.
- Same revision `crypto-rs/src/pow.rs:166-194`: exact integer division of
  `(2^256 - 1)` by difficulty. Expected hashes approximately equal difficulty.
  Expected seconds = difficulty / H/s follows from that probability model.
- `blocknet-pool@069b9ee:crates/pool-runtime/src/engine.rs`: connection/job share
  difficulty and `note_share_and_maybe_adjust_difficulty`; vardiff controls
  submission frequency. Daemon block validation remains separate.
- Recent network hashrate estimate: daemon `block.go:1601-1633` sums sampled work
  and divides by elapsed time; differs from next difficulty / target interval.
- Arithmetic-only example: 30,000 / 100 = 300; 60,000 / 100 = 600;
  60,000 / 200 = 300 seconds. No live difficulty or hashrate is represented as fixed.

## Release data correction

v0.2.36 `src/dev_fee.rs` declares DEV_FEE_PERCENT=2.0 without a pool-specific
constant. Both release manifests now explicitly declare feePolicy=flat; their
source hashes and five archives were verified against the published release.
The validator retains legacy pool-specific support and rejects unexpected policy
overrides. The calculator renders the reviewed version and 2% default in all
20 locales; existing historical v0.2.26 measurements retain their version labels.
No miner fee is volunteered in the new update article; the calculator needs it
for its existing calculation. Tests cover current and legacy policy validation.

## Graphics and translations

Original SVG update diagram: application replacement, preserved configuration,
connection verification. Original pool cover: same result field, smaller qualifying
region; schematic, not a probability measurement. No screenshots of mining activity
were fabricated. All 19 translations authored by the active model and checked against
source structure and protected commands/links; metadata remains translation: draft.
No independent linguistic review is claimed.

## Verification

Both English drafts and all translations pass strict content checks. Closest
8-word-phrase overlaps are 0.0%; adjacent owners were checked for intent overlap.
Release policy tests: 5 passed. Pool frontend tests: 21 passed. Build/live results
and exact final source revisions are recorded in the stable showcase:
http://localhost:8874/update-and-difficulty/

Desktop/mobile captures use the shared Windows Chrome Playwright MCP. Production
pool deployment is --api-only; compare Stratum PID/start time before and after.
