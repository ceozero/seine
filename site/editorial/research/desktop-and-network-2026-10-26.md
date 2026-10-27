# Desktop use and network quality — October 26, 2026

## Scope and intent

Approved pair: `mine-while-using-pc` on Seine and `internet-speed-mining` on bntpool, English plus 19 translations. One translation subagent handles eight locales; the parent handles English and eleven translations. No external translation APIs. Separate linguistic review remains optional and translations remain marked draft. Existing list layout is retained with original language-neutral SVG graphics.

Desktop job: compare an ordinary foreground task with/without mining, choose the backend and CPU count, budget memory, save and verify a repeatable daily launch. CPU usage owns percentages, RAM owns sizing, tuning owns selection mechanics, NVIDIA owns installation. New procedure combines those controls around foreground responsiveness without claiming measured performance.

Network job: distinguish local computation, message delivery and pool estimates; compare Wi-Fi/Ethernet or competing transfers while holding the mining setup constant. Tracking owns lookup/endpoint setup, Stratum owns message formats, shares owns rejection categories. This guide owns the controlled network-path comparison and evidence record. No assumed monthly traffic allowance or recommended internet tier.

## Sources

Public miner release checked with `gh release view`: v0.2.37, published October 26, 2026 at 6:40:12 PM EDT; source f703b37ad93b87bbdbbb2d91eb23d0e76a26fabe. Starting site revision 767680736e3a59db9be80d56ddcdceba9f43a6e2; pool 9a41fa260fdd63687b3f24c0a39b49ada4191d8c. `src/config.rs`, `src/pool.rs` and `docs/guides/configuration.md` have no changes from that release in the selected worktree.

- Seine `src/config.rs:380-401`: explicit NVIDIA selection; CPU threads per backend; 2 GiB arena; automatic memory reserve and explicit-thread override. `:482-494` documents automatic tuning/minimum/maximum and `:960-980` validates bounds. `:2853-2880` applies the memory budget. No claim of a hard CPU percentage or electrical power target.
- Seine `docs/guides/configuration.md:34-67`: backend selection, explicit count, dashboard minus/plus, restart/reconnect semantics, session-only thread changes, q/Ctrl+C quit. Existing saved connection values and launch arguments remain separate; configuration guide owns persistence.
- Seine `src/miner/mod.rs:1520` selects profile hashrate targets; `src/miner/adaptive_cpu.rs` implements productive tuning. Efficiency is a hashrate/count policy, not a measured-watt policy. No unsupported game-detection, automatic foreground pause or guaranteed frame-rate claim.
- Seine `src/pool.rs:395-460` handles connect/login/reconnect and submission state; `PoolSubmit` carries a job ID, nonce and claimed hash, not each attempted hash or memory arena. Remaining connection loop handles jobs, replies and keepalives. `src/pool/submit_retry.rs` owns retryable outcome handling; article makes no universal resend promise.
- Pool `crates/pool-runtime/src/stratum.rs:847-875` has connection/login/idle handling; `:1122-1215` routes job-linked submissions; `:1703-1835` parses bounded lines and writes responses. Tests distinguish stale and duplicate share reasons near `:2203`. The article does not equate all rejection reasons with network latency.
- Existing `what-is-hashrate`, `track-your-miner-on-bntpool`, `accepted-rejected-stale-shares` and `stratum-mining-protocol` own rate windows, account lookup, rejection interpretation and message flow. Links point to those owners.
- Microsoft, https://support.microsoft.com/en-us/windows/experience/performance-optimization/tips-to-improve-pc-performance-in-windows (read October 26, 2026): Task Manager resource inspection. No copied tuning checklist or recommendation to disable protection.
- Cloudflare, https://www.cloudflare.com/learning/performance/glossary/what-is-latency/ (read October 26, 2026): bandwidth and delay terminology. Applying those definitions to the pool message flow is source-code-based reasoning. No Cloudflare website delivery recommendation is presented as a Stratum fix.

## Verification boundaries

No mining, GPU workload, hardware rental, router change, background transfer pause, packet capture or speed test was run. This is source review and rendered-page verification. Numeric two-thread example is illustrative: two 2 GiB arenas = 4 GiB, before overhead. No hashrate gain, desktop responsiveness gain, data volume or rejection improvement is claimed as measured. Pool deployment is API-only; service PIDs/timestamps must be compared before/after.

English strict checks passed. Wording overlap: desktop maximum 0.3% (3 eight-word phrases); network 0%. Intent boundaries above are the substantive check.

Concurrent release recheck: v0.2.38 published October 26, 2026 at 8:07:22 PM EDT, source e4f05927df3f2537679c2db17695eefb44e8ece6. Configuration, pool transport, tuning-profile hashrate targets, NVIDIA guide, fee policy and release workflow sources are unchanged from v0.2.37. Five platform archive names remain unchanged. Both release manifests and the new desktop guide now reference v0.2.38. The release changes the CPU streaming implementation, not the controls documented here.
