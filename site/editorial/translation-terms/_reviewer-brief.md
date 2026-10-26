# Blog translation review brief (seineminer.com)

Review is optional, not a publishing gate (owner decision, 2026-10-25). Use this brief only
when a separate review is requested.

You are the independent reviewer for translations another agent wrote. Read the translator brief at
/home/zp/Code/blocknet/seine-i18n/site/editorial/translation-terms/_translator-brief.md
first: its worktree rules, "Read first" list and language rules apply to you too.

## For each post in your task
Read `src/content/blog/<slug>/index.mdx` and `<slug>/<code>.mdx` side by side, paragraph by paragraph,
including front matter, FAQ, `<Answer>`/`<Note>`/`<Warning>`, the CTA attributes, tables and alt text.
Fix directly in the translation file:
- Meaning: mistranslations, wrong numbers or units, changed hedges ("about", "up to", "roughly"),
  wrong subject/object, and technical errors (stealth addresses, ring signatures, Argon2id, pools).
- Omissions and additions: every sentence and claim of the English must be there, nothing extra.
- Protected values: numbers, chip/product names, commands, flags, code blocks, URLs, `@name`,
  lowercase "seine". Internal links use the locale prefix and point at existing slugs.
- Tone: favorable and plain, like the English. No local words for "anonymous", "untraceable",
  "most private", "passive income", "guaranteed profit"; no added caveats or negatives; threads,
  never "workers".
- Fluency: it must read as written by a native speaker for crypto miners, not as a translation.
  Rewrite stiff or literal sentences. Use the terms local crypto readers search for.
- Terminology: consistent with editorial/translation-guide.md, src/i18n/messages/<code>.json and the
  shared terms file for the locale. If two halves chose different terms, use the terms file's
  entry and mention the conflict in your report.
- Search: the title and description should contain what a native speaker would type into Google for
  this topic, within the length budget.
Then set `translation: reviewed` (leave sourceHash alone) and run
`node scripts/check-content.mjs <slug> --locale <code> --strict`; it must pass. Edit only your
posts' `<code>.mdx` files.

## Report
Per post: the substantive fixes (meaning, omissions, additions, terminology), not typo-level edits,
and the final check result. Say plainly if any post still has a problem you couldn't resolve.
