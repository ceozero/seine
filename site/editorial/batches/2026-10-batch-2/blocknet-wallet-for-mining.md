# blocknet-wallet-for-mining: research notes

Writer notes for batch 2, 2026-10-25. Times are EDT.

## Intent

A new miner needs somewhere to receive rewards: install an official Blocknet wallet (command line
or desktop), create a wallet, back up the 12-word seed, copy the address into seine, and see
bntpool.com payouts arrive. Nearest owners: `how-to-mine-blocknet` (one bullet: "get an address")
and `blocknet-id-pay-by-name` (names). This post adds the documented wallet procedure, the seed
backup, balance/history readings for payouts, and keeping keys off mining rigs.

## Keyword-map row (proposed)

| get a blocknet wallet for mining | `/blog/blocknet-wallet-for-mining/` | Create an official Blocknet wallet, back up the seed, get the address to mine to and watch pool payouts arrive | blocknet wallet, blocknet address, blocknet recovery seed, blocknet desktop wallet, blocknet cli wallet, 获取 Blocknet 钱包地址 / 取得 Blocknet 錢包地址 |

Boundary: names (`@name`, blocknet.id) stay with `blocknet-id-pay-by-name`; this post links there in
one sentence. Pool-side payout mechanics (PPLNS) stay with bntpool.com's blog; this post only
states the fact-sheet confirmation count and minimum.

## Facts used and sources

From the fact sheet: 60 blocks before payout and 0.1 BNT minimum (§3, live `/api/info`);
5-minute blocks (§1); address 92-93 characters (§1); seine prompts for address or shortname,
default pool bntpool.com (§3, §4); pool miner lookup page (§3).

Command-line wallet, `git -C /home/zp/Code/blocknet/blocknet show master:<path>` (973e56e):

- Quick start: download, `blocknet setup`, or `blocknet install latest` then `blocknet start`;
  `blocknet attach mainnet`; Windows binary is `blocknet.exe`. `README.md:23-29`
- Setup wizard steps: auto-updates question, download latest core, offer to start, shell shortcut.
  `docs/reference-blocknet.md:254-268`
- The core is the daemon running node, wallet, miner and P2P; closing attach leaves it running.
  `docs/reference-core.md:21-23`, `docs/reference-blocknet.md:20-32`
- `load` -> "4) Create a new wallet", name, password, "Wallet created / Address / Filename";
  new BIP39 seed; path saved so future starts auto-load it. `docs/reference-core.md:73-114`,
  `docs/reference-wallet.md:35-108`
- Single `.wallet.dat` file; the password encrypts the spend key. `docs/reference-wallet.md:27-29`
- Loaded wallets copied to `~/.config/bnt/wallets/`. `docs/reference-wallet.md:112-116`
- Password never stored; the 12-word seed is the only recovery path. `docs/reference-wallet.md:131`
- `seed`: warning text, confirm, password, 12 words; store offline on paper, not in a text file,
  notes app or cloud storage. `docs/reference-core.md:349-377`, `docs/reference-wallet.md:184-205`;
  code `attach_wallet.go:836-890`
- `import` option 1 (12-word seed), name, password; the core then scans the chain.
  `docs/reference-wallet.md:156-180`; code `attach_wallet.go:896-917`
- `address` (`addr`, `a`) output with the blocknet.id line. `docs/reference-core.md:161-191`;
  code `attach_wallet.go:316-343`
- `balance` (`bal`): spendable / confirming / total. `docs/reference-core.md:139-157`;
  code `attach_wallet.go:300-309`
- `history`: incoming transactions oldest to newest with block, amount, coinbase/regular.
  `docs/reference-core.md:279-295` (its 72.325 BNT example amount is off by 10x, fact sheet §6;
  not quoted)
- `status` shows `Syncing:`; `sync` rescans downloaded blocks. `docs/reference-core.md:546-600`
- `viewkeys` for watch-only on another machine; a view-only wallet cannot send or sign.
  `docs/reference-core.md:181-191`, `:412-440`
- `lock` / `unlock`. `docs/reference-wallet.md:135-152`
- CLI release v1.2.0 (2026-10-15 21:43 EDT) assets: amd64 linux/macos/windows, arm64
  linux/macos/android zips, SHA256SUMS.txt (`gh api repos/blocknetprivacy/blocknet/releases/latest`).
  The post says only "Windows, macOS and Linux" (no Windows arm64 asset).

Confirmations in the wallet, `git -C /home/zp/Code/blocknet/blocknet-core show pool:<path>`:

- Regular outputs are spendable at 10 confirmations, coinbase at 60 (`wallet/wallet.go:723-744`);
  the balance API's `pending` (shown as `confirming`) is unspent-but-immature
  (`wallet/wallet.go:761-786`, `api_handlers.go:501-502`). 10 x 5 min = ~50 min (derived).
- Pool payouts are ordinary wallet sends (`blocknet-pool@master:crates/pool-runtime/src/node.rs:591`,
  `/api/wallet/send/advanced`), so they appear as `regular` in history.
- bntpool's stats page has a per-address Workers table
  (`blocknet-pool@master:frontend/src/pages/StatsPage.tsx:558-574`).

Desktop wallet, https://github.com/blocknetprivacy/blocknet-gui (README via `gh api .../readme`,
releases via `gh api .../releases/latest` and WebFetch, 2026-10-25):

- Repo description "Graphical wallet for the Blocknet network", BSD-3-Clause.
- Latest release v0.22.0, published 2026-10-16 02:11 UTC = 2026-10-15 22:11 EDT. Assets:
  `.AppImage`, `.deb`, `.flatpak`, `.rpm` (Linux x86_64), `.exe` (Windows), `aarch64.dmg` (macOS
  Apple Silicon), `x86_64-darwin ... .app.zip` (macOS Intel), `SHA256SUMS.txt`.
- README: every release includes `SHA256SUMS.txt` (`sha256sum -c SHA256SUMS.txt`); macOS run
  `xattr -cr /Applications/blocknet.app` once; Windows Defender "More info" then "Run anyway";
  Linux install the `.deb` or run the `.AppImage`; bundled daemon talks to the UI only over
  `127.0.0.1`; zero requests to external services; registers as the `blocknet://` handler and
  pre-fills the Send form for review.
- The README does not describe the create-wallet screens, so the post only tells the reader to
  create a wallet, write down its seed and copy the address. For the integrator: the GUI source
  (`index.html` on master) has "Create New Wallet", "Generate a fresh wallet and recovery seed",
  "Restore an existing wallet with a 12-word phrase", "View Recovery Seed" and a Receive view with
  a copy button, if you want to expand that paragraph.

## Suggested related and cross-links

- related: `how-to-mine-blocknet`, `blocknet-id-pay-by-name`, `blocknet-privacy-features`.
- Batch-2 links to add: from "Watch-only access"/payout sections to `blocknet-encrypted-memos`
  is a weak fit; better, `blocknet-payment-links` from the desktop wallet's `blocknet://` sentence,
  and `seine-dashboard-explained` from the seine address step.
- Inbound: `how-to-mine-blocknet` "A Blocknet address" bullet should link here.
