# Payments and explorer — October 27, 2026

User approved both topics and publication in all 20 languages. One translation subagent; optional independent review not performed or claimed. No wallet transaction, proof form submission, daemon operation, hardware rental or pool deployment. Existing list layout and components retained.

## Distinct jobs

- send-receive-blocknet owns a fixed-amount payment from an existing wallet through preview, send identifier and receiving-wallet verification. Existing wallet article owns creation/recovery; fees owns calculation; ID owns registration; memos and payment links own their own syntax.
- blocknet-explorer-guide owns public search/navigation/interpretation. Confirmation maturity remains on bntpool, privacy mechanisms remain in their explainers, node lifecycle remains in the node guide.
- English overlap check: both 0.0% shared eight-word phrases with existing posts. Semantic boundaries reviewed separately.

## Sources and facts

Inspected October 26,2026 EDT; publication October 27. Public CLI v1.2.0 at 948af4de8b7a3e3cddc86a329c7d2d003cb3fd6b, core v0.22.0 at 5a0a5b510c1dce46f4eeb12c33a291052e44e7b3. References in articles pin these revisions.

- CLI docs/reference-core.md: attach-shell load/address/balance/send/history; shortnames accepted; wallet-state distinctions; view-only receipt and privacy.
- CLI attach_wallet.go:336–365 balance separates spendable/pending/unconfirmed. cmdSend at 452–553 requests dry_run, prints destination/fee/change/memo and resolved address when applicable, only trimmed lowercase y proceeds. It then prints transaction ID and explorer link. Enter or any other answer cancels. No actual command was run against a wallet. RECIPIENT_ADDRESS and 1.25 are explicit syntax/amount placeholders, not a real payee or requested transfer.
- CLI attach_wallet.go:753+ history combines owned incoming outputs and recorded outgoing sends, with mempool outgoing events sorted last. A send result should be checked before retrying; this guide makes no claim that the operation is idempotent.
- Public core explorer.go:635+ search uses numeric height, block hash or tx hash, checks chain and mempool. handleTx shows public fee, counts, key data and private output structures. Confirmations0 in mempool; when included currentheight-containingheight+1. 100/102/3 is labelled arithmetic only.
- https://explorer.blocknetcrypto.com/ inspected in shared Windows Chrome: mainnet label, search, recent blocks, hashrate/difficulty/average block time, peers labelled connected to this node, mempool table. Current browser UI differs visually from local pool daemon fork; live public UI is screenshot authority.
- https://explorer.blocknetcrypto.com/block/69579 and /tx/2c412998688ff824c0fbe4519aa4ec9a3c43ce6a60d5f6f6b7c8a37727c2f0b3: real public block/transfer pages captured. This is not our transaction; no association with an owner is asserted. Transfer shows public fee and hidden amounts, input ring and one-time output keys, encrypted memo. Block shows coinbase/transfer distinction, previous reference, timestamp, difficulty and reward. The article does not reuse observed values as current constants. Browser fetch of /search?q=<full sample transaction ID> followed the redirect to the exact /tx/ page with HTTP200.
- Explorer proof forms explicitly send supplied private view keys to the server. We did not use them. Ordinary public lookup needs only identifiers; article directs private receipt checks to wallet and excludes key submission.
- Existing linked source-backed articles cover fees, privacy, confirmations, rewards, wallet scanning and node progress. No new fee schedule, maturity threshold or timing guarantee is introduced.

## Images and verification

Three real 1200x900 viewport JPEGs from Windows Playwright, captured October 26 around11:57–11:58 PM EDT, reviewed individually; unmodified public UI, no private data. Public app renders timestamps in UTC; article marks capture date in EDT. Original SVGs provide locale-neutral article/list illustrations. Translated image alt text accompanies all assets. Verify strict content, exact command/link preservation, tests, release check, full build, all 40 local/live URLs and 120 incoming links, metadata, sitemap, narrow layouts, desktop/mobile captures, selector dismissal and console. Final evidence and source revision live in http://localhost:8874/payments-and-explorer/.
