# Linux installation guide evidence

Verified October 26, 2026 (EDT). Source article: `mine-blocknet-on-linux`.

- Official release: https://github.com/zpalmtree/seine/releases/tag/v0.2.26
- Tag commit: `899ff7ea8bd547163ae48d636f569a0a8c7e25bb`.
- Published October 25, 2026, 5:30:27 PM EDT.
- Release workflow at that commit builds x86_64 with NVIDIA and aarch64 with CPU only.
- Configuration source: https://github.com/zpalmtree/seine/blob/v0.2.26/docs/guides/configuration.md
- NVIDIA source: https://github.com/zpalmtree/seine/blob/v0.2.26/docs/guides/nvidia.md
- NVRTC runtime/builtins: https://docs.nvidia.com/cuda/nvrtc/
- Both official Linux binaries were checked with readelf in the previous accuracy
  batch and require GLIBC_2.39. This article pins that statement to v0.2.26 and asks
  readers to recheck later releases. CUDA installation cannot add a missing backend.

## Archive and command verification

Official release-level SHA256SUMS.txt matches:

- x86_64: `9ce8abaeb585dec7c93651eb35f518fe63b25e845591b59642c0dd0850dea8be`
- aarch64: `d63ba08d5dd7f7b4d699783e0b718f1636220faa8917f40540d6c9f5de45806e`

The x86_64 archive was rehashed in this batch, extracted into an isolated temporary
folder, given owner execute permission and run with `--help` only. Exit 0 and backend
option verified. The archive contains ./seine, SHA256SUMS.txt, SEINE-LICENSE.txt,
README.md and PRIVACY.md at its root. The inner manifest covers extracted files;
readers compare the archive against the separate release-level manifest.

No mining, GPU workload, hardware rental or system setting change was performed.

## Image and links

`site/public/assets/blog/linux-download.png` is a real official download table,
captured through the shared Windows Playwright MCP on October 26, 2026, around
2:01 AM EDT. Windows detection on that browser is expected; Linux archive rows
are shown. No fabricated product screenshot. The download page links to this guide
in all 20 languages; the general guide has a reciprocal related-article link.
The existing general guide changed only related metadata; translation hashes were
refreshed without changing translated prose or review status.

## Translation policy

English plus all 19 supported locales. Translated with the active models, no external
translation API. Translation status remains draft; no independent linguistic review
is claimed. Owner authorized publishing without a reviewer gate. Automated checks,
protected code/link checks, build and browser verification remain required.

## Build and browser validation

Strict content checks passed in all 20 languages; the full site content/release/benchmark
checks and all three existing release-fact tests passed. The live release check still
matched v0.2.26. Local HTML audit covers all 20 article URLs and their metadata,
canonical/hreflang links, FAQ/schema, images and fragment destinations.
Desktop and mobile English, Arabic and Thai were visually inspected through Windows
Playwright. Code blocks scroll within their containers; the page does not overflow.
The download screenshot declares intrinsic dimensions and lazy loading.
The list template previously hid custom images; it now chooses the supplied thumbnail
or the existing generated card so this article keeps its real screenshot in list rows.
Showcase: http://localhost:8874/linux-and-luck/ (source revisions and live checks there).
