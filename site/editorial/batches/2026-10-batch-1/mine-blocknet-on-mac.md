# mine-blocknet-on-mac: research notes

Writer notes for `src/content/blog/mine-blocknet-on-mac/` (batch 1, 2026-10-25).

## Intent

A Mac owner wants to mine Blocknet on an Apple Silicon machine: whether it works well, what an
M-series chip does, how many threads their memory size allows, and the exact macOS/Terminal
steps. Nearest owner: `/blog/how-to-mine-blocknet/` (all-OS newcomer guide, one Mac row in its
hardware table and one Mac bullet). This post adds the Mac-only procedure (tar.gz extraction in
Terminal, Gatekeeper, `caffeinate`), the M4 Max balanced vs maximum settings, a thread table by
Mac memory size derived from seine's sizing code, and why seine mines CPU-only on Apple Silicon.

## Keyword-map row (proposed)

| mine blocknet on mac | `/blog/mine-blocknet-on-mac/` | Set up and size Blocknet mining on an Apple Silicon Mac (macOS steps, M4 Max results, threads by memory, CPU-only default) | blocknet apple silicon, blocknet m4 max hashrate, mine blocknet macbook, seine macos, Argon2id on Mac, 在 Mac 上挖 Blocknet |

Boundary: the hardware post owns cross-platform comparisons and buying advice; this post owns
Mac depth. The general guide keeps its single Mac row and links here.

## Facts used from the fact sheet

- Argon2id, 2 GiB per hash; about 2 GB RAM per thread (§1, §2, §4).
- M4 Max 48 GB MacBook Pro: 30.94 H/s at 16 threads `auto`; balanced 29.26 H/s at 14 threads
  `pcore-only` (§5). The post presents 30.94 as the maximum-throughput setting and 14 threads as
  seine's default ceiling on that machine, per §6 ("don't present 30.9 as balanced or default").
- Comparison rows (Graviton4 21.50, Xeon best 13.10, EPYC Zen 4 35.7 / Zen 5) (§5).
- Archive names, `SHA256SUMS.txt`, default pool URL, 0.1 BNT minimum payout, update check every
  12 h, 5% memory reserve, threads park and release arenas under memory pressure, autotuning
  behavior, Faraday note (§0, §3, §4).
- CPU-only default; on the M4 Max CPU-only beat GPU and CPU+GPU modes because both compete for
  the same unified memory bandwidth (§4, Apple Metal bullet). The post doesn't name Metal or
  present it as a feature.

## Facts added (not in the fact sheet), with sources

Seine read at `origin/master` = d03a1b0 (2026-10-25 01:31 EDT).

- **Default affinity on macOS is `pcore-only`.** `seine@master:src/config.rs:123-126`, help text
  `:391`; guide `docs/guides/apple-silicon.md:7-8`.
- **Default thread ceiling on a Mac = performance cores + half the efficiency cores.**
  `macos_hybrid_pcore_parallelism_cap` at `seine@master:src/config.rs:2783-2790`, used by
  `cpu_parallelism_cap` (`:2792-2806`) and the autotune ceiling (`cpu_autotune_worker_ceiling`).
  Unit test `(12, 16) -> 14` (`:4382-4386`) matches the 12P+4E M4 Max, so 14 threads is seine's
  default ceiling there, the balanced profile in the guide.
- **Auto thread count = min(core ceiling, (available memory - 5% of total) / 2 GiB).**
  `auto_cpu_threads` / `auto_cpu_memory_bytes`, `seine@master:src/config.rs` (just after the
  parallelism cap; reserve default `:387`).
- **Derived thread table** (memory ceiling only, floor(RAM x 0.95 / 2), Mac RAM sizes are GiB):
  16 -> 7, 24 -> 11, 32 -> 15, 36 -> 17, 48 -> 22, 64 -> 30. Presented as "up to"; the core
  ceiling and currently free memory lower it.
- **M4 Max core layout 12P+4E and measurement date 2026-07-10.**
  `seine@master:docs/guides/apple-silicon.md:20`; `docs/PERFORMANCE.md:54-55`.
- **macOS archive contents:** `seine`, `SEINE-LICENSE.txt`, `README.md`, `SHA256SUMS.txt`,
  packed with `tar -C <stage> -czf ... .` (files at archive root, no folder), hence the
  `mkdir` + `tar -C ~/seine` steps. `seine@master:.github/workflows/release.yml:55-72`.
- **Signing / Gatekeeper:** "The macOS binary is ad-hoc signed. If Gatekeeper blocks the first
  launch, allow it in System Settings → Privacy & Security or run
  `xattr -d com.apple.quarantine ./seine`." `seine@master:docs/guides/apple-silicon.md:44-48`.
- **Metal not auto-enabled** (code comment: Argon2id on unified memory, running both degrades
  total throughput). `seine@master:src/config.rs:1457-1460`.
- **Unified memory wording:** Apple describes "a unified memory architecture that brings together
  high-bandwidth, low-latency memory into a single pool".
  https://www.apple.com/newsroom/2020/11/apple-unleashes-m1/ (checked 2026-10-25).
- **`caffeinate -i <utility>`:** "-i Create an assertion to prevent the system from idle
  sleeping"; with a utility, the assertion holds "as long as that process is running".
  https://ss64.com/mac/caffeinate.html (macOS man page mirror, checked 2026-10-25).

## Deliberately left out

- The ~3 GiB swap note on the 16-thread run (described instead as using more memory than the
  balanced default, suited to a Mac that only mines).
- Metal as a feature, other M-series chips (no measurements), Apple bandwidth figures (not
  needed), Ryzen 9950X3D desktop row.

## Checker note

`scripts/check-content.mjs` drops the first slug argument when `--hash` is absent
(`i !== hashIdx + 1` with `hashIdx = -1` excludes index 0), so `npm run check -- <slug> --strict`
checks every post. It still passed with zero warnings across all posts, including this one.
Translation structure (headings, code blocks, external links, block and FAQ counts, localized
links) was compared separately and matches.
