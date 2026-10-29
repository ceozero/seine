# Linux and WSL HugePages

Each CPU worker hashes inside a 2 GiB Argon2id arena. Backing those arenas with
explicit huge pages cuts TLB misses and is the single biggest tuning knob for CPU
mining on Linux: about **+4–6%** with 2 MiB pages and a further **+2%** with 1 GiB
pages on the validation host. Seine works without them; this guide is for squeezing
out the last few percent.

Seine maps each worker's arena with `MAP_HUGETLB` when a reserved pool is
available and falls back to transparent huge pages (THP) otherwise, which is often
slower and less consistent under memory fragmentation.

## Quick setup (2 MiB pages)

Each worker needs 1024 two-MiB pages. Reserve a little headroom:

```text
vm.nr_hugepages = ceil(cpu_threads * 1024 * 1.05)
```

Example for 4 workers:

```bash
# 4 workers * 1024 pages/worker = 4096 hugepages (~8 GiB)
sudo sysctl -w vm.nr_hugepages=4096
```

If the kernel cannot allocate enough pages (fragmented memory), compact and retry:

```bash
echo 3 | sudo tee /proc/sys/vm/drop_caches
echo 1 | sudo tee /proc/sys/vm/compact_memory
sudo sysctl -w vm.nr_hugepages=4096
```

Verify the reservation:

```bash
grep -E 'HugePages_Total|HugePages_Free|Hugepagesize' /proc/meminfo
```

Persist across reboots:

```bash
echo 'vm.nr_hugepages=4096' | sudo tee /etc/sysctl.d/99-seine-hugepages.conf
sudo sysctl --system
```

If a runtime `sysctl -w vm.nr_hugepages=...` request only allocates a fraction of
the target, keep the value persisted and reboot. Early-boot reservation is much
more reliable than carving out tens of GiB of huge pages after the machine is
already fragmented. For nine workers, for example, reserve `9677` pages (about
18.9 GiB) in `/etc/sysctl.d/99-seine-hugepages.conf`.

## Page modes

| Mode | Behaviour |
|---|---|
| `--cpu-page-mode auto` (default) | Try `MAP_HUGETLB`, then THP, then regular pages. |
| `--cpu-page-mode large` | Require `MAP_HUGETLB` for every worker; CPU backend startup fails instead of mixing page classes or silently falling back. |
| `--cpu-page-mode large-1g` | Same, with explicit 1 GiB pages (`MAP_HUGETLB\|MAP_HUGE_1GB`, x86_64 Linux/WSL only). |
| `--cpu-page-mode regular` | Disable THP for a controlled base-page benchmark. |

Runtime checks:

- Startup warns with exact sizing and commands when HugeTLB is under-provisioned
  (`hugepages | CPU lanes=... need ...`).
- Per-backend fallback warnings appear if a worker falls back from `MAP_HUGETLB`
  (`MAP_HUGETLB unavailable; hugepage coverage...`).
- Benchmark reports record measured HugeTLB, THP, regular-page, and heap bytes per
  CPU backend, so page-backed runs can be verified rather than inferred.
- Once many CPU lanes are active, hugepage coverage usually matters more than
  ISA-level tuning.

## 1 GiB pages

`--cpu-page-mode large-1g` maps every worker arena from the explicit 1 GiB pool and
fails closed on any shortfall. Each 2 GiB arena needs exactly two 1 GiB pages, so no
fractional headroom is required:

```bash
# 9 workers * 2 pages/worker = 18 x 1 GiB pages
echo 18 | sudo tee /sys/kernel/mm/hugepages/hugepages-1048576kB/nr_hugepages
```

1 GiB pages usually cannot be assembled after boot on a fragmented host; prefer
reserving them at boot with the `hugepagesz=1G hugepages=18` kernel parameters.
Verify the pool with
`cat /sys/kernel/mm/hugepages/hugepages-1048576kB/free_hugepages` (the
`HugePages_*` lines in `/proc/meminfo` cover only the default 2 MiB size).
Benchmark telemetry reports 1 GiB backing separately (`large1g=`/`large1g_bytes=`).

## WSL2

On WSL2, set boot-time kernel parameters in `%UserProfile%\.wslconfig`, for example
`kernelCommandLine = hugepagesz=1G hugepages=18`, then restart WSL.

The VM also needs ordinary headroom for Windows and WSL services. The validated
64 GiB host used `memory=48GB`, `processors=32`, and `swap=8GB` in `.wslconfig`.
Restart WSL only when convenient, then confirm `HugePages_Free` covers every
requested arena before mining. A reservation is unavailable to ordinary
applications until reduced, so size it for the profile you actually run.

Native Windows mining is usually faster than WSL for the same hardware; see
[Windows large pages](windows-large-pages.md).

## Large servers

HugeTLB pools need enough pages on the NUMA nodes that host the workers; a
sufficient global count alone does not guarantee local placement. See
[Large servers](large-servers.md).
