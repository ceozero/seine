#!/bin/bash
# perf stat comparison of seine (candidate, fixed kernel) and NTM (extra/) at one
# thread count. Aborts early if the host exposes no hardware counters.
# Usage (root, /opt/cohort): remote_perf_compare.sh <kernel> <threads> <seconds>
set -u
KERNEL=$1 T=$2 SECS=$3
R=/opt/cohort/results/perf-t$T
mkdir -p "$R"; chown -R bench:bench /opt/cohort
export DEBIAN_FRONTEND=noninteractive
apt-get install -y -qq "linux-tools-$(uname -r)" linux-tools-common > "$R/apt.log" 2>&1
if ! perf stat -e cycles,instructions true > "$R/probe.log" 2>&1 || grep -q 'not supported' "$R/probe.log"; then
  echo "NO-PMU" | tee "$R/summary.txt"; exit 0
fi
EV=cycles,instructions,cache-misses,LLC-load-misses,dTLB-load-misses
run() { # run <name> <cmd...>
  local name=$1; shift
  sync; echo 3 > /proc/sys/vm/drop_caches
  perf stat -a -x, -e "$EV" -o "$R/$name.perf" -- \
    unshare -n setpriv --reuid=bench --regid=bench --init-groups --reset-env -- env HOME=/home/bench "$@" \
    > "$R/$name.log" 2>&1
}
run seine bash -c "cd /opt/cohort/candidate && exec ./seine --bench --bench-kind backend --backend cpu --ui plain --data-dir /home/bench/perf-seine --threads $T --disable-cpu-autotune-threads --bench-cpu-kernel $KERNEL --bench-secs $SECS --bench-rounds 1 --bench-warmup-rounds 1 --bench-output $R/seine.json"
run ntm bash -c "cd /opt/cohort/extra && exec ./NTMminer-BNT --bench $((SECS * 2)) -t $T"
python3 - "$R" <<'PY' | tee "$R/summary.txt"
import json, re, sys, pathlib
r = pathlib.Path(sys.argv[1])
def counters(name):
    out = {}
    for line in (r / f'{name}.perf').read_text().splitlines():
        parts = line.split(',')
        if len(parts) > 3 and parts[0].replace('.', '').isdigit():
            out[parts[2]] = float(parts[0])
    return out
seine_hps = json.load(open(r / 'seine.json'))['avg_hps']
ntm_hps = float(re.findall(r'([0-9.]+) H/s（', (r / 'ntm.log').read_text())[-1])
for name, hps in (('seine', seine_hps), ('ntm', ntm_hps)):
    c = counters(name)
    print(name, 'hps', round(hps, 3), 'ipc', round(c.get('instructions', 0) / max(c.get('cycles', 1), 1), 3),
          {k: v for k, v in c.items()})
PY
