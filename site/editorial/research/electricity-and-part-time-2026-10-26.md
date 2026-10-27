# Electricity and part-time mining — October 26, 2026

Approved scope: two new guides in English and 19 translations, original graphics and existing list layouts; publish both sites, pool API-only. One translation subagent handles 12 locales and the parent handles English plus seven. No separate linguistic review; translations remain `translation: draft`.

## Distinct reader jobs

`mining-electricity-use` owns measurement scope, energy arithmetic, total versus incremental PC consumption and tariff-interval budgeting. The older-PC guide has brief cost arithmetic but owns suitability; desktop use owns foreground responsiveness; benchmarks own performance-test procedure. The worked energy record and baseline comparison provide the new job.

`mine-blocknet-part-time` owns a concrete session/pause/return timeline and verification procedure. PPLNS retains allocation mechanics, payout thresholds and eligibility; confirmations owns maturation; tracking owns account navigation. The article links to those owners rather than duplicating their full explanations. A brief existing FAQ about stopping remains; this guide expands it into a daily operating procedure.

Both English drafts passed strict editorial checks. Wording overlap reports show 0.0% shared eight-word phrases; intent boundaries above are the substantive duplication check.

## Energy sources and arithmetic

- Virginia Cooperative Extension, “Estimating Appliance and Home Electronic Energy Use”, https://ext.vt.edu/content/pubs_ext_vt_edu/en/2901/2901-9014/2901-9014.html (read October 26, 2026): watts × hours ÷ 1,000 = kWh, then kWh × tariff. Only the general unit calculation is used; its historical appliance wattages and tariffs are not reproduced.
- Linux kernel documentation, https://cdn.kernel.org/doc/html/latest/power/powercap/powercap.html (read October 26, 2026): energy counters belong to named zones and subzones; package and component domains are distinct and can overlap. No counter probe or setting change was performed.
- Seine `docs/CPU_ENERGY.md:11–30`: package energy includes other applications on the package and does not establish wall-plug consumption or separately unmeasured DRAM. The experimental harness's whole-invocation metric is not a steady-state measurement. The public article does not prescribe running this development harness or claim its results.
- Published release checked: v0.2.38, commit e4f05927df3f2537679c2db17695eefb44e8ece6, October 26 at 8:07:22 PM EDT. `src/config.rs` defines the CPU profile; `src/miner/mod.rs` applies its hashrate target. `--cpu-profile efficiency` is a tuning policy, not a whole-PC watt cap. Selected source files are compared to this tag before publishing.
- Invented round-number examples are explicitly labeled, not hardware results or current tariff quotes: 150 W × 8 h ÷ 1,000 = 1.2 kWh; × 0.20 currency units/kWh = 0.24. Thirty sessions = 36 kWh and 7.20. Baseline 60 W versus mining 150 W yields 90 W incremental, 0.72 kWh and 0.144 for eight hours. Full consumption remains 1.2 kWh. No currency conversion, investment advice or promised return.
- Matching foreground work, screen state, peripherals and duration is necessary for an incremental comparison. A PSU capacity label and a momentary sensor are not a measured whole-session energy budget. Plug-in measurements must respect the meter's documented ratings and instructions; no wiring work is instructed.

## Pool accounting sources

Public `https://bntpool.com/api/info` checked October 26, 2026: `pplns_window_duration=6h`, `blocks_before_payout=60`, `min_payout_amount=0.1`. These are dated operational settings, not universal protocol constants. API response retained with showcase verification.

- `crates/pool-runtime/src/payout.rs:735–789`: reward allocation looks up shares between the reward window end minus configured duration and its end, then applies payout-eligible difficulty weights. No six-hour connection-age gate.
- `crates/pool-runtime/src/payout.rs:2544–2550`: window end uses the later of recorded block timestamp and latest linked share timestamp. The example says “reward window ending at” rather than claiming every wall-clock block observation supplies the exact endpoint.
- `crates/pool-runtime/src/pgdb.rs:1418–1428`: range query uses stored creation timestamps and inclusive endpoints. Illustrative times avoid exact boundary ambiguity.
- `crates/pool-runtime/src/payout.rs:1090–1195`: payout scans account balances, checks pending payments, network address and configured minimum. A currently connected worker is not a payout requirement. Disconnect does not request immediate payment. Other processing conditions still apply.
- Existing PPLNS/confirmation guides supply the distinction between estimated block rewards, confirmed unpaid balances and sent payments. No automatic movement of balance between wallet addresses.
- Example in a single unspecified local timezone: session 18:00–20:00; one eligible share at 19:00. Window ending22:00 starts16:00 and includes it. Window ending02:00 next day starts20:00 and excludes it. Return08:00 does not change old timestamps. No real block timing or reward measurement claimed.
- `docs/guides/configuration.md` documents q/Ctrl+C normal exit. No new miner scheduling feature is claimed.

## Verification scope

Source review, deterministic arithmetic, content/structure/protected-token checks, builds, existing tests, shared Windows browser desktop/mobile/RTL checks and live public-page verification. No hardware rental, mining, GPU load, electricity measurement, network test or change to a user's power settings. Deploy only pool API/UI; compare service PIDs/start times to verify Stratum, monitor and recovery remain unchanged.
