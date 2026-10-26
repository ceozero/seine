# what-is-blocknet: research notes

## Intent

Reader's job: someone searching "what is Blocknet" or "Blocknet privacy coin" wants a plain overview
of what the coin does and how to start using it. Nearest owner: `/blog/how-to-mine-blocknet/`
(mining setup only). What's unique: the only page that covers the coin as a whole (private by
default, pay by name, memos, payment links, fair launch, emission, mining, Faraday) and routes to
the deep posts on privacy, names and mining.

Boundaries: privacy tech is one bullet per protection (depth belongs to
`blocknet-privacy-features`); names get one section with the rules (registration and mining depth
belong to `blocknet-id-pay-by-name`); mining is one section linking to the how-to guide and
`/#download`.

## Keyword-map row (proposed)

| what is blocknet | `/blog/what-is-blocknet/` | Explain what Blocknet is and what it does for someone new to the coin, then route to wallet, names and mining | Blocknet privacy coin, Blocknet cryptocurrency, Blocknet BNT, Blocknet fair launch, Blocknet Faraday upgrade, Blocknet 是什么 |

## Facts used that are not in fact-sheet.md

- **Payment link format.** The CLI wallet treats a pasted line starting `blocknet://`, `blocknet:`,
  `bntpay.com/` (bare, `www.`, `http://` or `https://`) as a send. The path or host is the
  address or shortname, `amount` is required, `memo` is optional and URL-decoded. Example from the
  tests: `https://bntpay.com/$rock?amount=100&memo=thank%20you` parses to `$rock 100 "thank you"`.
  Source: `blocknet-core@pool:cli.go:821-879`, `cli_payment_link_test.go:38-40` (checked 2026-10-25).
- **Payment links go to a confirm prompt.** The parsed link runs the normal send, which prints the
  details and asks `Confirm [y/N]`. Source: `blocknet-core@pool:cli.go:738`,
  `cli_cmd_wallet.go:161-188` (checked 2026-10-25).
- **Shortnames resolve in send.** `cmdSend` calls `resolveRecipientAddress` and prints
  "Resolved X -> addr [verified]". Source: `blocknet-core@pool:cli_cmd_wallet.go:~90-99` (checked 2026-10-25).
- **Memos are readable only by sender and receiver.** The memo is XOR-masked with a key derived
  from the transaction's shared secret and output index. Source:
  `blocknet-core@pool:wallet/memo.go:22-34`, `:103` (checked 2026-10-25).
- **Empty memos look the same as written ones.** The envelope is padded with cryptographic random
  bytes "to make empty memos indistinguishable". Source: `blocknet-core@pool:wallet/memo.go:65-89`
  (checked 2026-10-25).
- **Memos with spaces work in send** (`send @alice 10 invoice 1042`). Source:
  `blocknet@master:docs/reference-core.md:198`, `:223` (checked 2026-10-25).
- **bntpay.com is live** and its own page uses a `$name?amount=&memo=` link
  (`https://bntpay.com/$bntpay?amount=100&memo=thanks%20%3A%29`). The page doesn't say whether it is
  official, so the post names the link format the wallet parses and doesn't link the site.
  Source: https://bntpay.com/ (fetched 2026-10-25).
- **Faraday wording added beyond the fact sheet,** all from https://blocknetcrypto.com/#faraday
  (fetched 2026-10-25):
  - "One hard fork moves the whole network to post-quantum cryptography and hides every spend in
    the full chain."
  - "Built so a quantum computer cannot forge a spend."
  - "Wallets find their payments faster, so a new wallet is ready sooner."
  - "The wallet scans, shows the fee, and moves your coins when you say so."
  - "after the upgrade you have 1 year to move your coins to the new format."
  - "Planned near the first anniversary of block 1."
  - Also on the page but left out of the post: "VEIL atomic swaps are rebuilt on post-quantum
    primitives" (VEIL isn't described elsewhere; left for a later post).

## Facts used from fact-sheet.md

Ring of 16 (CLSAG), one-time stealth addresses, Pedersen commitments + Bulletproofs, no transparent
mode; 128-byte memo, 124-byte plaintext; shortnames `@`/`$`, case-insensitive, a-z 0-9 `_ - .`, up
to 64 characters, signed mapping via blocknet.id; addresses 92-93 characters ("more than 90");
genesis 2026-02-15 with no transactions; one coinbase output equal to the reward, no treasury or
dev fund; 5-minute blocks, 288/day, 10 safe confirmations (~50 min), 60-block maturity (~5 h);
initial reward 723.25 BNT, monthly decay, ~100M over four years, 2 BNT tail; Argon2id 2 GiB,
"designed to resist ASICs" wording; seine OS and NVIDIA support, auto-tuning, update check every
12 h; pool and seine accept `@name`; Faraday date ~2027-02-16, hash-based spend proofs, ML-KEM,
full-chain privacy, lighter PoW, no new coin, status in design/testing/review, dates planned.

## Wording decisions

- The strict check flags the literal "post-quantum" (and 后量子/抗量子). The post describes the
  planned spend proofs with the site's own phrasing instead ("spend proofs that a quantum computer
  can't forge", "hash-based proofs instead of elliptic curves"), attributed and in the future tense.
- "Anonymity set" is a forbidden word, so the full-chain change is phrased "will hide among every
  output on the chain", quoting the site.
- The site's "experimental: do not use for significant value" line isn't contradicted: the post
  makes no claims about suitability for large amounts.
- Left out: the relaunch history, the month-48 reward drop, fee burning, price and exchange talk.

## Checks

- `npm run check -- what-is-blocknet --strict`: ok (1,375 body words, description 150 characters).
- Translations: passed the full translation checks (structure, blocks, code, links, claims) in a
  scratch copy with the post marked published. `sourceHash` 8c7a72584e9c. `translation: draft`.
- `npm run overlap -- what-is-blocknet`: 0.8% shared with how-to-mine-blocknet, 0.3% with
  mine-blocknet-on-mac.
