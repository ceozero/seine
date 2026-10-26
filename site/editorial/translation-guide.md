# Translation guide

Every published post exists in English and 19 translations, the same set as the Sol Incinerator
site: id, es, de, fr, pt-BR, ru, it, pl, tr, vi, ar, nl, uk, el, ja, ko, th, zh-Hans, zh-Hant.
A translation sits beside its source as `src/content/blog/<slug>/<locale>.mdx` (for example
`pt-BR.mdx`), and the build fails if one is missing or stale. The bntpool.com blog uses
the same rules with `.md` files.

## How to translate

1. Translate with the active model. Don't call external translation APIs.
2. Translate meaning, not word order: write as a native speaker writing for miners and crypto users
   in that language. Plain, literal and favorable, the same as the English (see
   `writing-guide.md`). Don't add claims, caveats or marketing, and don't drop any.
3. Keep exactly: units (H/s, GB, GiB, BNT), chip and product names, commands, code blocks, file
   names, flags, URLs, `@name`/`$name`, addresses, and lowercase "seine". Keep every number's
   value, but write numbers in prose with the locale's separators, so "6,000 BNT" can't be read
   as six: es, pt-BR, de, it, id, tr, vi, nl, el `6.000` and `16,8`; fr, ru, uk, pl `6 000` and
   `16,8` (no-break space); ar, ja, ko, th, zh keep `6,000` and `16.8`. Numbers inside code blocks,
   inline code, commands and quoted program output stay byte-identical. Years, versions (0.2.23),
   model numbers (RTX 4090) and four-digit numbers in Spanish and Polish (`2048`) get no separator.
   Dates in prose use the local form (de `16. Februar 2027`, pt-BR `16 de fevereiro de 2027`,
   ja/zh `2027年2月16日`, ko `2027년 2월 16일`), not the English ISO `2027-02-16`.
4. Front matter: translate `title`, `description` (aim for the same length budget, roughly
   140-160 characters in Latin scripts and 60-90 characters in CJK), `tags` and every FAQ `q`/`a`
   (one line of plain text each, in YAML single quotes; double any `'` inside). Keep the same number
   of FAQ entries. Add `sourceHash` (`npm run check -- --hash <slug>`) and `translation`.
5. Body: same headings, same `<Answer>`, `<Note>`, `<Warning>` blocks and one `<CTA>` (translate
   its `title` and `text`, keep `target`; avoid ASCII double quotes inside them), same tables, same
   images (translate alt text). Internal links get the locale prefix (`/es/blog/<slug>/`,
   `/pt-br/#download`); external links stay identical.
6. A separate review is optional, not a publishing gate (owner decision, 2026-10-25). Keep
   `translation: draft` when there has been no separate review; automated checks still require
   complete, current translations with matching structure and protected code/links. If a separate
   review checks meaning, omissions, additions, terminology and protected values, record
   `translation: reviewed`. Never claim an independent review that did not happen.

## Glossary

Use the term the local crypto-mining community uses. When unsure, prefer the form people would
type into a search engine.

| English | Usual rendering |
|---|---|
| mining / miner | id penambangan / penambang; es minería / minero; de Mining, minen / Miner; fr minage / mineur; pt-BR mineração / minerador; ru майнинг / майнер; it mining / miner; pl kopanie (wydobywanie) / koparka (program: miner); tr madencilik / madenci; vi đào coin / thợ đào (phần mềm đào); ar التعدين / المعدِّن; nl minen / miner; uk майнінг / майнер; el εξόρυξη / miner; ja マイニング / マイナー; ko 채굴 / 채굴기 |
| mining pool | id pool penambangan; es pool de minería; de Mining-Pool; fr pool de minage; pt-BR pool de mineração; ru майнинг-пул; it pool di mining; pl pula wydobywcza (pool); tr madencilik havuzu; vi pool đào; ar مجمع التعدين; nl miningpool; uk майнінг-пул; el mining pool; ja マイニングプール; ko 채굴 풀 |
| hashrate | id hashrate; es tasa de hash (hashrate); de Hashrate; fr taux de hachage (hashrate); pt-BR hashrate; ru хешрейт; it hashrate; pl moc obliczeniowa (hashrate); tr hash gücü (hashrate); vi tốc độ băm (hashrate); ar معدل التجزئة; nl hashrate; uk хешрейт; el hashrate; ja ハッシュレート; ko 해시레이트 |
| thread (CPU) | id thread; es hilo; de Thread; fr thread; pt-BR thread; ru поток; it thread; pl wątek; tr iş parçacığı (thread); vi luồng; ar خيط المعالجة; nl thread; uk потік; el νήμα; ja スレッド; ko 스레드 |
| share / block / payout | translate normally (ru шара / блок / выплата; ja シェア / ブロック / 支払い; ko 셰어 / 블록 / 지급) |
| privacy coin | es moneda de privacidad; de Privacy Coin; fr cryptomonnaie de confidentialité; pt-BR moeda de privacidade; ru монета конфиденциальности (приватная монета); ja プライバシーコイン; ko 프라이버시 코인 |
| ring signature / stealth address | ru кольцевая подпись / стелс-адрес; ja リング署名 / ステルスアドレス; ko 링 서명 / 스텔스 주소; es firma de anillo / dirección sigilosa; de Ringsignatur / Stealth-Adresse |
| seed (recovery) phrase | ru сид-фраза; ja シードフレーズ; ko 시드 문구; es frase semilla; de Seed-Phrase; fr phrase de récupération |
| huge pages | ru huge pages (большие страницы); ja ヒュージページ; ko 휴즈 페이지; es páginas grandes (huge pages); de Huge Pages |
| kernel (CPU code path) | a software kernel, not cores: ru вычислительное ядро (kernel); ja カーネル; ko 커널; zh-Hans 计算内核; zh-Hant 運算核心程式 |

Arabic is written right to left; the site sets `dir="rtl"`. Keep Latin names, numbers and code as
they are inside Arabic text. Use Brazilian conventions for pt-BR.
