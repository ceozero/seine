# huge-pages-blocknet-mining: research notes

Writer notes for `src/content/blog/huge-pages-blocknet-mining/` (batch 2, 2026-10-25).
seine read from this worktree (seine master, HEAD d3d5690).

## Intent

A miner who already runs seine wants the last few percent of CPU hashrate from huge pages: why
they help Argon2id, how many to reserve for their thread count, and the exact commands on Linux,
WSL2 and Windows. Nearest owners: `/blog/argon2id-proof-of-work-explained/` (one paragraph on
why huge pages help) and `/blog/how-to-mine-blocknet/` and `/blog/blocknet-mining-hardware-hashrate/`
(one bullet each linking seine's guide). This post adds the TLB explanation, the per-thread sizing
table, every setup command (2 MiB, 1 GiB, WSL2, Windows large pages), page modes and the Zen 5
reservation evidence. NUMA placement stays with `mine-blocknet-on-servers`.

## Keyword-map row (proposed)

| huge pages blocknet mining | `/blog/huge-pages-blocknet-mining/` | Reserve huge pages (Linux/WSL 2 MiB and 1 GiB) or Windows large pages for seine: why they help Argon2id, pages per thread, exact commands, page modes | blocknet hugepages, seine hugepages, vm.nr_hugepages mining, 1GB huge pages argon2id, windows large pages mining, lock pages in memory seine, Blocknet 大页内存 / 大分頁 |

Boundaries: the Argon2id explainer keeps its one-paragraph "why" and links here; the hardware and
how-to posts keep their one bullet and link here; the servers post owns NUMA-local placement and
links here for page setup.

## Facts used from the fact sheet

- 2 GiB Argon2id arena per thread, 1 KiB blocks, data-dependent second half, ~2 GiB read per hash
  (§1, §9 Argon2id background).
- +4–6% with 2 MiB pages and a further +2% with 1 GiB pages on the validation host; 1,024 2 MiB
  pages per thread (§4 Huge pages). Quoted as the guide's split, per §6 contradictions.
- Cloud server rows measured with explicit 2 MiB huge pages (§5); Zen 5 49.4 H/s at 32 threads
  (§5 update, §9).

## Facts added, with sources

- **Sizing formula** `ceil(threads × 1024 × 1.05)`; nine threads = 9,677 pages (~18.9 GiB).
  `docs/guides/linux-hugepages.md:15-19`, `:52-55`. Derived table: 4→4,301 (8.4 GiB),
  8→8,602 (16.8), 16→17,204 (33.6), 24→25,805 (50.4), 32→34,407 (67.2); 1 GiB = 2 × threads.
- **Zen 5 49.39 H/s run reserved 34,407 2 MiB pages** (equals the derived 32-thread figure).
  `seine:origin/codex/zen5-turin-result:experiments/readme-hardware-20261025/summary.json:297`
  (EPYC 9R45), `:353` (`hugetlb_2mib_pages_reserved: 34407`), `:587` (mean 49.393). PR #59;
  switch to master once it merges.
- **Commands** (sysctl, meminfo grep, drop_caches/compact_memory, sysctl.d persist, sysfs 1 GiB
  pool, `free_hugepages`, `hugepagesz=1G hugepages=18`, `.wslconfig` with `memory=48GB`,
  `processors=32`, `swap=8GB`, `kernelCommandLine`): `docs/guides/linux-hugepages.md:21-47`,
  `:76-95`, `:97-106`. Persist-and-reboot advice: `:49-55`. `/proc/meminfo` covers only 2 MiB:
  `:89-90` (line 90).
- **"Single biggest tuning knob for CPU mining on Linux"; coverage beats ISA tuning with many
  lanes:** `linux-hugepages.md:3-6`, `:72-73`.
- **`auto` order HugeTLB → THP (MADV_HUGEPAGE + MADV_COLLAPSE) → regular; `large` fails closed;
  `large-1g` uses `MAP_HUGETLB|MAP_HUGE_1GB`, x86_64 Linux only, never falls back; `regular`
  sets MADV_NOHUGEPAGE.** `src/backend/cpu/kernel.rs:1752-1823`, `:1863-1910`; enum
  `src/config.rs:58-69`; flag `src/config.rs:395-398`; `docs/MINER_FLAGS.md:36`.
- **Startup `hugepages |` warning prints needed pages, the sysctl command (+5% headroom) and
  persist/compact commands; skipped in `regular` mode.** `src/miner/mod.rs:1978-2054`; 1 GiB
  variant incl. WSL hint `:2056-2107`.
- **Auto thread sizing adds unreserved HugeTLB (and 1 GiB pool in large-1g) to available
  memory.** `src/config.rs:2985-3010` (`detect_memory_budget_bytes`).
- **Dashboard label "Threads:".** `src/miner/tui.rs:405`.
- **Windows:** tries `VirtualAlloc(MEM_RESERVE|MEM_COMMIT|MEM_LARGE_PAGES)` after
  `GetLargePageMinimum`, enables `SeLockMemoryPrivilege` in its own token via
  `AdjustTokenPrivileges`, falls back to regular pages and logs the Win32 error plus the fix;
  `large-1g` rejected on Windows. `src/backend/cpu/kernel.rs:1456-1495`, `:1512-1570`,
  `:1675-1720`. secpol steps, Home editions/`ntrights`, never grants the right or signs out,
  native Windows usually faster than WSL: `docs/guides/windows-large-pages.md:9-21`,
  `linux-hugepages.md:106-107`.
- **TLB quotes:** "A TLB is a cache of virtual-to-physical translations"; "Typically this is a
  very scarce resource on processor"; boot-time allocation "is the most reliable method ... as
  memory has not yet become fragmented." https://docs.kernel.org/admin-guide/mm/hugetlbpage.html
  (checked 2026-10-25).
- **Windows large-page API** (SeLockMemoryPrivilege, GetLargePageMinimum, MEM_LARGE_PAGES):
  https://learn.microsoft.com/en-us/windows/win32/memory/large-page-support (checked 2026-10-25).
- **`.wslconfig` `[wsl2]` section holds `memory` and `kernelCommandLine`; `wsl --shutdown`
  applies changes.** https://learn.microsoft.com/en-us/windows/wsl/wsl-config (checked
  2026-10-25).
- **Arithmetic:** 2 GiB / 4 KiB = 524,288; / 2 MiB = 1,024; / 1 GiB = 2; 2 MiB / 4 KiB = 512;
  1 GiB / 4 KiB = 262,144.

## Deliberately left out

- CHANGELOG's older "roughly 6% and 8%" wording (`CHANGELOG.md:183-186`); the guide's split is used.
- No Windows large-page gain (none documented). No macOS (explicit modes are rejected there).
- NUMA-local reservation detail (one sentence linking `large-servers.md`), left to the servers post.
- Specific TLB entry counts per CPU (unsourced).

## Checker note

`npm run check -- --strict huge-pages-blocknet-mining` reports one warning, "list 2-4 related
posts", because the brief requires `related: []` for the integrator. Suggested related:
`argon2id-proof-of-work-explained`, `blocknet-mining-hardware-hashrate`, `mine-blocknet-on-servers`.
Overlap: 0% shared 8-word phrases with every post.
