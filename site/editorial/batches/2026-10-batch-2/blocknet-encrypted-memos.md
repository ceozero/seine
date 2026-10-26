# blocknet-encrypted-memos: research notes

Post: `src/content/blog/blocknet-encrypted-memos/` ("Encrypted memos on Blocknet payments"),
drafted 2026-10-25. English `sourceHash` 15e0f8b98360; zh-Hans and zh-Hant are `translation: draft`.

## Intent

Reader's job: attach an invoice number, order reference or note to a BNT payment, know who can
read it, and find memos they've received. Nearest owner: `blocknet-privacy-features`, which has
two paragraphs on memos (who reads them, padding) and lists "blocknet encrypted memo" as a
supporting phrase. This post adds the procedure (CLI `send` memo argument, `hex:` form, API
`memo_text`/`memo_hex` per recipient), the envelope layout, change-output and coinbase memo
rules, where memos appear on receipt (`history`, `outputs`, API) and payment proofs that reveal
the memo. Link format stays with `blocknet-payment-links`.

## Keyword-map row (proposed)

| Primary keyword cluster | URL | Search job | Supporting phrases |
|---|---|---|---|
| blocknet memo | `/blog/blocknet-encrypted-memos/` | Add an encrypted memo (invoice, order number, note) to a Blocknet payment, know who can read it, and find received memos | blocknet encrypted memo, blocknet payment memo, blocknet send memo, blocknet memo length, Blocknet 加密备注 / Blocknet 加密備註 |

Boundary: `blocknet-privacy-features` keeps a short memo section and should link here for the
how-to; `blocknet-payment-links` owns the `blocknet://` / bntpay.com format and only mentions
that a link can carry a memo. Consider moving "blocknet encrypted memo" from the privacy row
to this row when publishing. Overlap report: 0.4% shared 8-word phrases with
blocknet-privacy-features, 0.1% with what-is-blocknet.

## Facts used from the fact sheet

128-byte memo per output, 124 bytes of plaintext (§1 Privacy); memo encrypted with the
sender-receiver shared secret, short/empty memos padded with random bytes (§9); payment links
carry `memo` and a pasted link opens the normal confirm step (§9); 1 BNT = 100,000,000 atomic
units (§1); coinbase memo must be empty (§1 Fees bullet, `block.go:663-695`).

## Facts added (verified 2026-10-25)

Refs: `blocknet-core@pool` = c646196; `blocknet@master` = 973e56e.

- CLI usage `send <address> <amount> [memo|hex:<memo_hex>]`, "Sends BNT to another wallet,
  optionally with a note", "Memos with spaces are supported".
  `blocknet@master:docs/reference-core.md:34`, `:195-226`; `blocknet-core@pool:cli_help.go:99-135`
- Memo parsing: remainder of the line joined (spaces OK), a matching pair of single/double
  quotes stripped, `hex:` prefix decoded as hex, plain text is UTF-8 bytes; longer than 124
  bytes fails with `memo too long: max 124 bytes` before the transaction is built.
  `blocknet-core@pool:cli_cmd_wallet.go:63-86`
- Confirm screen order: `Resolved @x -> <addr> ✓ verified` (before the Send heading),
  "Building transaction...", `Send <amt> to <label>?`, `Fee:`, `Address:` (for names),
  `Change:` (when > 0), `Memo:` shown quoted (`strconv.QuoteToASCII`) or as hex, then
  `Confirm [y/N]:`. `cli_cmd_wallet.go:92-188`. Fee shown as `<fee>` in the post on purpose.
- Pasted payment link → send args `address amount [memo]`. `cli.go:821-886`
- API `POST /api/wallet/send` body `{"recipients":[{address, amount, memo_text|memo_hex}]}`;
  both fields → error; 124-byte max; names resolved per recipient; amounts in atomic units.
  `api_handlers.go:866-950`, `:1049`, `:1119-1121`; route `api_routes.go:35`
- Envelope: version(1) + length(1) + checksum(2) + payload(n) + padding; MemoSize 128,
  MemoPayloadMax 124. `protocol/params/memo.go:8-18`
- Checksum = first 2 bytes of SHA3-256("blocknet_memo_checksum" ‖ len ‖ payload); decrypt checks
  version, length and checksum. `wallet/memo.go:35-63`, `:92-101`
- Padding from `crypto/rand`, "to make empty memos indistinguishable", fails closed on RNG error.
  `wallet/memo.go:76-88`
- Mask: SHA3-256(shared secret ‖ "memo" ‖ output index ‖ network domain separator) expanded to
  128 bytes with four SHA3-256 blocks, XORed with the envelope; per-output index.
  `wallet/memo.go:21-33`, `:103-126`; `MemoBlockDomainSep = NetworkID` (`protocol/params/memo.go:22`)
- Recipient memo encrypted with the recipient's shared secret; change outputs get an empty
  (padded) memo. `wallet/builder.go:317`, `:372`
- Receiver decrypts during scan with the secret derived from the private view key.
  `wallet/scanner.go:180-200`, `:250-291`
- View key "lets anyone see all incoming funds — share it carefully".
  `blocknet@master:docs/reference-core.md:440`
- Coinbase memo must be an empty envelope, "to prevent miners from using coinbase memos as an
  on-chain metadata channel". `block.go:688-694`
- Blocks with an all-zero `encrypted_memo` on any output are rejected at prefilter.
  `daemon.go:729-746`
- Explorer shows the memo as hex "(encrypted)". `explorer.go:512`, `:1186`
- Received memos: CLI `history` shows IN and OUT entries with a `memo:` line (OUT from send
  records); `outputs <n>` / `outputs tx <txid>` print `memo:`; printable text quoted, else hex;
  API `GET /api/wallet/history` returns `memo_hex`.
  `cli_cmd_wallet.go:337-452`, `:575-612`, `:685-710`; `api_handlers.go:528-561`
- Payment proof: `prove <txid>` prints the tx key; `POST /api/verify-proof` (public route, no
  wallet) takes txid, tx_key and address and returns matched outputs, amounts and memo.
  `cli_cmd_wallet.go:1020-1064`; `api_handlers.go:343-466`; `api_routes.go:19`
- UTF-8 arithmetic: 124 bytes = 124 ASCII characters or 41 three-byte CJK characters.

## Wording decisions

- No fee amount shown (`<fee>` placeholder in the confirm example), per "don't volunteer fees".
- "Quickest way to get BNT" softened to "a simple way" (unverifiable superlative).
- The intro section is plain prose so the post has exactly two Answers
  (send, who can read).
- `related: []` per the batch brief; the strict check's only remaining warning is "list 2-4
  related posts", left for the integrator.
