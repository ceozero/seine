# Wallet sync and view-only access

Reviewed October 27, 2026, America/New_York (EDT). User approved both articles and publication in all 20 languages. One translation agent; no independent linguistic review claimed.

## Sources

Public CLI v1.2.0, commit `948af4de8b7a3e3cddc86a329c7d2d003cb3fd6b`, remains the latest public CLI release on this date. Public core v0.22.0 source is `5a0a5b510c1dce46f4eeb12c33a291052e44e7b3`. Do not substitute local fork behavior for published client claims.

- CLI `attach_wallet.go:336-423`: balance categories and best-effort lag warning compare wallet scan height with chain/sync target. A warning's absence is not proof of a complete scan.
- CLI `attach_wallet.go:880-1019`: output listing, scan/chain heights and empty-list messages. The catch-up message is conditional on an empty filtered list.
- CLI `attach_wallet.go:1268-1344`: viewkeys confirmation, original wallet password, separate export-file password, displayed private viewing key and saved path. No real key values or export operation used for this article.
- CLI `attach_wallet.go:1494-1535`: sync calls the wallet scan endpoint and reports scanned height or already-synced status.
- CLI `docs/reference-core.md:457-489,584-646`: viewing-file workflow, scan versus P2P download and node status.
- CLI `docs/reference-wallet.md`: loaded wallet paths, default folder and Windows equivalent, separate networks, import types and recovery.
- CLI `docs/troubleshooting.md:223-250,294-315`: scan progress, connectivity and backup-preserving recovery guidance. The article does not prescribe purge, chain deletion or repeated payments.
- Core `wallet/wallet.go:568-639`: the view-only wallet stores viewing keys and is encrypted when saved; `api_handlers.go:2490-2499` requires its file password to differ from the full-wallet password.
- Core `api_handlers.go:946-948,1171-1173`: view-only wallets cannot sign or send. `:2406-2535` exports viewing keys and optionally a separately encrypted wallet file. `:2267` demonstrates that viewing material has capabilities beyond a public address; article calls it private access and does not promise that outgoing information is secret from it.

Pinned source URLs: https://github.com/blocknetprivacy/blocknet/tree/948af4de8b7a3e3cddc86a329c7d2d003cb3fd6b and https://github.com/blocknetprivacy/core/tree/5a0a5b510c1dce46f4eeb12c33a291052e44e7b3 .

## Intent and evidence

The sync guide diagnoses an existing wallet observation; it does not duplicate node installation, checkpoint setup, wallet creation/recovery or pool payout accounting. The view-only guide teaches the exported-file workflow, unlike the stealth-address explainer's key mathematics. Both use exact documented command blocks and original explanatory SVGs; these are illustrations, not screenshots or observed wallet balances. No keys, funds, daemon state, mining hardware or live wallet were used.

English strict checks passed. Eight-word phrase overlap is 1.0% between the new guides (shared reviewed-version introduction) and 0.0% with existing posts. Existing related-article bodies remain unchanged; related frontmatter and translation source hashes are updated together.
