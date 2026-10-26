# Windows guide and hardware evidence — 2026-10-25

## Search jobs

- `/blog/mine-blocknet-on-windows/`: a native Windows ZIP → checksum → PowerShell → accepted-share walkthrough. The general mining guide remains the cross-platform owner; the huge-pages guide owns detailed page setup. No Windows tuning or antivirus keyword permutations are added.
- `/blog/blocknet-mining-hardware-hashrate/`: improve the existing hardware owner with a reproducible full-socket measurement. Do not create a competing benchmark article.

Search Console reports are still processing; these choices fill a documented setup gap and strengthen first-party evidence, not an invented traffic or query-volume forecast.

## Windows evidence

Read at `seine@f96abd9` (v0.2.25):

- `docs/guides/configuration.md:8-28`: first-run address/shortname, default Stratum endpoint, all available backends, CPU sizing, saved configuration location.
- `docs/guides/configuration.md:66-88`: quit controls, Windows error handling, shortname resolution once per run.
- `docs/guides/windows-large-pages.md:3-31`: automatic fallback, Lock pages in memory, sign-out requirement, supported Windows editions and page modes.
- `docs/guides/windows-large-pages.md:41-44` and `.github/workflows/release.yml:83-110`: Windows ZIP bundles the CUDA 12.8.61 NVRTC DLLs. Keep them beside the executable; the separate Toolkit is unnecessary.
- `.github/workflows/release.yml:138-158`: published SHA256SUMS.txt covers release archives, distinct from the file manifest inside each archive.
- https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/get-filehash : Get-FileHash and SHA256. Read 2026-10-25.
- https://support.microsoft.com/en-us/windows/zip-and-unzip-files-8d28fa72-f2f9-712f-67df-f80cf89fd4e5 : File Explorer Extract All. Read 2026-10-25.
- `site/editorial/fact-sheet.md` §§1,3,4: 2 GiB per CPU mining thread; pool share accounting and payout distinction; NVIDIA support.

The image is a real shared-Chrome capture of `https://seineminer.com/#download` at 1200×900, showing the v0.2.25 Windows ZIP. It is not a fabricated miner screen. This task did not run a miner or change Windows privileges.

## Benchmark evidence

`experiments/amd-page-size-20261025/RESULTS.md`, checked at `f96abd9`:

- EPYC 9355P, 32 cores / 64 hardware threads, one socket / NUMA node.
- 192 GiB across twelve populated DDR5-4800 channels.
- Fixed 64 mining threads, streaming kernel, automatic affinity, thread autotuning disabled, explicit 1 GiB pages, configured package cap 280 W.
- **68.256 completed H/s** (68.3 rounded), ratio of total completed hashes to total invocation seconds across four fresh 120-second runs. Startup, mapping, hashing, fences and teardown counted; page-pool preparation and settling outside the interval.
- Frozen executable SHA-256 `a4d3bd3b1091102b9d50b8d5c80aed057e8d30534ddcfee742b1d69ec137f6dc`; prepared source `28191b798b8dc18fdf6ebcaf44fd549b35264870`, unchanged runtime from `d92abe5872bf215a2f001af4e3891c4afa1a3fcc`.
- Published `benchmark-records.json` supplies raw numerators/denominators, configuration and variability. Do not call this a v0.2.25 measurement merely because that is today's release.
- This is a manual result. It does not establish the automatic default, whole-wall electricity usage, cross-host variability or a combined power-cap/page-size gain.

The older 49.39 H/s EPYC 9R45 cloud measurement remains accurately labeled as cloud data. Its 16-versus-32-thread reasoning is retained. The Mac measurements have separate settings. Source: `experiments/readme-hardware-20261025/README.md`, `summary.json`, `docs/PERFORMANCE.md`.

## Publishing policy

Owner authorized proceeding, shipping translations without mandatory independent reviewers, and deploying the pool API/UI with `--api-only`. Translations are honestly marked `translation: draft`; structural/content checks and visual checks still apply. This batch edits no miner runtime or Stratum service.
