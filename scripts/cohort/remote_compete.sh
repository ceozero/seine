#!/bin/bash
# Same-host default-vs-default comparison: Seine (candidate, cold autotune),
# NTM (extra/NTMminer-BNT, default threads) and Longhorn (extra/longhorn-*, own tune).
# Usage (root, /opt/cohort): remote_compete.sh [seconds]
set -u
SECS=${1:-30}
R=/opt/cohort/results/compete
mkdir -p "$R"; chown -R bench:bench /opt/cohort
run() { local name=$1 dir=$2; shift 2
  sync; echo 3 > /proc/sys/vm/drop_caches
  unshare -n setpriv --reuid=bench --regid=bench --init-groups --reset-env -- env HOME=/home/bench \
    bash -c 'cd "$0" && exec "$@"' "$dir" "$@" > "$R/$name.log" 2>&1; }
run seine /opt/cohort/candidate ./seine --bench --bench-kind backend --backend cpu --ui plain \
  --data-dir /home/bench/compete-seine --bench-secs "$SECS" --bench-rounds 2 --bench-warmup-rounds 1 --bench-output "$R/seine.json"
[ -x /opt/cohort/extra/NTMminer-BNT ] && run ntm /opt/cohort/extra ./NTMminer-BNT --bench $((SECS * 3))
LH=$(ls -d /opt/cohort/extra/longhorn-* 2>/dev/null | head -1)
[ -n "$LH" ] && run longhorn-tune "$LH" ./longhorn --tune && run longhorn "$LH" ./longhorn bench --seconds "$SECS"
{
  python3 -c "import json; d=json.load(open('$R/seine.json')); print('seine lanes', d.get('total_lanes'), 'hps', round(d['avg_hps'], 3), 'late%', round(d.get('late_hash_pct') or 0, 1))"
  grep -hoE '测速结果: [0-9.]+ H/s（[0-9]+ 线程' "$R/ntm.log" 2>/dev/null | sed 's/^/ntm /'
  grep -hE 'TUNE selected|BENCH round=[12]' "$R/longhorn-tune.log" "$R/longhorn.log" 2>/dev/null | sed 's/^/longhorn /'
} | tee "$R/summary.txt"
