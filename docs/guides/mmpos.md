# mmpOS

Seine runs on mmpOS as a custom miner. Add it to a miner profile with one
download URL. Your rigs then show seine's hashrate per GPU and its accepted and
rejected shares on the mmpOS dashboard.

Each release has an mmpOS package named `seine-mmpos-<version>.tar.gz`. It holds
a seine build that runs on older system libraries, the CUDA NVRTC library seine
needs to compile its NVIDIA kernels, and `jq` for the stats script. You don't
need to install anything else on the rig.

## Set up a miner profile

mmpOS's coin lists don't include BNT yet, so you can't pick it in the wallet,
pool or profile forms. Import the profile below instead: it brings in the BNT
wallet, the bntpool.com pool and the seine miner profile in one step.

1. **Edit the profile below** before you import it:
   - Replace `YOUR_BLOCKNET_ADDRESS` with your Blocknet payout address. Seine
     also accepts a Blocknet ID shortname such as `@name`. Use the `@` form,
     because mmpOS runs the command line through a shell, which treats `$`
     specially.
   - Replace both `X.Y.Z` in `custom_url` with the newest version on the
     [releases page](https://github.com/zpalmtree/seine/releases/latest). You
     can also copy the link to the `seine-mmpos-…tar.gz` file there.

   ```json
   {
     "miner_profile": {
       "name": "seine BNT",
       "coin": "BNT",
       "os": "linux",
       "miner": "custom",
       "miner_version": "latest",
       "custom_url": "https://github.com/zpalmtree/seine/releases/download/vX.Y.Z/seine-mmpos-X.Y.Z.tar.gz",
       "commandline": "./mmp-launch.sh --coin %coin% --pool %pool_server%:%pool_port% --user %user% --password %password% --api-port %api_port%",
       "api_port": 4444,
       "platforms": ["nvidia", "amd_sysfs", "amd_adl", "cpu_intel", "cpu_amd"]
     },
     "pools": [
       {
         "name": "bntpool",
         "coin": "BNT",
         "url": "bntpool.com",
         "port": "3333",
         "ssl": false,
         "username": "%wallet_address%.%rig_name%%miner_id%",
         "password": "x"
       }
     ],
     "wallets": [
       {"name": "BNT wallet", "coin": "BNT", "address": "YOUR_BLOCKNET_ADDRESS"}
     ]
   }
   ```

2. **Import it.** Open **Miner profiles**, click **Import from JSON**, paste the
   edited profile and click **Import**.
3. **Add each part** from the import result, in this order. The coin, platform
   and miner fields in these forms look empty because BNT isn't in mmpOS's
   lists; the imported values are still saved.
   - **Add wallet**: check the address and save.
   - **Add pool**: the BNT wallet fills in by itself. Save.
   - **Add miner profile**: select the `bntpool` pool, then create the profile.
4. **Assign the profile** to your rigs: on each rig, set **Active miner profile**
   to `seine BNT`.

Seine flags go at the end of the profile's arguments (see below). Leave the
mmpOS placeholders in place: mmpOS fills in your wallet, the rig name and the
pool when it starts the miner. If the profile has no pool, seine mines on
`stratum+tcp://bntpool.com:3333`.

On the first start, seine tunes itself to each GPU for a few minutes before
hashrate appears. It saves the result, so later starts begin hashing within
seconds.

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
- Seine needs an mmpOS image built on Ubuntu 20.04 or newer (glibc 2.31). On an
  older image it logs `seine needs 2.31 or newer` and doesn't start.

### Add CPU mining to a GPU rig

Add the backends you want to the end of the arguments. Plan on one thread per
2 GiB of RAM you can spare, and leave at least 2 GB for mmpOS.

```text
--backend nvidia,cpu --threads 2
```

Use `amd,cpu` on AMD rigs, or `nvidia,amd,cpu` on mixed rigs. If you leave out
`--threads`, seine sizes and tunes the CPU threads itself to the free RAM.

## More seine flags

Anything after the mmpOS placeholders goes to seine as is, and your value wins
over the package defaults. Some examples:

| Add to the arguments | Effect |
|---|---|
| `--pool-url stratum+tcp://bntpool.com:3333,stratum+tcp://backup.example.com:3333` | Backup pools: seine tries them in order and returns to the first when it recovers |
| `--pool-url stratum+ssl://pool.example.com:3443` | Connect to a pool's TLS port |
| `--backend nvidia --nvidia-devices 0,1,3` | Mine on some NVIDIA GPUs only |
| `--nvidia-max-lanes 4` | Use less VRAM on each NVIDIA GPU |
| `--cpu-page-mode regular` | CPU mining without huge pages |
| `--telemetry off` | Don't send hardware reports |

See the [flag reference](../MINER_FLAGS.md) for every option. Quote values that
contain spaces.

The package always adds these flags, unless you set them yourself:

| Flag | Why |
|---|---|
| `--backend nvidia` / `amd` / `cpu` | Picked from the GPUs mmpOS detects (see above) |
| `--ui plain` | Plain log lines for the mmpOS miner log |
| `--no-auto-update` | mmpOS installs new versions through the package |
| `--data-dir <miners folder>/seine-data` | Tuning results survive package upgrades |
| `--api-server --api-bind 127.0.0.1:<Api port>` | Local stats for the mmpOS dashboard |

The control API listens on the profile's **Api port** (4444 unless you change it),
or on 9977 if the port is empty or 0. Don't change `--api-bind`, `--api-cookie` or `--api-token` by hand:
the dashboard stats read seine's local control API at that address.

## Huge pages

GPU mining doesn't use huge pages. For CPU mining on Linux, huge pages are worth a
few percent (see [Linux huge pages](linux-hugepages.md)). The package doesn't
change system settings, so reserve the pages yourself if you want them. Reserved
huge pages are unavailable to the rest of the system, so only reserve what the
CPU threads use.

## Upgrading

Seine doesn't update itself on mmpOS. When a newer release is out, seine logs a
notice. To upgrade, change the version in the profile's download URL to the new
release. mmpOS downloads each URL once, so the new URL fetches the new package.
Your tuning results and settings stay in `seine-data` beside the miner folders
(`/opt/mmp/miners/seine-data`, or `/miners/seine-data` with mmpOS's Docker agent).

## Troubleshooting

- The miner log shows the arguments mmpOS started the miner with
  (`Starting with: ./mmp-launch.sh …`), then the full seine command line and
  seine's output.
- **"no wallet"**: the profile's pool has no wallet. Edit the `bntpool` pool and
  select your BNT wallet.
- **Hashrate shows 0 right after starting**: seine is tuning the GPUs on the first
  start. Wait a few minutes.
- **NVIDIA GPUs aren't mining**: check the log for CUDA or driver errors. Seine
  keeps mining on the other GPUs and logs a `running degraded` warning.
- Shares and payouts for bntpool.com are on the pool's dashboard. Search for your
  address there.
