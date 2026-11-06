# HiveOS

Seine runs on HiveOS as a custom miner. Add it to a flight sheet with one
installation URL. Your rigs then show seine's hashrate per GPU, accepted and
rejected shares, and GPU temperatures and fans on the HiveOS dashboard.

Each release has a HiveOS package named `seine-hiveos-<version>.tar.gz`. It
holds a seine build that runs on HiveOS's older system libraries, plus the CUDA
NVRTC library seine needs to compile its NVIDIA kernels. You don't need to
install anything else on the rig.

## Set up a flight sheet

1. **Add a wallet.** In HiveOS, open **Wallets** and add your Blocknet payout
   address. If BNT isn't in the coin list, type `BNT` as the coin name. Seine
   also accepts a Blocknet ID shortname such as `@name`. Use the `@` form,
   because HiveOS treats `$` specially.
2. **Create a flight sheet.** Choose your BNT coin and wallet. Set
   **Pool** to *Configure in miner* and **Miner** to *Custom*.
3. **Click Setup Miner Config** and fill in:

   | Field | Value |
   |---|---|
   | Miner name | `seine-hiveos` (HiveOS fills this in from the URL) |
   | Installation URL | `https://github.com/zpalmtree/seine/releases/download/vX.Y.Z/seine-hiveos-X.Y.Z.tar.gz` |
   | Hash algorithm | leave empty |
   | Wallet and worker template | `%WAL%.%WORKER_NAME%` |
   | Pool URL | `stratum+tcp://bntpool.com:3333` |
   | Pass | leave empty (Blocknet pools don't use passwords) |
   | Extra config arguments | optional, see below |

   Replace `X.Y.Z` with the newest version on the
   [releases page](https://github.com/zpalmtree/seine/releases/latest). You can
   also copy the link to the `seine-hiveos-…tar.gz` file there.
4. **Apply the flight sheet** to your rigs.

Backup pools go on separate lines in **Pool URL**. Seine tries them in order and
switches back to the first one when it recovers. Pools that offer TLS take
`stratum+ssl://host:port`. If you leave **Pool URL** empty, seine mines on
`stratum+tcp://bntpool.com:3333`.

On the first start, seine tunes itself to each GPU for a few minutes before
hashrate appears. It saves the result, so later starts begin hashing within
seconds. If you use HiveOS's watchdog with a low-hashrate restart, give it more
than 10 minutes so it doesn't interrupt the first tuning run.

## What it mines on

- **GPU rigs mine on the GPUs only.** Every hash takes 2 GiB of memory: VRAM on a
  GPU, system RAM on the CPU. Many GPU rigs have 4–8 GB of RAM, so CPU mining on
  top of the GPUs could run the rig out of memory. That's why the package leaves
  the CPU off.
- **Rigs without a GPU mine on the CPU.** Seine sizes the thread count to the free
  RAM and keeps some RAM back for the system.
- **NVIDIA** needs a driver with CUDA 12 support. RTX 50 series cards need driver
  570 or newer.
- **AMD Radeon RX 6000, 7000 and 9000** cards (RDNA) need the ROCm HIP runtime
  (`libamdhip64`). If the rig doesn't have it, seine says so at startup and
  leaves those cards idle. Older AMD cards (RX 400/500, Vega) are not supported.

### Add CPU mining to a GPU rig

Put the backends you want in **Extra config arguments**. Plan on one thread per
2 GiB of RAM you can spare. Leave at least 2 GB for HiveOS.

```text
--backend nvidia,cpu --threads 2
```

Use `amd,cpu` on AMD rigs, or `nvidia,amd,cpu` on mixed rigs. If you leave out
`--threads`, seine sizes and tunes the CPU threads itself to the free RAM.

## Extra config arguments

Anything you put in **Extra config arguments** goes to seine as is. Your value
wins over the package defaults. Some examples:

| Extra config arguments | Effect |
|---|---|
| `--backend nvidia --nvidia-devices 0,1,3` | Mine on some NVIDIA GPUs only |
| `--nvidia-max-lanes 4` | Use less VRAM on each NVIDIA GPU |
| `--cpu-page-mode regular` | CPU mining without huge pages |
| `--telemetry off` | Don't send hardware reports |

See the [flag reference](../MINER_FLAGS.md) for every option. Quote values that
contain spaces.

The package always adds these flags, unless you set them yourself:

| Flag | Why |
|---|---|
| `--backend nvidia` / `amd` / `cpu` | Picked from the GPUs HiveOS detects (see above) |
| `--ui plain` | Plain log lines for the HiveOS miner log |
| `--no-auto-update` | HiveOS installs new versions through the package |
| `--data-dir /var/lib/seine` | Tuning results survive package upgrades |
| `--api-server --api-bind 127.0.0.1:9977` | Local stats for the HiveOS dashboard |

Don't change `--api-bind`, `--api-cookie` or `--api-token`. The dashboard stats
read seine's local control API at that address.

## Huge pages

GPU mining doesn't use huge pages. For CPU mining on Linux, huge pages are worth a
few percent (see [Linux huge pages](linux-hugepages.md)). The package doesn't
change system settings, so reserve the pages yourself if you want them. Reserved
huge pages are unavailable to the rest of the system, so only reserve what the
CPU threads use.

## Upgrading

Seine doesn't update itself on HiveOS. When a newer release is out, seine logs a
notice. To upgrade, change the version in the **Installation URL** to the new
release and apply the flight sheet. HiveOS downloads the new package. Your
tuning results and settings stay in `/var/lib/seine`.

## Logs and troubleshooting

- `miner log` (or the miner log on the dashboard) shows seine's output. The full
  log is in `/var/log/miner/custom/seine-hiveos.log`.
- **"Custom miner name should be seine-hiveos"**: set **Miner name** to exactly
  `seine-hiveos`.
- **"set Wallet and worker template"**: the flight sheet has no wallet. Fill in
  **Wallet and worker template**.
- **Hashrate shows 0 right after starting**: seine is tuning the GPUs on the first
  start. Wait a few minutes.
- **NVIDIA GPUs aren't mining**: check the log for CUDA or driver errors. Seine
  keeps mining on the other GPUs and logs a `running degraded` warning.
- Shares and payouts for bntpool.com are on the pool's dashboard. Search for your
  address there.
