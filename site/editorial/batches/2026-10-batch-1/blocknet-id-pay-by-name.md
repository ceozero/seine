# Research notes: blocknet-id-pay-by-name

Writer notes for `/blog/blocknet-id-pay-by-name/`, 2026-10-25 (EDT).

## Intent

A Blocknet user wants a short `@name` to receive payments and mining payouts, and needs to know
how to claim one at blocknet.id and use it in the wallet, payment links, seine and bntpool.com.
Nearest owner: `/blog/how-to-mine-blocknet/` (mentions mining to `@name` in one bullet). This
post adds the name rules, the signed-record verification, the real blocknet.id claim flow and
pricing, wallet send and payment-link usage, and the pool's balance behavior on a name change.

## Keyword-map row (proposed)

| blocknet id | `/blog/blocknet-id-pay-by-name/` | Claim a Blocknet ID shortname and get paid (wallet sends, payment links, pool payouts) to `@name` | blocknet.id, blocknet shortname, pay by name blocknet, bntpay link, mine to @name bntpool, Blocknet ID 短名称 |

Boundary: `what-is-blocknet` mentions pay-by-name in one paragraph and links here; this post owns
the how-to. `how-to-mine-blocknet` keeps its one-line `@name` mention and links here.

## Facts used from the fact sheet

- Prefixes `@`/`$`, case-insensitive, a-z 0-9 `_` `-` `.`, up to 64 chars, resolved via blocknet.id
  with a signed mapping (§1 Addresses and @shortnames).
- Address = base58(spend_pub || view_pub || 4-byte checksum), 92-93 chars (§1). Post says
  "92 or 93 characters"; description says "90-plus-character" per §6.
- CLI: "Get a short name like @name or $name at https://blocknet.id"; `blocknet://` / `bntpay.com/`
  links auto-parse as a send (§1).
- Memo plaintext up to 124 bytes; one-time stealth addresses (§1 Privacy).
- Pool: login accepts shortnames, resolved address fixed for the connection, "a name change never
  redirects an existing balance"; seine v0.2.16+ for shortnames (§3).

## Facts added (not in the fact sheet), with sources

Daemon / wallet (`blocknet-core@pool` = c646196):
- Resolver fetches `https://blocknet.id/api/v1/resolve/<handle>` and verifies an **Ed25519**
  signature over the payload with the key from `https://blocknet.id/.well-known/blocknet-id.json`
  (cached 10 min); the signed payload carries `handle`, `address`, `updated_at_unix`, and handle,
  address and timestamp must all match. `handle_resolver.go:15-19`, `:62-69`, `:107-152`, `:154-184`.
- CLI `send` prints `Resolved <name> -> <address> [verified]` (a green "✓ verified" with color),
  and the confirmation shows the name plus an `Address:` line. `cli_cmd_wallet.go:89-99`, `:163-171`.
- Wallet API resolves names for every recipient of a send request. `api_handlers.go:885-905`.
- Payment link format: `blocknet://<address>?amount=..&memo=..` and `bntpay.com/<address-or-name>?amount=..&memo=..`
  (bare, http(s), www accepted); `amount` is required ("payment link missing amount"), memo optional.
  `cli.go:821-886`. Test case `https://bntpay.com/$rock?amount=100&memo=thank%20you` parses to
  `$rock 100 "thank you"`: `cli_payment_link_test.go:38-42`. (The post uses `$name` in the bntpay
  example because that form is tested; `blocknet://@name` was not used since URL parsing would
  read `@` as userinfo.)
- `send` example `send @rock 100 "hello"`; "You can send whole numbers or fractions".
  `blocknet@master:docs/reference-core.md:199-225` (973e56e).

blocknet.id (live, fetched 2026-10-25 ~01:35 EDT with WebFetch and curl):
- Home: "short names for wallets", search box "find a name", nav "search / pricing / sign in".
  Live hint text: "letters, numbers, . _ - only", "too long (max 64 characters)". https://blocknet.id
- Search result for an available 9+ char name: price "FREE", "18 characters — free while the promo
  runs. No invoice, no payment.", a "wallet address" field and a "Claim free" button. For an
  8-char name: "100 BNT" and a "Register" button. https://blocknet.id/search?handle=...
- Registered name: shows address, "updated <date>", "view public page". Public page
  (`https://blocknet.id/$blocknetid`) shows address, "signed payload" and "signature (ed25519)".
- Pricing: "One-time price, by name length. Shorter names cost more." "9+ characters: FREE!
  ... no invoice, no payment." Table: 1=6000, 2=5000, 3=4000, 4=3000, 5=2000, 6=1000, 7=500,
  8=100 BNT, 9+ FREE (PROMO). https://blocknet.id/pricing. Volatile: the post dates it "October 2026".
- Manage: "sign in with your blocknet address"; the page script has reassign-address controls
  (edit/save an address per name). https://blocknet.id/manage
- `/.well-known/blocknet-id.json` returns `signing_pubkey`, `resolve_template` `/api/v1/resolve/{handle}`,
  `ttl_default` 60.
- Not verified: what sign-in requires after entering the address (likely a signed challenge; the
  page has challenge-card styles), and what paying for a priced name involves. The post says only
  what the site shows.

bntpay.com (live 2026-10-25): home "Payment links for Blocknet", format
`bntpay.com/ADDRESS?amount=100&memo=invoice-42`; a link page shows "Pay <name>", Amount, Memo, an
"Open in Wallet" button that navigates to `blocknet://<address>?amount=..&memo=..` (auto after 600 ms).
https://bntpay.com

bntpool.com (`blocknet-pool@origin/master` = 02232a5):
- Stratum login calls the shortname resolver before `login_with_hint`; jobs/shares/balances/payouts
  use the resolved address; new login resolves again; resolver failures reject login; stats page
  supports shortname lookups. `README.md:280`, `crates/pool-runtime/src/stratum.rs:681-698`,
  `crates/pool-runtime/src/shortname.rs` (same wire contract as the daemon).
- Start page: "Mine and track payouts with your wallet address or Blocknet ID shortname";
  "Keep the quotes around shortnames so your shell passes them correctly"; "Register a shortname at
  blocknet.id. Seine shows the resolved wallet address before mining and keeps it fixed until you
  restart mining. You can also use either shortname form in My Stats." `frontend/src/pages/StartPage.tsx:38`, `:89-104`.

seine (`seine@origin/master` = d03a1b0):
- `--address`, first-run prompt, saved config and control API `mining_address` accept shortnames in
  pool and daemon mode; quote `$name` in shells; verifies the signed mapping and validates the
  address before mining; resolved address logged and fixed for the run including reconnects; saved
  shortnames resolved again next run; full addresses need no resolver. `docs/guides/configuration.md:78-88`,
  `docs/MINER_FLAGS.md:22`, `src/miner/mod.rs:229-275` (logs `resolved <name> to <address>`).
- Seine resolves the name itself and logs into the pool with the full address; the pool's own
  resolution covers any client that logs in with a name. The post describes both.

## Suggested fact-sheet additions

- Ed25519 signed resolver contract and the well-known key URL (daemon `handle_resolver.go`).
- blocknet.id claim flow and the pricing table (live, volatile, dated).
- Payment-link grammar and the required `amount` field (`cli.go:821-886`).
- Pool login resolves names (`stratum.rs:681-698`) and the stats page accepts names (`README.md:280`).
- Resolves §7 open question on the product name: the pool UI and seine docs say "Blocknet ID
  shortname"; blocknet.id itself brands as "$blocknet.id" / "short names for wallets".
