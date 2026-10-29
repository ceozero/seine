# Seine benchmark navigation

Benchmark chart names link to the existing hardware guide. Its localized section links work without JavaScript. This static feature has no loading, error, empty or disabled state.

Open `index.html` for reviewed captures, with exact source hashes in
`source-revision.json`. These are real components with synthetic pool fixtures
or the built Seine site. No private wallet data is included.

Run `python3 -m http.server 8795 --directory site/showcases/seo-navigation`
from the repository root, then open http://localhost:8795/ for the gallery.
Run `npm --prefix site run build` and preview `site/dist` for the real pages.

Verified: all four section anchors resolve, chart links retain the selected
language, no overflow at desktop/mobile, nine tests pass, all 20-language content
checks and production asset-size budgets pass. No benchmark numbers changed.
