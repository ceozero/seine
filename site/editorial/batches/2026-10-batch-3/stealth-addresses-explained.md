# stealth-addresses-explained: research notes

Post: `src/content/blog/stealth-addresses-explained/` ("Stealth addresses explained: how one-time
addresses work"), drafted 2026-10-25. English `sourceHash` 73b695eab1d7; zh-Hans and zh-Hant are
`translation: draft` with that hash.

## Intent

Reader's job: understand how stealth (one-time) addresses work in general (the sender/receiver
math, what the view key and spend key each unlock, how a wallet scans for its outputs), then see
Blocknet as the worked example. Nearest owner: `blocknet-privacy-features` (owns "blocknet stealth
address" as one layer among five, in two paragraphs). This post adds the generic concept and
history, the full key equations, view-only wallets (`viewkeys`), how scanning and seed recovery
work, and routes to the privacy, Blocknet ID, wallet and mining posts.

## Keyword-map row (proposed)

| Primary keyword cluster | URL | Search job | Supporting phrases |
|---|---|---|---|
| stealth addresses explained | `/blog/stealth-addresses-explained/` | Explain how stealth (one-time) addresses work for any coin: view and spend keys, the sender/receiver math, view-only wallets and wallet scanning, with Blocknet as the example | stealth address, one-time address, what is a view key, private view key vs spend key, view-only wallet, how wallets scan for payments, 隐身地址 / 隱身地址, 查看密钥 / 檢視金鑰 |

Boundary: `blocknet-privacy-features` keeps "blocknet stealth address" and summarizes the layer in
two paragraphs, linking here for the mechanics; this post owns the generic term and the key
mechanics. `blocknet-wallet-for-mining` keeps one bullet on `viewkeys` and owns seed backup;
`blocknet-id-pay-by-name` owns names.

## Facts used from the fact sheet

Address = base58(spend_pub ‖ view_pub ‖ 4-byte checksum), 92-93 characters (§1 Addresses);
one-time stealth addresses (§1 Privacy); Ed25519/Ristretto curve25519-dalek (§1); ring of 16,
Pedersen commitments, Dandelion++ (§1); no transparent mode (§1); shortnames and blocknet.id (§1,
§9); memos encrypted with the sender-receiver shared secret (§9); stealth construction
R = rG, shared secret = H(r·view_pub), one-time key = secret·G + spend_pub (§9 via batch-1
privacy notes, `crypto-rs/src/stealth.rs:1-14`); seine address prompt and default pool bntpool.com (§3, §4).

## Facts added (verified in `blocknet-core@pool`, commit c646196, checked 2026-10-25)

- Receiver check and spend key: expected = H(view_priv·R)·G + spend_pub; if it matches,
  one_time_priv = shared_secret + spend_priv. `crypto-rs/src/stealth.rs:11-14`;
  `wallet/scanner.go:233-240` (secret + spendPriv via BlindingAdd).
- Shared-secret hash is SHA-256 with the domain tag `blocknet_stealth_hs`, reduced to a scalar.
  `crypto-rs/src/stealth.rs:259-270`
- Per-output index mixed into the hash, H(shared ‖ output_index), "preventing key collisions when
  multiple outputs go to the same recipient"; builder uses it from `IndexedDerivationHeight`
  6,500 (coinbase outputs keep the non-indexed form). `crypto-rs/src/stealth.rs:272-284`;
  `protocol/params/network.go:15-18`; `wallet/builder.go:275-291`; `wallet/scanner.go:128-137`
- One tx public key R per transaction, shared by its outputs; the scanner computes the ECDH
  point view_priv·R once per transaction, then checks every output. `wallet/builder.go:279`;
  `crypto-rs/src/stealth.rs:472-489`; `wallet/scanner.go:62-69`, `:141-176`
- Scanner verifies the decrypted amount against the on-chain Pedersen commitment before recording
  an output. `wallet/scanner.go:51-56`
- The per-output shared secret derives the amount blinding, the encrypted amount and the memo
  encryption. `wallet/builder.go:294-317`
- Block rewards (coinbase) are paid to a stealth one-time key (`DeriveStealthAddress`).
  `transaction.go:1195-1200`
- Both key pairs derive from the recovery seed: spend from seed bytes 0-31, view from 32-63
  (BIP39-style PBKDF2 seed). `wallet/mnemonic.go:128-186`; 12-word seed in `cli_help.go:219`
- `viewkeys` creates a view-only wallet file `<name>.view.wallet.dat`; its prompt text (quoted in
  the post as a code block) is at `cli_cmd_wallet.go:984-987`; help text "Creates a wallet file
  that can watch funds but cannot spend", use when "you want watch-only access on another
  machine", note "view-only wallets can monitor but cannot spend". `cli_help.go:222-229`
- View-only keys exported = spend public, view private, view public. `api_handlers.go:2328-2405`
- View-only wallets cannot send or sign. `cli_cmd_wallet.go:54-56`, `:232-233`

## External sources (checked 2026-10-25)

- CryptoNote v2.0 whitepaper, Nicolas van Saberhagen, October 17, 2013; section "Unlinkable
  payments", "one-time public key", P = Hs(rA)G + B, x = Hs(aR) + b, tracking key (a, B).
  https://bytecoin.org/old/whitepaper.pdf (read with pdftotext)
- Monero Moneropedia "Stealth address": senders "create random one-time addresses for every
  transaction on behalf of the recipient"; view key shows incoming transactions, spend key sends.
  https://www.getmonero.org/resources/moneropedia/stealthaddress.html
- BIP 352 "Silent Payments" (josibake, Ruben Somsen, Sebastian Falbesoner; assigned 2023-03-09;
  status Complete): a static address receives payments that can't be linked on chain.
  https://github.com/bitcoin/bips/blob/master/bip-0352.mediawiki
- ERC-5564 "Stealth Addresses" (Final; created 2022-08-13; Wahrstätter, Solomon, DiFrancesco,
  Buterin). https://eips.ethereum.org/EIPS/eip-5564

## Wording decisions

- Bitcoin, Monero and Ethereum are described factually; "opt-in features on those chains" for
  BIP 352 / ERC-5564 is a plain description, no ranking.
- The `viewkeys` warning ("Anyone with this file can see your balance and transaction history")
  is quoted because a reader needs it to use the feature safely; framed as "give it only to
  someone you would show your history to".
- No claims about bntpool.com payouts' on-chain visibility (the pool publishes recent payouts),
  so the mining section only says the wallet finds earned BNT with the same scan.
- Chinese terms follow the published privacy and wallet posts: 隐身地址 / 隱身地址, 查看密钥 /
  檢視金鑰, 花费密钥 / 花費金鑰, 恢复助记词 / 復原助記詞; view-only wallet = 仅查看钱包 / 僅檢視錢包.

## Checks

- `npm run check -- --strict stealth-addresses-explained`: 0 errors, one warning ("list 2-4
  related posts") because the brief requires `related: []`.
- Translations pass the structural checks (headings, Answer count, code blocks, external links,
  CTA, FAQ count, localized links) when run with the draft guard removed in a temporary copy of the
  script; the only errors are the expected `translation: draft` ones.
- `npm run overlap` crashed on another writer's in-progress folder; the same overlap logic run on
  a temporary copy that skips unreadable posts gives 0.7% with blocknet-id-pay-by-name, 0.7% with
  blocknet-privacy-features, 0.2% with blocknet-mining-hardware-hashrate.

## Suggested related and cross-links

- related: `blocknet-privacy-features`, `blocknet-id-pay-by-name`, `blocknet-wallet-for-mining`.
- Batch-3 links to add: `ring-signatures-explained` and `bulletproofs-explained` from the
  "combine with the rest of Blocknet's privacy" paragraph; `what-is-a-privacy-coin` from the
  history section; `seed-phrase-explained` from the recovery paragraph. Reverse: link here from
  the stealth-address section of `blocknet-privacy-features` and the `viewkeys` bullet in
  `blocknet-wallet-for-mining`.
