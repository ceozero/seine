# Windows download verification guide — October 25, 2026

## Reader task and scope

`/blog/antivirus-flags-crypto-miner/` owns identifying a Windows download warning,
checking the exact official archive and reporting an unresolved detection.
The Windows setup guide retains normal installation and its short checksum step;
the NVIDIA guide retains runtime and device setup. Both now link here in all
20 languages. No antivirus alert for seine was observed or invented for this
article, and no scan verdict or false-positive claim is made.

The owner authorized writing, translating, checking and publishing this guide.
Translations were produced by the active model without external translation
services or subagents. They remain `translation: draft`; no independent review
is claimed.

## Primary references

Checked October 25, 2026:

- Microsoft Protection History: https://support.microsoft.com/en-us/windows/security/windows-security/protection-history-in-the-windows-security-app
  — expand entries, identify affected files, administrator access for details,
  quarantine and item-specific actions. The article keeps protection enabled
  and does not treat a matching checksum as permission to bypass a detection.
- Microsoft SmartScreen reputation: https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation
  — file/publisher reputation differs from a named antivirus detection.
- Microsoft classification criteria: https://learn.microsoft.com/en-us/defender-xdr/criteria
  — cryptomining software appears in PUA criteria for enterprise environments;
  the article preserves that scope and defers managed-device policy to admins.
- Microsoft Get-FileHash: https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/get-filehash?view=powershell-7.5
  — SHA-256 file integrity comparison. The guide supplies its own exact-entry
  comparison rather than asking readers to compare a visually truncated hash.
- Microsoft file submission: https://www.microsoft.com/en-us/wdsi/filesubmission
  — suspected incorrect detections can be submitted for analysis. No submission
  or external message was made during this task.
- Official release: https://github.com/zpalmtree/seine/releases/tag/v0.2.26
  — `seine-windows-x86_64.zip` and separate `SHA256SUMS.txt` release assets.
- `.github/workflows/release.yml:105-110` and `:138`
  — extracted-file manifest inside Windows ZIP versus release archive checksums.

## Actual Windows verification

Downloaded the official v0.2.26 ZIP and separate checksum asset with `gh release
download`. Ran the article's comparison in native Windows PowerShell 5.1.26100.7920.
No miner was executed and no Windows security setting was changed.

Archive SHA-256 (also matches the GitHub release asset digest):

`75adac2aa25626b547f18e85b4ff20e4b6a9cf2872bc641ca2220229ffa364a5`

The public transcript at `/assets/blog/seine-v0.2.26-verification.txt` records the
actual computed and expected hashes, PowerShell version and ZIP entries. The
archive contains `seine.exe`, two NVRTC DLLs, licenses, documentation and its own
`SHA256SUMS.txt` manifest. This verifies archive identity, not malware absence.

`checksum-tests.json` records executions of the exact published snippet against
four task-local manifest cases. The authentic manifest succeeds; wrong hash,
missing entry and duplicate entry each exit 1 without a success message. The
original manifest was restored after tests.

## Images

- `/assets/blog/seine-release-assets.png`: actual GitHub v0.2.26 expanded Assets
  element captured through Playwright MCP in shared Windows Chrome.
- `/assets/blog/seine-checksum-result.png`: Playwright capture of the actual
  PowerShell output rendered as a plain transcript. The caption explicitly says
  this is not a Windows Security notification. No private paths or credentials
  appear in either image. Both captures were visually reviewed.

## Content checks

Strict checks pass for 26 English articles and 494 translations. All protected
code blocks and external links match their source. The overlap report shows
0.1% shared eight-word phrases with the NVIDIA guide, 0.0% with other nearest
matches; distinct intent is recorded in the keyword map.

Showcase: http://localhost:8874/download-verification.html

Startup: `python3 -m http.server 8874 --directory /home/zp/Code/blocknet/showcases/blog-i18n`

Production build passed: 562 pages and 561 sitemap URLs. All 20 new routes have
self-canonicals, 21 hreflang entries, RSS/blog-list/sitemap inclusion, FAQ and
BlogPosting schema and both localized setup backlinks. Audited 840 internal
links/assets. Reviewed 12 desktop/mobile captures across English, Arabic and
Thai: no page overflow, all images loaded, code remains left-to-right.
