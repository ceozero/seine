# mine-blocknet-on-servers: research notes

Writer notes for `/blog/mine-blocknet-on-servers/` (batch 2, 2026-10-25). Sources were read from
this worktree (`seine-blog-batch2`, HEAD d3d5690, which is seine master). Its `docs/` and
`CHANGELOG.md` match `seine@origin/master` (4cdf83b, 2026-10-25), and the only `src/` difference
is `src/miner/mining_pool.rs`, which this post doesn't use.

## Intent

Someone running Blocknet mining on a many-core server or on several rigs wants seine to use the
whole machine (NUMA nodes, L3 groups) and to run it unattended and monitored (headless startup,
systemd, `--service`, control API, live events, Prometheus). Nearest owners:
`/blog/blocknet-mining-hardware-hashrate/` (which machine to buy; mentions placement in one bullet)
and `/blog/how-to-mine-blocknet/` (desktop first run; one bullet on servers). This post adds the
measured placement gains with method, the headless procedure and the control API workflow, none
of which exist on the site.

## Keyword-map row (proposed)

| mine blocknet on servers | `/blog/mine-blocknet-on-servers/` | Run seine on many-core servers and mining rigs: NUMA/L3 placement and its measured gains, headless runs, `--service`, the control API, live events and Prometheus | blocknet mining server, blocknet NUMA, EPYC blocknet mining, seine headless, seine control API, seine Prometheus metrics, 在服务器上挖 Blocknet |

Boundaries: huge pages commands and gains belong to `/blog/huge-pages-blocknet-mining/` (this post
links there and only notes that placement and huge pages stack); buying advice and per-chip H/s
belong to `/blog/blocknet-mining-hardware-hashrate/`.

## Facts used (not already in the fact sheet, or more detail than it gives)

- Placement detail: OS-order 8 threads on the two-node EPYC 7R13 put all workers on node 0 with
  nearly all 16 GiB of arenas there; `auto` put four per node and about 8 GiB on each.
  `CPU_OPTIMIZATION_LOG.md:781-818` ("2026-10-24 two-node EPYC placement").
- Measurement method and date: identical binary, `--cpu-affinity os` vs `auto`, alternating pairs,
  2026-10-24; all three 8-thread pairs favor `auto` in each page mode; host AWS c6a.8xlarge.
  `CPU_OPTIMIZATION_LOG.md:781-808`, table at `:800-804`.
- EPYC 8434P: 48 cores / 96 threads, one NUMA node, eight L3 groups; at 24 threads `os` packs
  six per group in four groups, `auto` uses three per group in all eight; +16.72% with gains in
  all three pairs. `CPU_OPTIMIZATION_LOG.md:866-915`.
- Gains: +73% / +108% / +16.7% from `docs/guides/large-servers.md:7-12` (also fact sheet §4).
  The post shows percentages only, no absolute H/s from these runs.
- Placement respects process CPU and memory masks; threads pin before allocating their arena;
  opt-outs `--cpu-affinity os` and `off`; compare `auto` vs `os` at the same thread count;
  HugeTLB pages must be on the nodes hosting threads. `docs/guides/large-servers.md:14-34`.
- Native Windows `auto` uses physical cores before SMT. `docs/MINER_FLAGS.md:35`.
- Memory reserve 5%, `--cpu-memory-reserve-percent`, threads release and return arenas;
  autotune cache invalidated when allowed CPU set or NUMA/L3 layout changes.
  `docs/guides/large-servers.md:36-62`.
- Headless: on a first run without a terminal (stdin and stderr not TTYs), pool mode requires
  `--address` and `--pool-url` or it stops with "Provide --address and --pool-url";
  a missing pool name is generated as `seine-NNNN`. `src/config.rs:2318-2374`, `:2477-2484`.
- First run with flags writes `seine.config.json` under `--data-dir` (default `./seine-data`) and
  later runs reuse it. `src/config.rs:844-871`, `:2292-2306`, `:2418-2439`;
  `docs/guides/configuration.md:27-28`; `docs/MINER_FLAGS.md:25`.
- `--ui auto` shows the dashboard only when stdout and stderr are terminals.
  `src/miner/mod.rs:963-969`; `docs/MINER_FLAGS.md:61`.
- `--service` skips the first-run prompts. `src/config.rs:854-858`.
- Control API modes, bind default `127.0.0.1:9977`, `--api-allow-unsafe-bind`, endpoints, SSE
  event types, resync with `/v1/runtime/state`, metric names, curl flows.
  `docs/API.md:14-210`; metric names confirmed in `src/control_api/mod.rs` (`render` near
  `:1792-1805`).
- Shortnames accepted in the control API's `mining_address`. `docs/guides/configuration.md:80-82`.
- **Token (new since the fact sheet):** seine **v0.2.23** (released 2026-10-25 01:18 EDT,
  `gh release list -R zpalmtree/seine`; `Cargo.toml:3` version 0.2.23) requires
  `Authorization: Bearer <token>` on every endpoint except `/v1/health`; token written to
  `<data-dir>/control-api.cookie` each start (owner-only on Unix, deleted on shutdown),
  `--api-token`, `--api-cookie`; CORS off by default (`--api-cors`); loopback binds reject
  non-loopback `Host`. `CHANGELOG.md:9-19`; `docs/API.md:40-46`; `docs/MINER_FLAGS.md:127-133`;
  enforcement `src/control_api/mod.rs:1388-1447`, cookie removal `:1364`.
- systemd unit and Prometheus scrape config are standard usage examples of the flags above
  (`DynamicUser`, `StateDirectory`, `authorization.credentials_file`), not seine claims.

## Left out on purpose

- The 16-thread all-core control (+0.30%) and the 32/48-thread 8434P rows (inconclusive): the
  post says the gain appears when threads are fewer than cores instead.
- "Multi-socket NUMA servers have not been benchmarked yet" (`docs/PERFORMANCE.md:145`): the post
  calls the 7R13 a two-node machine and makes no multi-socket claim.
- Absolute H/s from placement runs (weak next to the headline table).
- The fact sheet's §4 "Control API" bullet predates v0.2.23 and doesn't mention the token; the
  integrator may want to add it there.
