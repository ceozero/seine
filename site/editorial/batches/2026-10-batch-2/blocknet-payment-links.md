# blocknet-payment-links: research notes

Writer: batch 2, 2026-10-25. Refs: `blocknet-core@pool` = c646196 (2026-10-15), `blocknet@master` = 973e56e.

## Intent

A reader who wants to request BNT writes a `blocknet://` or bntpay.com payment link (recipient,
amount, memo, `$name`) and knows what the payer's wallet does with it. Nearest owner:
`/blog/blocknet-id-pay-by-name/`, which has one short section showing the two forms with a name.
This post adds the full format (accepted prefixes, required fields, decimal places, URL encoding of
the memo), the address-vs-name choice, the step-by-step paste-to-confirm flow, testing a link, and
use cases.

Proposed keyword-map row:

| blocknet payment link | `/blog/blocknet-payment-links/` | Write a `blocknet://` or bntpay.com link that requests an amount (with memo and `$name`) and know what pasting it does | blocknet uri, bntpay link, request BNT payment, blocknet invoice link, blocknet://, Blocknet 付款链接 |

Boundary: the Blocknet ID post keeps its short payment-link section and links here for the format;
"bntpay link" could move from its supporting phrases to this row. Memo encryption and padding stay
with `blocknet-encrypted-memos` (this post says only that the link memo travels as the encrypted
memo and appears in `history`).

## Facts used (beyond fact sheet §1 and §9)

- Accepted prefixes: `blocknet://`, `blocknet:`, `bntpay.com/`, `www.bntpay.com/`, and both with
  `http://` / `https://`; prefix matched on a lowercased copy (case-insensitive); a bare bntpay link
  gets `https://` prepended. `blocknet-core@pool:cli.go:827-842`.
- Recipient = URI host (or opaque part / path) for `blocknet:`; path for bntpay; host must be
  bntpay.com or www.bntpay.com. `cli.go:849-867`.
- Errors: `payment link missing address`, `payment link missing amount`; memo optional.
  `cli.go:869-883`.
- The parsed link becomes `send <recipient> <amount> [memo]`. `cli.go:738-743`.
- Amount: decimal BNT, fraction padded or truncated to 8 digits; 1 BNT = 100,000,000 atomic.
  `cli.go:990-1035` (`atomicPerBNT` at `:1010`).
- Memo max `MemoSize-4` = 124 bytes ("memo too long"). `cli_cmd_wallet.go:83-85`; size in
  `protocol/params/memo.go` (fact sheet §1).
- Send flow: resolve recipient and print `Resolved <name> -> <addr>` with verified mark
  (`cli_cmd_wallet.go:88-100`); balance check and build (`:116-159`); summary "Send X to <name>?",
  Fee, Address (when a name was used), Change, Memo, `Confirm [y/N]` (`:161-185`); anything but y
  prints `Cancelled` and releases the input lease (`:187-192`); y submits and prints `Sent:` plus
  `https://explorer.blocknetcrypto.com/tx/<id>` (`:194-226`).
- Received memos are shown by `history` on IN entries. `cli_cmd_wallet.go:351-365`, `:432-450`.
- CLI docs: "Pasting a `blocknet://` URI or `bntpay.com/` link auto-parses as a send."
  `blocknet@master:docs/reference-core.md:226`; send usage and example `:195-225`.

## Parser behavior verified by running it

Copied `parseSendArgsFromPaymentLink` verbatim from `cli.go:821-884` into a scratch Go program
(go1.26.5, 2026-10-25) and ran these inputs:

- `blocknet://$rock?amount=25&memo=invoice-42` -> `$rock 25 invoice-42` (so `$name` works in the
  `blocknet://` form as well as bntpay; the tested bntpay case is `cli_payment_link_test.go:38-42`).
- `blocknet://@rock?amount=25` -> `rock` (the `@` is read as URL userinfo), which is why the post
  tells readers to write names as `$name` in links. `blocknet:@rock` and `bntpay.com/@rock` keep
  the `@`, but the post shows only the `$` form.
- `memo=order%201042` and `memo=order+1042` -> `order 1042`; `%2B` -> `+`; `%26` -> `&`;
  unencoded `&b` is dropped as a new field; unencoded `#1042` is cut off as a fragment; `%23` -> `#`.
- `memo=x&amount=3` parses (field order free); trailing slash after the name is trimmed;
  `BNTPAY.COM/$Rock?...` matches; `amount=0.00000001` passes through.

## bntpay.com

Live 2026-10-25: titled "BNTPAY", "Payment links for Blocknet", example
`bntpay.com/ADDRESS?amount=100&memo=invoice-42`. Per the assignment the post mentions bntpay.com
only as a link format the wallet accepts, does not call it official and does not link it.

## Not used

- Desktop (GUI) wallet handling of links: not verified, so the post describes the command-line
  wallet only.
- `amount=all` and `hex:` memos would pass through the parser to `send`; left out as edge cases.
