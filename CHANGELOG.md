# Changelog

Short release notes for miners deciding whether to upgrade. Lead with the biggest
user benefit, name the hardware for measured gains, and include required upgrade
steps. Keep test results and implementation details in the engineering docs.
Each `## vX.Y.Z` section becomes the corresponding GitHub release body.

## Unreleased

- **One miner fee everywhere:** a flat 2% dev fee on every pool and in solo mode replaces the previous 1% bntpool.com / 2.5% elsewhere rates. Upgrade to use the new rate.

- **More useful failure reports:** optional telemetry preserves specific memory and pool connection failure reasons, Windows code locations, and the last observed stage of interrupted runs.

**For self-hosted telemetry collectors:** update the collector before installing miners built from this version; see the [deployment guide](telemetry/deploy/PRODUCTION.md).

- **Clearer tuning startup:** CPU and NVIDIA messages explain when saved tuning is reused and why tuning runs again.

- **Peak hashrate by default:** CPU tuning targets the highest confirmed hashrate; choosing fewer workers at a lower rate is opt-in with `--cpu-profile efficiency`.
- **More accurate CPU kernel benchmarks:** hashing speed is measured separately from memory setup and cleanup. Regenerate saved CPU kernel benchmark baselines before comparing runs.

## v0.2.26

- **Help diagnose mining failures:** privacy-preserving warning and error summaries now identify affected hardware and code paths, including early failures and unclean restarts, while honoring your telemetry opt-out.
- **Help improve mining on your hardware:** fixes missing CPU and GPU performance reports during pool mining and includes memory and CPU settings so future optimizations can target comparable machines. Your telemetry opt-out preference is preserved.

