# Batch 2 brief (2026-10-25)

Six seineminer.com posts written in parallel, one writer each. Shared rules:

- Work only in `site/` of this worktree (`/home/zp/Code/blocknet/seine-blog-batch2`). Don't commit,
  push, deploy or switch branches.
- Read first: `editorial/writing-guide.md` (first rule: promote Blocknet, bntpool.com and seine,
  nothing negative, nothing false), `editorial/README.md` (post format, the required `<CTA>`,
  translation rules), `editorial/fact-sheet.md` (including section 9), `editorial/keyword-map.md`,
  and one finished post with its translations as the model:
  `src/content/blog/blocknet-id-pay-by-name/` (`index.mdx`, `zh-Hans.mdx`, `zh-Hant.mdx`).
- Create only: `src/content/blog/<slug>/index.mdx`, `zh-Hans.mdx`, `zh-Hant.mdx` and
  `editorial/batches/2026-10-batch-2/<slug>.md` (research notes). Don't edit the keyword map,
  backlog, fact sheet, ui.ts, other posts or code.
- English: `draft: true`, `date: 2026-10-25`, `related: []`, 900-1,600 words, 2+ question headings,
  1-2 `<Answer>` blocks (40-60 words), 3-5 FAQ entries (40-60 words), 2-6 tags, description 140-160
  characters, and exactly one `<CTA target="seine|pool" title="…" text="…" />` at the end of the body
  written for this post (no ASCII double quotes inside title/text). Plain American English, no
  "X, not Y" lines, no taglines, no "this is not the BLOCK project" notes. Don't volunteer fees.
- Links: published posts are fair game (`/blog/how-to-mine-blocknet/`, `/blog/what-is-blocknet/`,
  `/blog/blocknet-privacy-features/`, `/blog/blocknet-id-pay-by-name/`,
  `/blog/blocknet-mining-hardware-hashrate/`, `/blog/mine-blocknet-on-mac/`,
  `/blog/argon2id-proof-of-work-explained/`), plus home sections (`/#download`, `/#start`,
  `/#performance`) and external sources. The integrator adds links between batch-2 posts.
- Facts: only from the fact sheet, or verified in code with a citation in your notes:
  `git -C /home/zp/Code/blocknet/blocknet-core show pool:<path>`,
  `git -C /home/zp/Code/blocknet/seine show origin/master:<path>` (or this worktree, which is seine
  master), `git -C /home/zp/Code/blocknet/blocknet show master:<path>`. Never invent numbers; best
  results only, no weak ones.
- Translations: `zh-Hans.mdx` and `zh-Hant.mdx` per the README (mainland vs Taiwan terms; zh-Hant
  uses 運算核心程式 for software kernels; localized internal links; same structure; code and external
  links identical; translate the CTA title/text) with `translation: draft` and `sourceHash` from
  `npm run check -- --hash <slug>` after the English is final.
- Check with `npm run check -- --strict <slug>` (flag before slug) until clean.
- Report in at most 20 lines: intent sentence, keyword-map row (incl. a Chinese phrase), suggested
  related slugs, cross-links you'd add, and facts you added with sources.

## Assignments and boundaries

| Slug | Owns | Leaves to |
|---|---|---|
| `blocknet-encrypted-memos` | the 128-byte encrypted memo on every payment: what it's for (invoices, order numbers, notes), who can read it, padding so memos don't stand out, adding one when sending in the wallet | payment-link format to the payment-links post |
| `blocknet-payment-links` | requesting a payment with a `blocknet://` URI or a bntpay.com link: format, amount and memo, using `$name`, what happens when someone pastes one | memo encryption to the memos post |
| `huge-pages-blocknet-mining` | huge pages for Argon2id mining on Linux/WSL (2 MiB and 1 GiB pages, gains on the validation host, 1,024 pages per thread, commands) and Windows large pages (`docs/guides/windows-large-pages.md`) | NUMA placement to the servers post |
| `mine-blocknet-on-servers` | big machines and rigs: NUMA/L3-aware placement and its measured gains, `--service` mode, the local control API with live events, Prometheus metrics, running headless | huge pages to their own post; buying advice to the hardware post |
| `blocknet-wallet-for-mining` | getting a Blocknet wallet and address to mine to: the official command-line and desktop wallets, creating a wallet, backing up the recovery phrase, finding your address, seeing mining payouts arrive, keeping keys off shared rigs | names to the Blocknet ID post |
| `seine-dashboard-explained` | a tour of seine's terminal dashboard: every field (hashrate, threads, kernel, shares, pool, uptime and so on; read the TUI code under `src/` to get the real labels), what tuning looks like while it runs, keyboard controls if any. You may show the screenshot at `/assets/blog/seine-dashboard.webp` (1400×1037, an Apple M4 Max mining on bntpool at 30.6 H/s with 5 of 5 shares accepted) using Markdown image syntax with descriptive alt text | the pool-side stats to bntpool.com's blog |
