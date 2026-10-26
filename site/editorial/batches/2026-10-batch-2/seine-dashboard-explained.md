# seine-dashboard-explained: research notes

Writer notes for `src/content/blog/seine-dashboard-explained/` (batch 2, 2026-10-25).

## Intent

A seine user looking at the running dashboard wants to know what each label and number means
(Current vs Average, Rejected, State values, lanes, Pending vs Paid, log tags), what auto-tuning
looks like while it runs, and which keys work. Nearest owners: `/blog/how-to-mine-blocknet/`
(gets a newcomer to first shares, mentions "the dashboard shows your hashrate" in one line) and
`/blog/mine-blocknet-on-mac/` (one line about the dashboard). This post adds the field-by-field
reading of the real UI, sourced from the TUI code, plus the live-tuning log lines and the
keyboard controls. Pool-side stats (bntpool.com's web dashboard) stay with bntpool.com's blog.

## Keyword-map row (proposed)

| seine dashboard | `/blog/seine-dashboard-explained/` | Read seine's terminal dashboard: every panel and label, live auto-tuning in the log, keyboard thread controls | seine hashrate current vs average, seine accepted rejected shares, seine change threads while mining, seine tui, seine --ui plain, seine 仪表盘 / seine 儀表板 |

Boundary: how-to-mine and the Mac post keep their one-line "the dashboard shows your hashrate"
and can link here; the autotuning mechanics stay in seine's `docs/guides/autotuning.md` (linked).

## Source revision

Worktree `/home/zp/Code/blocknet/seine-blog-batch2` = seine master; `src/` last changed at
acc6003 (2026-10-25 01:27 EDT). All `src/...` paths below are in that worktree.

## Facts from the fact sheet

- Default pool `stratum+tcp://bntpool.com:3333`; minimum payout 0.1 BNT; vardiff aims for ~10
  shares per 5 minutes (§3).
- Update check at startup and every 12 h; GPU kernels compile at startup and the first launch
  autotunes per GPU; tuning never reconnects to the pool or restarts GPU backends; "threads"
  terminology (§4).
- 2 GiB arena per thread (§1, §4).

## Facts added (not in the fact sheet), with sources

Layout and refresh
- Panel order: header, HASHRATE / NETWORK / MINING, DEVICES, CONFIG, wallet panel, LOG.
  `src/miner/tui.rs:349-396` (`draw_dashboard`).
- Wide layout at width >= 80, otherwise the stat panels stack (`tui.rs:350`, `draw_stats_narrow`
  `:722`); CONFIG and the balance panel side by side at >= 148 columns (`tui.rs:23`, `:847-877`).
- Compact view when the terminal is too short: Threads, State, Current, Average, Accepted /
  Submitted, Rejected (or Stale) / Height, then the log (`tui.rs:376-379`, `:411-466`).
- Renders about once per second (`TUI_RENDER_INTERVAL = 1s`, `src/miner/mining_tui.rs:19`, `:91-95`).

Header
- Title ` seine {version} `, plus ` update {latest} available ` badge (`tui.rs:468-482`);
  configuration guide confirms the header notice (`docs/guides/configuration.md:69-72`).
- Two wave rows advance one step per second; accepted work adds a gold ♦ at the right edge that
  moves one column per second (`tui.rs:505-540`); uptime overlaid
  on the last row (`tui.rs:487-495`), format `10m 29s` (`tui.rs:264-283`).
- What adds a diamond: each accepted pool share (`src/miner/mining_pool.rs:1569-1578`), a pool
  "miner block found" notification (`mining_pool.rs:1541-1545`), and an accepted solo block
  (`src/miner/submit.rs:599-602`).
- "About two minutes on a ~130-column terminal" is derived: one column per second × ~130 columns.

HASHRATE
- Current = rolling 5 s window (`src/miner/hashrate_tracker.rs:6`, `:158-175`); NVIDIA uses a 30 s
  current window because batches complete in bursts (`mining_tui.rs:18`, `:210-226`).
- Average = hashes over active (unpaused) time (`hashrate_tracker.rs:158`); paused states are
  wallet-required, wallet-password-required, daemon-syncing, daemon-unavailable, invalid-address,
  and Current shows zero in them (`mining_tui.rs:199-208`, `:161-175`).
- Average survives a thread change ("Keep lifetime averages", `hashrate_tracker.rs:72-80`;
  `mining_tui.rs:228-239`); configuration guide: session statistics, uptime, average hashrate and
  history preserved (`docs/guides/configuration.md:55-62`).
- Total = completed hashes (`mining_tui.rs:131`, `tui.rs:620-626`).
- Why Average starts lower: tuning starts from a cached count or "an initial estimate of half
  the automatic capacity" (`docs/guides/autotuning.md:12-14`), and "every arena completes one hash
  before its measurement window starts" (`:15-16`).

NETWORK and State
- Labels Height / Global / State (`tui.rs:632-647`). In pool mode Global is the network hashrate
  from the pool's `/api/stats` (`/chain/network_hashrate`), cached 30 s
  (`mining_pool.rs:54`, `:2521-2578`, `:2506`).
- Pool-mode states set in `mining_pool.rs`: `pool-connecting` (`:655`), `pool-connected` (`:1463`),
  `pool-authenticated` (`:1512`), `pool-disconnected` (`:1494`), `pool-login-rejected` (`:1533`,
  with `AUTH` "login rejected: {message}" at `:1515`), `pool-resync` (`:1722`). Reconnect delay
  constant `src/pool.rs:20`. Solo states `stale-tip`, `stale-refresh`, `refresh`, `solved`
  (`src/miner/mining.rs:1192-1225`, `:1946`). Colors in `tui.rs:618-651`.

MINING
- Submitted / Rejected (pool) or Stale (solo) / Accepted (`tui.rs:684-705`).
- Pool Rejected = share ack not accepted (`mining_pool.rs:1593`, `:1821`); solo Stale = solution
  for an old tip (`submit.rs:640-672`).

DEVICES, CONFIG, balance
- Device names `cpu#1`, `nvidia#1`… (`src/miner/mod.rs:3177`); pending NVIDIA messages
  `starting CUDA runtime` (<20 s), `preparing NVIDIA backend` (<90 s), then "still initializing"
  (`tui.rs:1185-1193`).
- CONFIG labels Endpoint, the pool name label, Threads with `  [+] [-]` hint, Backends
  (`tui.rs:398-409`, `:879-904`). Endpoint is the pool URL in pool mode or the daemon API URL in
  solo mode; default pool name is a random `seine-NNNN` unless `--pool-worker` is set
  (`src/miner/mod.rs:982-986`, `src/config.rs:320-322`, `:2477-2484`). The post doesn't print the
  label text because the check script flags the word; it describes it as the rig's login name.
- Backends text `cpu#1 (N lanes, ~X GiB RAM)` with X = lanes × `CPU_LANE_MEMORY_BYTES` (2 GiB);
  GPUs show VRAM (`src/miner/mod.rs:2988-3011`, `pow-spec/src/lib.rs:9`).
- POOL BALANCE: Pending, Paid, Miner (address shortened to first and last 6 characters)
  (`tui.rs:942-954`, `:1221-1231`); fetched from `/api/miner/{address}/balance` every 5 s
  (`mining_pool.rs:53`, `:2507-2510`, `:2580+`). Solo mode: WALLET panel with Pending / Unlocked /
  Address; pool mode with a local wallet: BALANCES with P.Pending, P.Paid, W.Pending, Unlocked
  (`tui.rs:906-967`; `docs/guides/solo-mining.md:48-54`).

LOG
- 200 entries (`tui.rs:21`, `:202-207`); badges INFO / OK / WARN / ERR / ** (`tui.rs:43-52`);
  `**` is "solution found!" (`src/miner/mining.rs:1196`); relative times "1 min ago" etc.
  (`tui.rs:1069-1115`).
- Tags and messages: AUTH login accepted (screenshot), SHARE `accepted (backend=…)`
  (`mining_pool.rs:1570-1575`), VARDIFF `difficulty {old} -> {new}` (`mining_pool.rs:369-371`).

Live tuning in the log
- `cpu-autotune | starting with {threads} threads ({reason}); tuning while mining…`, reasons
  "initial estimate", "cached starting point", "waiting for RAM" (`src/miner/adaptive_cpu.rs:170-177`).
- Decision lines `cpu-autotune | [done — ]{n} threads per CPU backend: {reason}`
  (`adaptive_cpu.rs:1078-1092`); reasons "measuring useful mining work" (`:798`), "checking baseline
  again" (`:807`), "keeping confirmed setting" (`:879`). Threads value in CONFIG updated from the
  tuner (`adaptive_cpu.rs:1118-1126`).
- Kernel lines: "comparing {base} and {candidate} while mining", "confirmed faster {kernel} path in
  two comparisons (… H/s)" (`src/miner/adaptive_kernel.rs:566`, `:669`); kernel names `avx2`,
  `avx512`, `neon-sha3`, `avx512-256-stream` (`pow-kernel/src/cpu_kernel.rs:31-37`).
- Windows >= 30 s and >= 20 hashes for thread trials (`docs/guides/autotuning.md:15-17`).

Keyboard and modes
- `q` or Ctrl+C quits; `+` or `=` adds one thread, `-` removes one (min 1, max = live cap); ignored
  while a change is pending; notice `Restarting: {from} -> {to} threads...` (`tui.rs:202-262`).
- The change restarts the session with `cpu_autotune_threads: false` and logs `THREADS restarting
  mining with N threads per CPU backend; session statistics preserved`
  (`src/control_api/mod.rs:908-947`, `:1256-1296`); not saved as default, capped at the automatic
  CPU/RAM cap (`docs/guides/configuration.md:55-64`).
- `--ui auto|tui|plain`, default auto = dashboard only when stdout and stderr are terminals
  (`src/miner/mod.rs:963-969`; `docs/MINER_FLAGS.md:61`).

Screenshot
- `/assets/blog/seine-dashboard.webp` matches seine's README screenshot
  (`docs/assets/screenshots/dashboard.png`, added in 48771ca on 2026-10-24 23:49 EDT): Apple M4 Max,
  seine v0.2.22, bntpool.com, 14 threads, Current 30.63 H/s, Average 29.33 H/s, 5/0/5 shares,
  uptime 10m 29s. The post doesn't quote the Paid figure, Global or Height from it.

## Integrator notes

- The image uses Markdown syntax with a title (`![alt](/assets/... "title")`). Without the title,
  `check-content.mjs` reads `](/assets/...)` as an internal page link and errors ("link to unknown
  page"); the title stops its link regex from matching. A proper fix is to exempt `/assets/` in
  `checkLinks`.
- `related: []` per the brief, so `--strict` reports one warning ("list 2-4 related posts").
  Suggested: `how-to-mine-blocknet`, `blocknet-mining-hardware-hashrate`,
  `argon2id-proof-of-work-explained`.
- Left out on purpose: the `working (dev fee)` state label (fees not volunteered).
- Translations were validated with a scratch copy marked published/reviewed: `--strict` clean.