**For self-hosted telemetry collectors:** update the collector before upgrading
miners to this release. The official collector is already updated. See the
[deployment guide](https://github.com/zpalmtree/seine/blob/v0.2.26/telemetry/deploy/PRODUCTION.md).

## v0.2.25

- **Faster startup and restarts on AMD EPYC 9355P.**
- **About 8% faster mining after a restart on AMD EPYC 9R14** with saved tuning settings.
- **Fewer lost shares when the pool is busy:** Seine retries temporary rejections automatically.
- **Fewer duplicate-share rejections** when returning from a dev-fee round.
- **Safer thread controls:** the dashboard checks available RAM before adding CPU threads and explains when an increase is blocked.
- AMD-only source builds now work without NVIDIA support.

## v0.2.24

- **About 33% higher CPU hashrate on Ryzen 9 9950X3D at 8 threads**, automatically.
- **Cleaner dashboard logs**, with less routine share and job-switch noise.
- **Clearer tuning updates** show which settings are faster.

## v0.2.23

- **Up to 57% higher CPU hashrate on AWS Graviton4**, 49% on Graviton3 and about 4% on Graviton2.
- **Up to 20% higher hashrate on AMD EPYC 9R45 after tuning**, and about 5% on Intel Xeon 8275CL.
- **CPU mining recovers automatically when RAM becomes available.** Seine also starts more reliably on Linux systems with tight thread limits.
- **Protected miner controls:** websites you visit can no longer change your mining settings through an unauthenticated local control API.
- **Update notices** tell you when a newer release is available. Use `--disable-update-check` to turn them off.

**For control API users:** send `Authorization: Bearer <token>` on requests other
than `/v1/health`. Read the token from `<data-dir>/control-api.cookie` after each
start, or set a fixed token with `--api-token`. Browser integrations also need
`--api-cors <origin>`. Plain CLI and dashboard mining need no changes.

## v0.2.22

- **About 30% higher CPU hashrate on AMD EPYC 9R45 at 24 threads** with huge pages. Seine selects the faster settings automatically.
- **More reliable automatic tuning**, including when you change which CPU cores Seine can use on Windows.
- **Ready-to-run Linux ARM64 downloads**, with no source build needed.

## v0.2.21

- **Start mining sooner.** CPU tuning now runs while you mine.
- **Keep mining as conditions change.** Seine adjusts CPU threads to available RAM and restores them when memory returns.
- **Automatic CPU speed tuning** finds faster settings for your hardware without manual configuration.
- **Steadier efficiency mode** keeps a lower thread count when it delivers close to peak hashrate.

## v0.2.20

- **More reliable CPU tuning** finds suitable thread counts and avoids getting stuck during startup.
- **Compare CPU mining options on your own hardware** with expanded benchmark controls.

**For benchmark users:** capture a new CPU baseline before comparing results
with this release. See the [benchmark guide](https://github.com/zpalmtree/seine/blob/v0.2.20/docs/benchmarks.md) for options.

## v0.2.19

- **Adjust CPU threads from the dashboard** with `+` and `-`, while keeping your session totals. Mining reconnects briefly; changes last for the current run and turn off automatic thread tuning.
- **Use Seine in smaller terminals** with a compact dashboard that keeps key controls and hashrate visible.
- **Read Windows startup errors** before the window closes when launching `seine.exe` by double-clicking.

## v0.2.18

- **Faster CPU mining on AMD Zen 3 and other AVX2 processors.**
- **Better use of CPU cores on Linux**, especially on large servers.
- **More RAM left for other apps:** automatic CPU sizing reserves 5% of system RAM. Use `--cpu-memory-reserve-percent 0` to remove the reserve.

## v0.2.17

- **More reliable pool statistics when the pool is busy**, especially for several rigs sharing one internet connection.
- **Less network traffic** from routine dashboard updates.

## v0.2.16

- **Mine with your Blocknet ID**, using `--address '@name'` or `--address '$name'` instead of a full wallet address. Keep the quotes in shell commands.
- **Use every NVIDIA GPU automatically.** AMD builds also use all supported GPUs when started with `--backend amd`.
- **Faster repeat starts on multi-GPU rigs:** each GPU's tuning settings are saved reliably.
- **See available GPUs through the control API** for easier dashboard and script setup.

**For multi-GPU scripts:** use `--nvidia-devices` or `--amd-devices` to select
specific GPUs. Match `--backend-*-per-instance` lists to the number of selected
GPUs. In control API `backend_specs`, set `device_index` to select one GPU;
omitting it now selects all detected GPUs.

## v0.2.15

- **Start NVIDIA mining on Windows without installing the CUDA toolkit.** Unzip and mine.
- **About half the first-start tuning time on RTX 5090**, with settings saved for later launches.
- **More CPU performance options on Linux and WSL** through huge-page support. See the [setup guide](https://github.com/zpalmtree/seine/blob/v0.2.15/README.md#wsl-linux-hugetlb-provisioning) before using `--cpu-page-mode large` or `large-1g`.
- **Clear warnings if a CPU or GPU stops mining**, so reduced performance is easier to spot.
- **More reliable solo block submission after a daemon restart.**
- Improved automatic CPU tuning on Apple Silicon and CPU core selection on Windows.

## v0.2.14

- **Keep the blocks your GPU finds.** Fixes a case where a block solution could be lost when found alongside a pool share.
- Pools can now identify your Seine version and mining hardware type to help with support and updates.

## v0.2.13

- **Catch invalid payout addresses before mining starts**, with a clear error instead of repeated pool connection failures.

## v0.2.12

- **More reliable pool statistics** when the pool limits requests.
- Improved CPU hashing performance on processors with AVX-512 support.

## v0.2.11

- **Keep NVIDIA GPUs mining when the pool adjusts share difficulty**, reducing interruptions and wasted work.

## v0.2.10

- **More reliable share handling** when pool difficulty changes or share confirmations arrive late.

## v0.2.9

- **Keep mining after finding a share.** Fixes CPU and GPU mining getting stuck after a submission.
- Clearer hardware names in mining logs.

## v0.2.8

- **More reliable NVIDIA pool mining** when new jobs arrive.
- Better recovery from pool connection problems and steadier dashboard hashrate readings.

## v0.2.7

- **Steadier NVIDIA hashrate readings** make the dashboard easier to follow.

## v0.2.6

- **Automatic AVX-512 support** lets compatible CPUs use the faster hashing option without a custom build.
- **More reliable pool statistics** through automatic pool API discovery.

## v0.2.5

- **Faster NVIDIA mining**, with improved automatic tuning for Blackwell GPUs.
- **See your pool and local wallet balances together** while pool mining.
- **Easier solo setup:** Seine finds wrapper-managed Blocknet daemons and waits for the wallet to become ready.

## v0.2.4

- **Keep pool mining moving after a share submission**, with more reliable continuation of the current job.
- See pool block notifications while mining.

## v0.2.3

- **Resume mining immediately after finding a share**, without repeating work already done.
- **Keep your own pool account details on screen** during dev-fee rounds.

## v0.2.2

- **Mine on more ARM devices**, including Raspberry Pi 4.
- **More reliable pool submissions and reconnects.**
- **A lower 1% dev fee on bntpool.com.**
- A better-fitting dashboard in narrow terminals.

Thanks to @donuts-are-good for the ARM compatibility fix.

## v0.2.0

- **Pool mining is here.** Connect to bntpool.com without running a local daemon.
- **Guided first-run setup** saves your pool and payout settings for next time.
- **Follow pool mining from the dashboard**, including network hashrate and accepted shares.
- Keep solo mining available when you want to use your own daemon.

## v0.1.12

- **More accurate hashrate readings** during startup and pauses while the daemon is unavailable.
- **Better automatic CPU thread sizing** when huge pages are reserved.
- Clearer handling of incorrect wallet passwords.

## v0.1.11

- **Network hashrate matches the explorer**, with clearer dashboard number formatting.

## v0.1.10

- **Choose your payout address** with `--address`, with validation before mining starts.
- **Spend less time on CPU tuning** at startup.
- **Clearer mining status**, including network hashrate, startup progress and version information.
- **Simpler source builds** with a Makefile that places the finished binary in the project root.

Thanks to @donuts-are-good for the build improvements.

## v0.1.9

- **Support for more older NVIDIA GPUs** through a more compatible startup path.
- A quieter dashboard shows dev-fee status without extra log messages.

## v0.1.8

- **Easier-to-read CPU memory setup warnings** in the dashboard.

## v0.1.7

- **Verify your full payout address at startup** in the logs.

## v0.1.6

- **See wallet balances and stale-share statistics** in the dashboard.
- **Read complete log messages** with wrapping instead of truncation.
- **Control Seine from other apps and scripts** through the new control API.
- Improved automatic CPU tuning on macOS.

## v0.1.5

- **Clearer huge-page setup guidance** helps you configure CPU mining memory.
- **Easier source builds** with stable Rust support.

## v0.1.4

- **Smoother CPU and NVIDIA mining** with reduced overhead.
- **More useful GPU hashrate readings** between batches of work.
- **Clearer daemon connection and sync status**, with a dashboard that fits your terminal width.

## v0.1.3

- **Automatic CPU tuning stays closer to peak hashrate.**
- **Clearer stale-block reporting** when the chain advances before submission.

## v0.1.2

- **Faster CPU mining on Apple Silicon and x86-64**, with improved automatic hardware selection.
- **Start CPU mining while NVIDIA GPUs initialize**, and reuse saved GPU setup on later launches.
- **Easier daemon connection setup** through automatic discovery and clearer guidance.
- **Stop startup or tuning with one Ctrl+C.**
- **More accurate average hashrate and stale-block reporting.**

**For existing configurations:** use `--daemon-dir` for the daemon's cookie
location. `--data-dir` now stores Seine's own settings.

## v0.1.1

- **Stop automatic tuning cleanly with Ctrl+C.**
- **Read long log messages more easily** in the terminal.
