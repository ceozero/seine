# Batch 3 brief (2026-10-25): general explainers

Ten seineminer.com posts written in parallel, one writer each. Shared rules:

- Work only in `site/` of this worktree (`/home/zp/Code/blocknet/seine-blog-batch3`). Don't commit,
  push, deploy or switch branches.
- Read first: `editorial/writing-guide.md` (first rule: promote Blocknet, bntpool.com and seine,
  nothing negative, nothing false), `editorial/README.md` (post format, the required `<CTA>`,
  translation rules), `editorial/fact-sheet.md` (including section 9), `editorial/keyword-map.md`,
  and one finished post with its translations as the model:
  `src/content/blog/blocknet-id-pay-by-name/` (`index.mdx`, `zh-Hans.mdx`, `zh-Hant.mdx`).
- These are GENERAL explainers: each targets a generic search term ("ring signatures explained",
  "what is a privacy coin") that people search regardless of coin. Explain the concept properly for
  anyone, then use Blocknet as the worked example and route readers to the Blocknet-specific posts,
  seine and bntpool.com. You may describe other well-known projects factually where the concept
  needs it (Bitcoin, Monero, Ethereum, Zcash), never disparagingly; don't rank coins or call any
  coin "best" or "most private". General external sources (papers, specs, Wikipedia, project docs)
  are fine when cited in your notes.
- Create only: `src/content/blog/<slug>/index.mdx`, `zh-Hans.mdx`, `zh-Hant.mdx` and
  `editorial/batches/2026-10-batch-3/<slug>.md` (research notes). Don't edit the keyword map,
  backlog, fact sheet, ui.ts, other posts or code.
- English: `draft: true`, `date: 2026-10-25`, `related: []`, 900-1,600 words, 2+ question headings,
  1-2 `<Answer>` blocks (40-60 words), 3-5 FAQ entries (40-60 words), 2-6 tags, description 140-160
  characters, and exactly one `<CTA target="seine|pool" title="…" text="…" />` at the end of the body
  written for this post (no ASCII double quotes inside title/text). Plain American English, no
  "X, not Y" lines, no taglines, no "this is not the BLOCK project" notes. Don't volunteer fees.
- Links: any published post in `src/content/blog/` is fair game (13 posts, see the folder), plus home sections (`/#download`, `/#start`,
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

| Slug | Generic search job | Blocknet angle / boundary |
|---|---|---|
| `what-is-a-privacy-coin` | what a privacy coin is, how privacy coins hide sender, receiver and amount, why it matters | Blocknet as an example of privacy by default; details live in blocknet-privacy-features |
| `ring-signatures-explained` | how ring signatures work (from the 2001 Rivest-Shamir-Tauman idea to linkable ring signatures, key images, CLSAG) | Blocknet's ring of 16; link the privacy post |
| `stealth-addresses-explained` | how stealth (one-time) addresses work: view and spend keys, scanning | Blocknet addresses, view keys and @name; link the ID and privacy posts |
| `bulletproofs-explained` | confidential amounts: Pedersen commitments and Bulletproofs range proofs (cite the 2018 Bünz et al. paper) | Blocknet hides every amount; link the privacy post |
| `dandelion-plus-plus-explained` | Dandelion++ transaction relay: stem and fluff phases, why it protects IP privacy (cite the 2018 paper) | Blocknet's stem probability 0.9 and 10-minute epochs |
| `proof-of-work-vs-proof-of-stake` | the difference between PoW and PoS, security and issuance trade-offs explained neutrally | Blocknet chose memory-hard PoW so anyone can mine; link the Argon2id post |
| `how-crypto-mining-works` | how mining works: blocks, hashes, difficulty, rewards, pools, in plain words | Blocknet numbers as the example (5-minute blocks, LWMA difficulty); link how-to-mine |
| `cpu-mining-2026` | CPU mining in 2026: what to mine with a CPU and why memory-hard coins favor ordinary computers | Blocknet with seine as the featured option; no "best coin" ranking, no profit claims |
| `mine-crypto-on-old-pc-or-laptop` | mining on an old PC or laptop: what matters (RAM, cooling, power), how to start safely | seine sizes itself to the machine; RAM-per-thread arithmetic |
| `seed-phrase-explained` | what a wallet seed (recovery) phrase is, how to store it, why never to share it | the Blocknet wallet's 12-word seed; link the wallet post |
