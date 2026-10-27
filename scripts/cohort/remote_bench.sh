#!/bin/bash
# Cohort benchmark, run as root on a fresh disposable Linux host from /opt/cohort.
# Expects: seine/seine, and optionally longhorn/ (extracted package),
# ntm/NTMminer-BNT, pair/streaming_pair_experiment.
# Every miner runs as an unprivileged user in a network-less namespace.
# Output: /opt/cohort/results (host facts, logs, timings.tsv, JSON reports).
set -u
W=/opt/cohort
R=$W/results
SECS=${SECS:-60}
mkdir -p "$R"
id bench >/dev/null 2>&1 || useradd -m bench
chown -R bench:bench "$W"

lscpu -J > "$R/lscpu.json"
cat /proc/meminfo > "$R/meminfo.txt"
dmidecode -t memory > "$R/dmidecode-memory.txt" 2>&1 || true
{ uname -a; cat /etc/os-release
  for f in enabled defrag; do echo "thp_$f: $(cat /sys/kernel/mm/transparent_hugepage/$f)"; done
  echo "governor: $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null)"
  echo "nr_hugepages: $(cat /proc/sys/vm/nr_hugepages)"
} > "$R/host.txt"
PHYS=$(lscpu -p=CORE,SOCKET | grep -v '^#' | sort -u | wc -l)
LOGICAL=$(nproc)
MEM_GIB=$(awk '/MemTotal/ {print int($2/1048576)}' /proc/meminfo)
echo -e "physical\t$PHYS\nlogical\t$LOGICAL\nmem_gib\t$MEM_GIB" > "$R/topology.tsv"

isolated() { # isolated <cwd> <cmd...>: no network, uid bench, clean env
  local dir=$1; shift
  unshare -n setpriv --reuid=bench --regid=bench --init-groups --reset-env -- \
    env HOME=/home/bench PATH=/usr/bin:/bin bash -c 'cd "$0" && exec "$@"' "$dir" "$@"
}

run() { # run <name> <cwd> <cmd...>
  local name=$1; shift
  echo "== $name $(date -u +%T)"
  sync; echo 3 > /proc/sys/vm/drop_caches; echo 1 > /proc/sys/vm/compact_memory
  local start=$SECONDS
  isolated "$@" > "$R/$name.log" 2>&1
  printf '%s\t%s\t%s\n' "$name" "$?" "$((SECONDS - start))" >> "$R/timings.tsv"
}

SEINE_DATA=/home/bench/seine-data
seine_bench() { # seine_bench <name> [extra args]
  local name=$1; shift
  run "$name" "$W/seine" ./seine --bench --bench-kind backend --backend cpu --ui plain \
    --data-dir "$SEINE_DATA" --bench-secs "$SECS" --bench-rounds 2 --bench-warmup-rounds 1 \
    --bench-output "$R/$name.json" "$@"
}

LH=$(ls -d "$W"/longhorn/longhorn-* 2>/dev/null | head -1)
NTM=$W/ntm

# Correctness first.
[ -x "$NTM/NTMminer-BNT" ] && run ntm-selftest "$NTM" ./NTMminer-BNT --selftest
[ -x "$W/pair/streaming_pair_experiment" ] && run pair-verify "$W/pair" ./streaming_pair_experiment verify

# Round 1: cold defaults (includes each miner's first-start tuning).
seine_bench seine-cold
[ -n "$LH" ] && run longhorn-tune "$LH" ./longhorn --tune
[ -n "$LH" ] && run longhorn-bench1 "$LH" ./longhorn bench --seconds "$SECS"
[ -x "$NTM/NTMminer-BNT" ] && run ntm-bench1 "$NTM" ./NTMminer-BNT --bench $((SECS * 2))

# Round 2: reversed order, warm caches.
[ -x "$NTM/NTMminer-BNT" ] && run ntm-bench2 "$NTM" ./NTMminer-BNT --bench $((SECS * 2))
[ -n "$LH" ] && run longhorn-bench2 "$LH" ./longhorn bench --seconds "$SECS"
seine_bench seine-warm

# Seine kernel sweep at the tuned thread count: does the default leave a kernel win unclaimed?
THREADS=$(python3 - "$R/seine-cold.json" <<'PY'
import json, sys
def find(o):
    if isinstance(o, dict):
        if isinstance(o.get('cpu_threads'), int) and o['cpu_threads'] > 0:
            return o['cpu_threads']
        o = list(o.values())
    if isinstance(o, list):
        for v in o:
            r = find(v)
            if r:
                return r
report = json.load(open(sys.argv[1]))
print(report.get('total_lanes') or find(report) or '')  # CPU-only: lanes == workers
PY
)
if [ -n "$THREADS" ]; then
  if grep -q avx512f /proc/cpuinfo; then
    KERNELS="avx2 avx512 avx512-256 avx512-256-stream avx512-256-stream-r8d2 avx512-256-stream-r64d3"
  else
    KERNELS="avx2"
  fi
  for k in $KERNELS; do
    seine_bench "seine-kernel-$k" --threads "$THREADS" --disable-cpu-autotune-threads --bench-cpu-kernel "$k"
  done
fi

# Paired arenas (Longhorn --depth 2 analogue) vs SMT at equal arena counts.
if [ -x "$W/pair/streaming_pair_experiment" ]; then
  PHYS_LIST=$(lscpu -p=CPU,CORE | grep -v '^#' | sort -t, -k2,2n -u | cut -d, -f1 | paste -sd,)
  ARENAS=$(( (MEM_GIB - 6) / 2 ))
  P=$W/pair
  run pair-single-logical "$P" taskset -c 0-$((LOGICAL - 1)) ./streaming_pair_experiment bench single "$LOGICAL" 30 5
  run pair-paired-phys "$P" taskset -c "$PHYS_LIST" ./streaming_pair_experiment bench paired "$PHYS" 30 5
  run pair-single-phys "$P" taskset -c "$PHYS_LIST" ./streaming_pair_experiment bench single "$PHYS" 30 5
  if [ $((LOGICAL * 2)) -le "$ARENAS" ]; then
    run pair-paired-logical "$P" taskset -c 0-$((LOGICAL - 1)) ./streaming_pair_experiment bench paired "$LOGICAL" 30 5
  fi
fi
echo "== done $(date -u +%T)"
touch "$R/COMPLETE"
