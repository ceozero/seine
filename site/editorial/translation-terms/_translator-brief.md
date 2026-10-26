# Blog translation brief (seineminer.com)

Worktree: /home/zp/Code/blocknet/seine-i18n/site (branch claude/i18n-20). Several agents work in this
worktree at the same time on different files. Edit only the files your task names, plus the shared
terms file below. Don't run `npm run build`, don't run git commands that change state (no commit, stash,
checkout or reset), and don't touch index.mdx, zh-Hans.mdx or zh-Hant.mdx files.

## Read first
1. `editorial/translation-guide.md`: the rules and glossary. Follow it exactly.
2. `editorial/writing-guide.md`: the copy must stay favorable to Blocknet, bntpool.com and seine.
   Nothing negative, no caveats the English doesn't have, no profit verdicts.
3. `src/i18n/messages/<code>.json`: this locale's interface strings. Match their wording for
   shared terms (Download, threads, pool, and so on).
4. A finished example: `src/content/blog/how-to-mine-blocknet/index.mdx` next to its `zh-Hans.mdx`
   (front matter shape, FAQ quoting, CTA, localized links).
5. The shared terms file for your locale (path in your task). Before choosing a rendering for a
   recurring technical term that the guide's glossary doesn't cover (e.g. "commitment",
   "view key", "output", "confirmation", "difficulty", "memory-hard", "daemon", "stealth address",
   "range proof", "dashboard", "@name"), check the file and reuse what's there. If it's not listed,
   choose the form native crypto readers search for and append one line: `English -> rendering`.
   Another agent translating the other half of the posts into the same language reads it too.

## Per post
1. Read `src/content/blog/<slug>/index.mdx` in full.
2. Write `src/content/blog/<slug>/<code>.mdx`:
   - Front matter keys, in this order: title, description, tags, faq, sourceHash, translation.
     No date, updated, related, draft or image. Optional `seoTitle` only if the translated title
     is far too long for a search result (CJK/Thai: about 30 characters).
   - Quote title/description in YAML single quotes if they contain `:` or start with a special
     character; FAQ q and a always in single quotes, one line each, `''` for an apostrophe.
   - `sourceHash`: output of `node scripts/check-content.mjs --hash <slug>`.
   - `translation: draft` (a separate review is optional; only an actual reviewer changes it to `reviewed`).
   - Body: same headings (count and order), same `<Answer>`, `<Note>`, `<Warning>` and one `<CTA>`
     (translate its title and text attributes, keep `target`, no ASCII `"` inside), same tables,
     same images (translate alt text), code blocks byte-identical. Internal links take the locale
     prefix: `/blog/x/` -> `/<path>/blog/x/`, `/#download` -> `/<path>/#download`. External links
     identical.
3. Run `node scripts/check-content.mjs <slug> --locale <code>`. All checks must pass. A separate review is no longer required for publishing.

## Language
Numbers in prose take the locale's separators (see translation-guide.md rule 3); code and commands don't.
Write as a native speaker writing for miners and crypto users in that language: natural, plain,
literal, favorable. Translate meaning, not word order. Keep exactly: number values and units, chip and
product names, commands, flags, file names, URLs, addresses, `@name`, lowercase "seine", "bntpool.com",
"Blocknet", "BNT", "Argon2id", "Faraday". Never write the local words for "anonymous",
"untraceable", "most private", "passive income" or "guaranteed profit"; Blocknet is "private".
CPU threads are threads, never "workers". Don't add or drop claims.

## Report
When done: the slugs you finished, every check result, and any passage you were unsure about.

## Scratch files
Keep any helper scripts or backups in your own folder,
/tmp/i18n-work/<code>-<A or B>-<translate or review>/,
never in a folder another agent might use.

## German-specific
In German, lowercase "seine" can read as the pronoun ("his/its"); reword so the product name is
unambiguous (e.g. "der Miner seine", "mit seine").
