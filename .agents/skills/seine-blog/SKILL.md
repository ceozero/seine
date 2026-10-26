---
name: seine-blog
description: Plan, research, write, translate (19 languages), check and publish SEO articles for the seineminer.com blog, which covers Blocknet in general (privacy, payment by name, wallet, upgrades) and mining it (seine, bntpool.com, Argon2id, CPU/GPU tuning). Use when asked to write or update a blog post, pick blog topics, translate a post, refresh the keyword map or fact sheet, or audit the site's SEO.
---

# seineminer.com blog

**First rule:** every post promotes Blocknet, bntpool.com and seine, with nothing negative
about any of them (no downsides, risk sections, weak results, unflattering caveats or
comparisons where we look worse), and nothing false: omit rather than misstate. The blog covers
Blocknet in general as well as mining, and links to seine and bntpool.com wherever it fits.

The site is an Astro project in `site/`; the pipeline lives in `site/editorial/`. Read these
before doing anything else:

1. `site/editorial/README.md`: the workflow, post format and translation rules.
2. `site/editorial/keyword-map.md`: which URL owns which search job. One job per URL.
3. `site/editorial/writing-guide.md`: house style, disambiguation and claims to avoid.
4. `site/editorial/fact-sheet.md`: the only allowed source of facts and numbers.

Then, by task:

- **New post:** take the top unclaimed topic in `site/editorial/backlog.md` unless the user
  named one. Write the intent sentence (README step 1), make the batch folder, research, and
  draft `site/src/content/blog/<slug>/index.mdx` with `draft: true`, ending with one
  `<CTA target="seine|pool" title="…" text="…" />` written for the post. From `site/`, run
  `npm run check -- <slug> --strict` and `npm run overlap -- <slug>` until clean. Leave it as a
  draft and report the intent sentence, the overlap result, and any facts you added to the fact
  sheet. Publishing needs the user's go-ahead.
- **Translating:** every published post needs all 19 translations; follow
  `site/editorial/translation-guide.md` (protected values, link prefixes, glossary), set
  `sourceHash` from `npm run check -- --hash <slug>`, and keep `translation: draft`. A separate
  review is optional; use `translation: reviewed` only after one actually happens.
- **Updating a post:** keep the slug; bump `updated` only for material changes; update the
  changed passages in every translation and their `sourceHash`; keep the keyword-map row in
  sync with any retargeting.
- **Several posts:** keep each to its own search job and cross-link them through `related`.
  Don't produce near-duplicate permutations.
- **Facts:** verify against code before adding to the fact sheet: `blocknet-core` on its
  `pool` branch for consensus, `blocknet-pool` for the pool, `seine` for the miner. Cite
  `path:line` and the date. The fact sheet is in a public repo: no unannounced Faraday details.

`npm run build` fails on forbidden claims, broken internal links, a missing keyword-map row and
missing, stale or structurally invalid translations. Pushing to `master` deploys (see `site/README.md`);
deploying by hand needs the user's request.
