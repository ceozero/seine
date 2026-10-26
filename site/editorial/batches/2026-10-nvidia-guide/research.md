# NVIDIA setup guide — evidence and publication

October 25, 2026. The owner authorized finishing and publishing this guide with a
real NVIDIA mining capture, a GPU-only/CPU-plus-GPU comparison and all 20 languages.
This dated setup article adds fresh measurements; it does not revive the older
WSL result removed from hardware-buying copy or make a card-purchase recommendation.

## Reader job and overlap

Help a Windows or Linux x86_64 user prepare the NVIDIA runtime, choose CPU-plus-GPU
or GPU-only mining, select a device, and verify the NVIDIA backend's accepted work.
The Windows article owns ZIP verification and first-run Windows setup. The dashboard
article owns the complete panel tour, and bntpool.com's tracking guide owns missing
pool credit. This guide links to those owners and adds NVIDIA-specific selection,
diagnosis and one named desktop's measured mode comparison. The Windows article's
related links now point back here; its translation hashes changed only because
that inherited metadata changed.

Search demand remains unverified. This work does not establish a traffic winner
while Search Console collects its first data. No RTX 4090 result or unmeasured
card compatibility/performance table is asserted.

## Source ledger


| Claim | Evidence |
|---|---|
| Windows/Linux x86_64 release names and NVIDIA package requirements | `README.md:39–47`; `docs/guides/nvidia.md:20–33` |
| Packaged Windows DLLs, CUDA 12.8.61 runtime | `.github/workflows/release.yml:83–103`; `Cargo.toml:28` pins the CUDA 12.8 loader |
| Default CPU plus detected NVIDIA selection; explicit backend lists | `src/config.rs:373–386,1475–1507`; `docs/guides/nvidia.md:3–16` |
| Comma-separated backend/device flags | `src/config.rs:373–386`; released v0.2.26 `--help`, lines 54–64 |
| NVIDIA autotune cache filename and data directory | `src/config.rs:130,370,513–515,1155–1158`; `docs/guides/nvidia.md:35–41` |
| GPU lane arena, available-memory budget and allocation checks | `src/backend/nvidia.rs:530–585,2874–2882,2929–2940,3350–3358`; existing fact-sheet current Argon2id memory parameter |
| Device rows, startup progress, per-backend share messages | Published `seine-dashboard-explained`, especially Devices and log sections; existing fact-sheet dashboard evidence |
| Driver download | https://www.nvidia.com/en-us/drivers/ (checked October 25) |
| NVRTC runtime compilation and matching builtins library | https://docs.nvidia.com/cuda/nvrtc/ (checked October 25); platform-specific packaging claims come from the release workflow, not the latest CUDA docs |
| Article images | Existing real download-page capture `/assets/blog/windows-download.png`; new `/assets/blog/nvidia-rtx5090-session.png` captured from actual release-terminal output through the shared Windows Chrome Playwright MCP |

## Release and real mining capture

