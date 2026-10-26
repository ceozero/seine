# Batch 1 brief (2026-10-25)

Six posts written in parallel, one writer each. Shared rules for every writer:

- Work only in `site/` of this worktree (`/home/zp/Code/blocknet/seine-blog-batch1`). Do not
  commit, push, deploy or switch branches.
- Read first: `editorial/writing-guide.md` (the first rule: promote Blocknet, bntpool.com and
  seine, nothing negative, nothing false), `editorial/README.md` (post format and translation
  rules), `editorial/fact-sheet.md`, `editorial/keyword-map.md`, and
  `src/content/blog/how-to-mine-blocknet/index.mdx` plus its `zh-Hans.mdx` and `zh-Hant.mdx`
  as the model for tone, components and translation style.
- Create only your own files: `src/content/blog/<slug>/index.mdx`, `zh-Hans.mdx`, `zh-Hant.mdx`,
  and `editorial/batches/2026-10-batch-1/<slug>.md` (research notes). Do not edit the keyword
  map, backlog, fact sheet, ui.ts, other posts or any code.
- English: `draft: true`, 900-1,600 words, 2+ question headings, 1-2 `<Answer>` blocks of 40-60
  words, 3-5 FAQ entries of 40-60 words, 2-6 tags, description 140-160 characters, plain
  American English, no "X, not Y" lines or taglines, no disambiguation notes (readers know
  Blocknet). Assume `date: 2026-10-25`. Set `related: []` (the integrator fills it in).
- Links: only to `/blog/how-to-mine-blocknet/`, home sections (`/#download`, `/#start`,
  `/#performance`) and external sources. The integrator adds cross-links between batch posts.
- Facts: every number and protocol claim comes from the fact sheet. If you need a fact that
  isn't there, verify it in code (`/home/zp/Code/blocknet/blocknet-core` on branch `pool`,
  read with `git show pool:<path>`; `seine` and `blocknet-pool` from `origin/master` the same
  way) or from an official URL, and record it with its source in your research notes. Never
  invent numbers, user statistics or competitor features. Use only best-per-generation
  hardware results and leave out weak ones.
- Translations: write `zh-Hans.mdx` and `zh-Hant.mdx` as the README describes (mainland vs
  Taiwan terms, localized internal links, same structure, code and external links identical),
  with `translation: draft` and `sourceHash` from `npm run check -- --hash <slug>` run in
  `site/` after the English is final.
- Check with `npm run check -- <slug> --strict` from `site/` until there are no warnings on the
  English. (Translation checks apply once the post is published; still keep structure identical.)
- Report back in at most 20 lines: the intent sentence (reader's job, nearest owner, what's
  unique), a keyword-map row (cluster, search job, supporting phrases incl. one Chinese
  phrase), suggested related slugs from this batch, internal cross-links you'd add, and any
  facts you added (with sources) that belong in the fact sheet.

## Assignments and boundaries

| Slug | Title direction | Owns | Leaves to |
|---|---|---|---|
| `blocknet-mining-hardware-hashrate` | Best hardware for Blocknet mining | which machine to mine on and what H/s it does: best-per-generation table, RAM per thread arithmetic, CPU+GPU | Mac depth to the Mac post; algorithm theory to the Argon2id post |
| `mine-blocknet-on-mac` | Mining Blocknet on a Mac | M-series Macs: setup on macOS, M4 Max results, thread counts by RAM, CPU-only default | general hardware comparison to the hardware post |
| `argon2id-proof-of-work-explained` | Argon2id proof of work explained | what Argon2id does as PoW, the 2 GiB parameters, why memory-hard suits ordinary computers | buying advice to the hardware post |
| `what-is-blocknet` | What is Blocknet | positive overview of the coin: private by default, pay by name, memos, fair launch, mineable on ordinary computers, the Faraday roadmap (attributed) | depth on privacy tech and on names to their own posts |
| `blocknet-id-pay-by-name` | Get paid to @name with Blocknet ID | Blocknet ID shortnames: what they are, how to get one at blocknet.id, paying and mining to `@name` | the overview to what-is-blocknet |
| `blocknet-privacy-features` | How Blocknet keeps payments private | ring of 16 (CLSAG), stealth addresses, Bulletproofs, Dandelion++, encrypted memos, no transparent mode | the overview to what-is-blocknet |
