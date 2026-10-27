# Faraday and node operation — October 26, 2026

User approved two guides, each in English and 19 translations. One translation subagent; no separate reviewer. Translations remain draft. Publishing permission includes the existing master-to-Cloudflare workflow. No daemon, wallet, pool or miner process is started, changed or restarted for this article work; no rental or GPU workload.

## Intent boundaries

- `blocknet-faraday-upgrade`: interpret the dated official network plan and distinguish wallet migration, node maintenance and miner compatibility. Current coin/privacy explainers remain the owners of today's mechanisms. No competitor comparison or hardware projection.
- `run-blocknet-node`: install a managed mainnet core and inspect its network/process lifecycle. Wallet creation and recovery stay in the wallet article; bntpool's checkpoint article owns acceleration details. No new performance or first-sync measurement.

## Sources checked

- https://blocknetcrypto.com/#faraday, read October 26, 2026: planned hash-based spend proofs and ML-KEM payment detection, full-chain spend privacy, lighter proof of work, faster node sync and wallet scan, revised VEIL swaps, same chain/history. These remain future intentions throughout. The page says design, testing and review continue.
- The official plan targets approximately February 16, 2027 activation and approximately February 16, 2028 old-format closure, with a one-year migration window. Dates are not final. Wallet scans, previews fee and moves coins with confirmation. Unmigrated old-format coins would become unspendable after the window. Backup is not a substitute for migration. Article gives no migration command, future fee, compatible miner version or unmeasured speedup.
- Public CLI latest release v1.2.0, commit `948af4de8b7a3e3cddc86a329c7d2d003cb3fd6b`; latest public core v0.22.0, commit `5a0a5b510c1dce46f4eeb12c33a291052e44e7b3`. GitHub release/tag metadata checked. CLI README at that commit includes the proposed dates and old-format consequence. Article links pin CLI references to this commit.
- CLI `docs/reference-blocknet.md`: core is a background daemon; client installs/starts/stops/manages it; attach is a separate shell. Mainnet/testnet have isolated data and settings. Start requires an enabled network and waits for API. `install latest` selects a stable core. The guide does not reuse illustrative version/height/peer values from documentation as current observations.
- CLI `setup.go:305–335` saves config and schedules automatic updates before offering core installation. Wizard later offers start. This is described explicitly; no claim updates are opt-in.
- CLI `commands.go:293–305`: outer `blocknet status` invokes `spawnAutoUpgrade`. `docs/reference-upgrade.md` documents scheduler/start/status checks, core restarts for updates following latest and untouched pinned versions. Article distinguishes this from attach's status and calls out dependent API services during maintenance.
- CLI `attach_daemon.go:22–59,118+`: attach status fetches node status and wallet information, displaying height, best hash, peers and syncing. Peers command lists connections. Wallet summary can be absent. Wallet scanning and chain sync are separate; no promise that a single peer count or sync flag establishes health.
- CLI `docs/reference-blocknet.md`: `logs mainnet` follows logs until Ctrl-C; `doctor` reports diagnostics without changing setup. `quit` leaves background core running; outer `stop mainnet` deliberately stops it. We did not run these commands against a live daemon.
- Public explorer https://explorer.blocknetcrypto.com/ is linked as a same-network comparison, not a fixed height or timing claim.

## Verification and presentation

Two original code-native SVG diagrams, existing list/article components, multilingual alt text and protected code blocks. All six node command fences and every inline code/link token must match English. Existing related articles receive links in all locales; their body copy stays unchanged. Check strict content, overlap and semantic boundary, live release manifest, site tests, full build, all localized metadata/internal paths, narrow layouts and desktop/mobile screenshots. No independent linguistic review is claimed.