- Official release: [v0.2.26](https://github.com/zpalmtree/seine/releases/tag/v0.2.26),
  published October 25, 2026, 5:30:27 PM EDT and still the latest release at the
  final preparation check. Both Windows and Linux archives were checked against
  the published SHA256SUMS.txt; Windows contains the two documented NVRTC DLLs.
- The Windows executable SHA-256 is
  `0fb37314c3add88be978303e1f1d624e2d7dd28ccc6393e9e213e818cc174320`.
  Its benchmark metadata reports build commit `899ff7ea8bd5` and source fingerprint
  `fb543f76ec54c9c0`; retain those binary-emitted identifiers alongside the release tag.
- Native Windows 11 Pro N, build 26200; NVIDIA GeForce RTX 5090 with driver 610.88;
  AMD Ryzen 9 9950X3D; 125.4 GiB usable RAM. Windows Balanced power plan.
- The live session began at 5:59:50 PM EDT in a fresh task-specific data directory without tuning caches,
  using the existing payout address and bntpool.com. Backend, CPU-thread, GPU-lane,
  kernel and register-cap choices were automatic. Telemetry was opted out for this
  temporary capture/measurement directory.
- NVIDIA cold initialization took 236.9 seconds and selected 13 lanes. The log
  confirmed `accepted (backend=nvidia#1)` at 308.39 seconds. The frozen frame at
  about 5 minutes 09 seconds shows 17.79 H/s current total, CPU 9.84 H/s, NVIDIA
  7.95 H/s, 10 accepted shares and zero rejected. These transient display values
  are screenshot evidence, not the paired benchmark results.
- A native Windows ConPTY session captured the actual ANSI stream. It was replayed
  faithfully in xterm.js and captured through Playwright MCP in shared Windows
  Chrome. The screenshot crops the real header, hashrate, network, mining and
  device panels; wallet/configuration and logs are excluded. No displayed value
  was drawn, replaced or generated. The private full terminal capture is not
  committed. Linux runtime requirements are verified from source/CLI documentation;
  the mining session and measurements here ran on native Windows only.

## Measurement protocol

All GPU work ran inside a `gpuq` exclusive admission job, normal priority, hold
while gaming, fail on preemption. The preceding Blender job completed before
admission. Other desktop applications stayed open; no user process was closed and
no system power or driver setting was changed. Preflight recorded about 4.6 GiB of
GPU memory already allocated, 6% GPU utilization, about 46.5 GiB available system
RAM, and 42.1% pagefile usage. These results describe that desktop session rather
than an isolated maximum-throughput measurement.

`scripts/benchctl.py run` wrapped a native Windows Python harness for the verified
release executable. The shell-only `bench_nvidia_ab.sh` fixes the backend to NVIDIA;
this adapter compared `nvidia` and `cpu,nvidia` while preserving its interleaved
pair design. Order: A/B, B/A, A/B, where A is GPU-only and B is CPU-plus-GPU.
Each run used one 20-second warmup and three 20-second measured rounds, followed
by a 20-second pause. GPU device 0 and the same NVIDIA autotune cache were used
throughout. No thread, lane, kernel or register-cap overrides were supplied.
Each invocation resolves its automatic CPU configuration at startup, including
compatible cache reuse; the choice is recorded in each report. Startup/tuning time is outside the measured backend rounds.

Per-run flags, with MODE either `nvidia` or `cpu,nvidia` and a unique report path:

```powershell
.\seine.exe --data-dir DATA --telemetry off --ui plain --bench --bench-kind backend --bench-secs 20 --bench-rounds 3 --bench-warmup-rounds 1 --backend MODE --nvidia-devices 0 --bench-output REPORT.json
```

Published H/s is the arithmetic mean of the three report `avg_hps` values per mode.
Each report uses the miner's counted-window/end-fence accounting; late hashes are
recorded separately. `scripts/benchctl.py compare` analyzes the three paired means.
The raw reports retain their effective settings and per-round backend counters;
only the desktop hostname was removed. No payout address, API token or private
terminal log appears in these files.

All six invocations succeeded. Every requested backend remained present; per-round
reports show zero dropped events and no assignment/control timeouts. GPU lanes
remained 13. The combined runs selected 6, 7 and 7 CPU threads with regular Windows
pages; the automatic GPU cache selected register cap 208, no block-loop unroll and
one hash per launch per lane. No manual tuning override was introduced.

| Pair | Order | Mode | CPU threads | Mean H/s |
|---|---|---|---|---|
| 1 | 1 | GPU only | — | 7.535268 |
| 1 | 2 | CPU + GPU | 6 | 13.324236 |
| 2 | 1 | CPU + GPU | 7 | 12.543875 |
| 2 | 2 | GPU only | — | 7.114533 |
| 3 | 1 | GPU only | — | 7.365645 |
| 3 | 2 | CPU + GPU | 7 | 12.777343 |

Across the three runs per mode: GPU-only **7.338482 H/s**; CPU-plus-GPU
**12.881818 H/s**. The article rounds these to **7.3** and **12.9 H/s**.
The paired geometric difference was +75.531%, with the three-pair bootstrap interval
+73.472% to +76.825%; sample CVs were 2.88% and 3.11%. This is a descriptive comparison
of this desktop/session, not a general estimate across other GPUs or systems.

Evidence: [raw runs and host/capture record](measurements/),
[paired input](measurements/results.tsv), and
[full comparison](measurements/comparison.json). Postflight returned to 6% GPU
utilization and 3583 MiB allocated; the admission job completed successfully and
its temporary miner processes exited. No persistent miner or control API remains.


## Verification and publication

- Strict checks pass for all 25 English articles and their 475 translations.
  All 19 new translations retain `translation: draft`; separate review is optional
  and no independent linguistic review is claimed. Protected commands, links,
  numbers, components and structure were checked.
- Wording overlap for the new article: 0.0% shared eight-word phrases in the
  reported nearest posts. Intent boundaries are recorded in the keyword map.
- Production build: 542 pages. All 20 new article routes have the expected
  canonical, 21 language alternates, four FAQ entries, RSS/sitemap inclusion and
  a backlink from the localized Windows guide. 840 local links/assets passed;
  sitemap contains 541 URLs.
- Shared Windows Chrome via Playwright MCP: English, Arabic and Thai at
  1440 × 1000 and 390 × 844, no horizontal document overflow, every image loaded,
  all command blocks left-to-right. Sixteen desktop/mobile captures visually
  reviewed, including article headings, measured tables, the real session image
  and the language menu. Outside-click and Escape dismissal pass at both widths.
  English, Greek and Simplified Chinese social cards visually reviewed.
- Stable showcase: http://localhost:8874/nvidia-guide.html. Start it with
  `python3 -m http.server 8874 --directory /home/zp/Code/blocknet/showcases/blog-i18n`.
  The gallery's verification record identifies the final content revision.
- No task-owned miner or control API listener remained after measurement. Removed
  the temporary control cookie, copied payout settings and private raw capture
  files after exporting the cropped screenshot and nonprivate evidence.
