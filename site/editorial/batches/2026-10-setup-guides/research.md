# Platform setup guides, 2026-10-28

## Reader job and site ownership

Improve the existing Windows, Linux and Mac URLs: download → extract → launch →
receiving address → accepted shares → My Stats in the reader's language. No new
keyword variant pages. Seine owns installation and hardware; bntpool owns worker
activity, shares, balances and payouts. All 20 languages receive the same flow.
The owner explicitly requested removing archive verification from normal setup.
Security-specific troubleshooting remains available in its existing article.

## Source evidence

- Reviewed source revision: `2c40c7b725f4ff1464205c09763149efe895e3e7`.
- `src/config.rs`, `resolve_first_run_pool_inputs`: public address/registered
  shortname, default `stratum+tcp://bntpool.com:3333`, automatically generated pool
  worker name. There is no interactive rig-name step.
- `docs/guides/configuration.md`: saved configuration is
  `seine-data/seine.config.json` relative to the working directory by default.
- Latest published release during research: [v0.2.44](https://github.com/zpalmtree/seine/releases/tag/v0.2.44),
  published October 27, 2026, 10:10:12 PM EDT. The source tree already identifies
  itself as v0.2.45; that is the version on the renderer fixture, not a claim that
  v0.2.45 binaries were published at capture time.
- Downloaded both Linux release archives. `readelf --version-info` reports highest
  required glibc symbol version `GLIBC_2.39` for each. Both archives extract `seine`
  at their root with mode 755. Ordinary extraction therefore preserves execute
  permission. No benchmark or mining session was started.
- [Apple's identification instructions](https://support.apple.com/en-us/116943):
  About This Mac identifies Apple Silicon under Chip and Intel under Processor.
  Separate macOS aarch64/x86_64 assets are present in the release.
- Mac benchmark figures and July 10 measurement conditions are retained; this
  change supplies no new hardware measurements. Corrected the 64 GB FAQ ceiling
  from 30 to 31 to agree with the existing table: (64 − 1) / 2, rounded down.

## Images

- `setup-prompts*.webp`: actual v0.2.44 Linux executable in a private PTY. Supplied
  the illustrative `@yourname` input and stopped at the pool prompt, before
  shortname resolution, network startup or mining. Actual terminal output replayed
  in xterm.js, captured through the shared Windows Playwright MCP. Mobile wraps
  the identical stream at 44 columns; no prompt text was rewritten.
- `setup-accepted-shares*.webp`: real Ratatui dashboard renderer using explicitly
  synthetic data. `dashboard-fixture.rs` is the reproducible ignored-test body:
  append temporarily to `src/miner/thread_showcase.rs`, run
  `cargo test --no-default-features export_setup_guide_dashboard -- --ignored`,
  then remove the appended body. It calls the existing TestBackend capture helper;
  no mining, GPU inference, wallet, or network is started. Desktop shows the top
  dashboard panels; mobile uses the actual compact renderer. Both image labels
  and all 20 captions identify example data; numbers are not performance evidence.
- `setup-download.webp`: current real homepage download section, including the
  platform setup links and published release. Shared Windows Playwright capture.
- PNG browser captures converted to WebP; no generated replacement UI or values.
  No secrets or private account information are present in the captures.

## Validation notes

The content checker permits only the matching locale's `?lang=` on My Stats;
foreign locale queries still fail external-link parity. Code blocks and MDX block
counts must match English. Shorter Linux copy is intentional: the owner's setup
request takes priority over the editorial word-count target. Pool-worker warnings
are legitimate pool identity usage. Shared wording across OS guides describes
identical prompts and share checks; archive, shell and troubleshooting instructions
remain platform-specific. No new overlapping search intent was introduced.

Showcase: http://localhost:8874/setup-guides/ (desktop/mobile article captures and
responsive terminal images). Static articles have no loading, empty or disabled
application state; error troubleshooting remains ordinary article content.

## Publication-time release check

v0.2.45 was published during this task on October 28, 2026, at 3:45:27 PM EDT.
All four pinned release source files and the five archive names are unchanged
from v0.2.44. Updated the reviewed release identity and verified it against GitHub.
The prompt and download screenshots retain their capture-time v0.2.44 provenance.

## Completed validation

- Content, source-hash, code-block and link parity checks: all 61 articles pass.
- Release-fact tests: 5 passed; live manifest check: v0.2.45 verified.
- Final production build, performance budgets and cover checks passed.
- Shared Windows Chrome: all 60 revised pages rendered at 390 px; no horizontal
  overflow, one H1, 21 hreflang alternatives, matching-language My Stats URLs,
  loaded mobile screenshots, no checksum commands in normal setup.
- Desktop/mobile visual review: Windows, Linux and Mac in English, Arabic Mac
  and Thai Windows; no browser console errors in the completed-build checks.
