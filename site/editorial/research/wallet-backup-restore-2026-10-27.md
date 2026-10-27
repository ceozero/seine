# Wallet backup, recovery and migration

Checked October 27, 2026 (America/New_York, EDT). User approved publishing in all 20 languages. One translation agent; translations remain draft without independent-review claims.

## Sources and scope

Official CLI latest release v1.2.0, commit 948af4de8b7a3e3cddc86a329c7d2d003cb3fd6b; core latest release v0.22.0, commit 5a0a5b510c1dce46f4eeb12c33a291052e44e7b3. GitHub latest tags rechecked for this batch. Article describes these released versions.

- CLI `attach_wallet.go:98-180`: load uses directory of configured wallet_file, lists existing wallet files; custom paths must stay inside that folder. Choosing create generates a different wallet. One wallet is loaded at a time.
- CLI `attach_wallet.go:183-319`: existing load uses supplied password; create prompts twice. Local backup is created with owner read/write permissions only if the destination filename does not already exist; it is not a rolling overwrite backup.
- CLI `attach_wallet.go:321-337`: unload calls wallet/unload, reports success. Core `api_handlers.go:1626-1654` releases wallet/scanner references. The article recommends unloading before copying; it does not claim filesystem snapshots or backup completeness are guaranteed by that command.
- CLI `attach_wallet.go:1072-1132`: seed prompts for confirmation and password; no-seed message exists for wallets without a mnemonic. Full file + password path remains applicable; no universal seed availability claim.
- CLI `attach_wallet.go:1134-1268`: import option 1 reads the original seed, asks for name and a new password twice, reports address. No sample recovery phrase is published in this guide.
- Core `api_handlers.go:1980-2087`: import refuses overwrite of an existing file, creates wallet under configured wallet directory, publishes the new wallet and starts catch-up scanning. A newly set password belongs to the new file; the old file is not modified by this import.
- CLI docs `reference-wallet.md:21-26,95-112,136-189,211-223` and `troubleshooting.md:344-348`: wallet file/state, directory, password, recovery and manual-copy guidance. Preserve separate original records; no claim that a seed reconstructs every local historical record.
- CLI `attach_wallet.go:340-391,757-882`: balance warns while behind; history merges incoming outputs and separately recorded outgoing sends. Seed recovery scan is distinguished from exact preservation of local history.
- Docs `reference-wallet.md:163-166`: view-only access cannot spend; cannot substitute for a full-wallet recovery backup.

Independent recommendations: separate dated backup storage, no overwriting unrelated files, record full address/network/filename, compare after recovery, preserve original until verified, retire old device storage using ordinary secure disposal. These are recommendations, not built-in automation claims. File copies retain access to the same keys; no automatic revocation or duplicate balance is claimed. No real wallet data, keys, seeds, transactions, signing or mining operation was used.

## Intent and overlap

The guide owns the end-to-end backup and migration/recovery procedure. Existing wallet setup has only a brief recovery paragraph; seed phrases owns conceptual secret handling; syncing owns scan diagnosis; view-only owns monitoring access. Overlap checker: 1.8% with message signing, 1.3% with payment proof, 0.3% with view-only, primarily shared wallet context. Existing related article bodies remain unchanged.

## Newly supplied Faraday source

During this batch the user supplied https://blocknetcrypto.com/blog/2026-10-27-how-blocknet-privacy-survives-quantum-computers/ and authorized updating the existing Faraday guide after this guide is published. It describes proposed future seed/address/migration changes, explicitly still in development. The current guide retains its released-version scope; Faraday update is separate follow-up work.
