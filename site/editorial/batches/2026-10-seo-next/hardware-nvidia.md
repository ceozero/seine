# NVIDIA evidence in the hardware guide

Updated October 25, 2026. The existing hardware guide owns hardware selection and
per-chip results. It now includes the RTX 5090 measurements already published in
the NVIDIA setup guide, with the same test method and source link. The NVIDIA
guide continues to own runtime setup, device selection and troubleshooting.

## Evidence and localization

- Source: `batches/2026-10-nvidia-guide/research.md` and its
  `measurements/comparison.json` and six raw benchmark reports.
- GPU-only arithmetic mean: 7.338482012985509 H/s, displayed as 7.3 H/s.
- CPU-plus-GPU arithmetic mean: 12.88181795466018 H/s, displayed as 12.9 H/s.
- Native Windows 11, RTX 5090, Ryzen 9 9950X3D, 125.4 GiB usable RAM,
  seine v0.2.26, NVIDIA driver 610.88, automatic settings. Three interleaved
  pairs; each run has one 20-second warmup and three measured 20-second rounds.
- This is a separate section from the cloud, Mac and manual EPYC measurements.
  The original desktop/session scope and local benchmark distinction remain.
- Reused the exact published measurement section in every locale, preserving
  numbers, commands and evidence links. Updated all 19 source hashes. No new
  translation or independent review is claimed.
- The existing NVIDIA reference now links to the localized setup article;
  related reading also includes it in every locale.

## Verification

Strict content checks pass for all 25 posts and their 475 translations.
Wording overlap is 8.2% with the NVIDIA guide, from intentionally shared
measurement evidence; the articles retain distinct reader tasks. Existing
overlap with the CPU and old-PC guides does not change their ownership.

Visual showcase: http://localhost:8874/hardware-nvidia.html

Startup: `python3 -m http.server 8874 --directory /home/zp/Code/blocknet/showcases/blog-i18n`

Production build: 542 pages. Audited all 20 updated routes, canonical URLs, 21
hreflang entries per page, sitemap/RSS inclusion, FAQ and BlogPosting schema,
and 900 internal links/assets. Desktop (1440 × 1000) and mobile (390 × 844)
checks pass for English, Arabic and Thai with no page overflow. All six
captures were visually reviewed; no site console errors were reported.
