# seed-phrase-explained: research notes

Writer notes for batch 3, 2026-10-25 (EDT).

## Intent

A reader searching "seed phrase explained" / "what is a recovery phrase" wants to know what the
words are, how they become keys, how to store them and why never to share them, for any coin.
Nearest owner: `blocknet-wallet-for-mining` (owns the Blocknet wallet walkthrough and one section
on backing up the seed). This post adds the general BIP39 mechanics, the Blocknet seed-to-key
derivation, the seed/password/file distinction, storage habits and scam awareness, and routes to
the wallet post for the step-by-step procedure.

## Keyword-map row (proposed)

| seed phrase explained | `/blog/seed-phrase-explained/` | Explain what a wallet seed (recovery) phrase is, how it becomes keys, how to store it and why never to share it, with Blocknet's 12-word seed as the example | what is a seed phrase, recovery phrase, mnemonic phrase, 12-word seed, how to store seed phrase, BIP39 explained, blocknet recovery seed, 助记词是什么 / 助記詞是什麼 |

Boundary: `blocknet-wallet-for-mining` owns creating the wallet, the `seed`/`import` walkthrough
and finding the address; this post explains the concept and summarizes view/restore in one
section that links there. Names stay with `blocknet-id-pay-by-name`; view keys with
`blocknet-privacy-features`.

Overlap (`npm run overlap`): 0.5% of 8-word phrases shared with blocknet-wallet-for-mining,
0% with everything else.

## Facts used and sources

General (external):

- BIP39 (https://github.com/bitcoin/bips/blob/master/bip-0039.mediawiki, read 2026-10-25):
  authors Marek Palatinus, Pavol Rusnak, Aaron Voisine, Sean Bowe; assigned 2013-09-10; entropy
  128-256 bits; table 128 bits/4-bit checksum/12 words up to 256/8/24; checksum = first ENT/32
  bits of SHA-256; 11-bit groups index a wordlist (0-2047); PBKDF2-HMAC-SHA512, 2048 iterations,
  salt "mnemonic"+passphrase, 64-byte output; "it's enough to type the first four letters to
  unambiguously identify the word".
- Derived: 4 checksum bits means 1 in 16 random 12-word lists validate; 2^128 ≈ 3.4 × 10^38.

Blocknet wallet code, `git -C /home/zp/Code/blocknet/blocknet-core show pool:<path>`:

- 12 words, 128 bits entropy, 4-bit checksum, 11 bits per word, PBKDF2 2048 rounds, 64-byte seed:
  `wallet/mnemonic.go:14-21`, generation `:31-39`, checksum check `:118-123`,
  PBKDF2-HMAC-SHA512 with salt "mnemonic"+passphrase `:130-149`.
- Spend key from the first 32 bytes of the seed, view key from the last 32: `wallet/mnemonic.go:159-186`.
- No BIP39 passphrase ("password is for encryption only"): `wallet/wallet.go:458-459`.
- English BIP39 wordlist, 2048 entries: `wallet/wordlist.go:3` (2048 entries counted).
- Mnemonic stored in the wallet data, empty for view-only: `wallet/wallet.go:329`, `:664-672`.
- Wallet file encrypted with Argon2id-derived key + AES-GCM, written 0600:
  `wallet/wallet.go:1567`, `:1650-1653`, `:643`.
- `seed` command warning text, y/N confirm, 12 words in numbered rows of four:
  `cli_cmd_wallet.go:759-800`. `import` option "1) 12-word recovery seed", "Input the 12 words of
  your seed", checksum validation: `cli_cmd_wallet.go:809`, `:830-840`.
- `viewkeys` exports spend public, view private and view public keys only (`ExportViewOnlyKeys`,
  `wallet/wallet.go:690-697`); view-only wallets cannot send (fact sheet via batch-2 wallet
  notes, `blocknet@master:docs/reference-core.md:412-440`).

Blocknet docs, `git -C /home/zp/Code/blocknet/blocknet show master:<path>`:

- New wallet gets a fresh BIP39 seed: `docs/reference-wallet.md:77`.
- Password never stored; the 12-word seed is the only recovery path: `docs/reference-wallet.md:131`.
- Store seed offline on paper; not in a text file, notes app or cloud storage; "Anyone with these
  12 words has full control of your funds": `docs/reference-wallet.md:205`.
- Restore scans the chain afterward: `docs/reference-wallet.md` "Recovery from seed" section.
- "The safest backup is your 12-word recovery seed": `docs/troubleshooting.md:340`.

Desktop wallet (`gh api repos/blocknetprivacy/blocknet-gui/contents/index.html`, master,
2026-10-25): "Create New Wallet" / "Generate a fresh wallet and recovery seed" (lines 70-71),
"Restore from Seed" / "Restore an existing wallet with a 12-word phrase" (74-75), settings item
"View Recovery Seed" with tooltip "Shows your 12-word recovery seed after you enter your
password." (504-510), restore textarea "12-word recovery phrase" (827).

From the fact sheet: seine and bntpool.com take an address or `@name` (§3, §4, §9); view keys and
stealth addresses (§1 privacy).

General security advice in the post (paper, two copies in two places, metal plates, treat seed
requests as scams, on-chain transactions can't be reversed) is standard practice, not a
Blocknet-specific claim, and contains no numbers.

## Suggested related and cross-links

- related: `blocknet-wallet-for-mining`, `blocknet-privacy-features`, `blocknet-id-pay-by-name`.
- Inbound: `blocknet-wallet-for-mining` "How do you back up your recovery seed?" should link here
  ("what a seed phrase is and how it works"); `what-is-blocknet` wallet mention could too.
- Batch-3 links worth adding: `stealth-addresses-explained` (spend/view keys sentence in "What 12
  words mean in Blocknet"), `what-is-a-privacy-coin`.

## Check status

`npm run check -- --strict seed-phrase-explained`: 0 errors, 1 warning ("list 2-4 related posts"),
expected because the brief requires `related: []` for the integrator to fill. sourceHash
03e9082afb55 in both translations (`translation: draft`).
