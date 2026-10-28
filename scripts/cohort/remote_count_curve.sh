#!/bin/bash
# Worker-count curve for one build and kernel: each count runs once ascending and
# once descending, so linear drift cancels in the per-count mean.
# Usage (root, /opt/cohort): [BUILD=candidate] remote_count_curve.sh <name> <kernel> <threads...>
set -u
W=/opt/cohort
R=$W/results/curve-$1
KERNEL=$2; shift 2
BUILD=${BUILD:-candidate}
SECS=${SECS:-20}
mkdir -p "$R"; chown -R bench:bench "$W"
isolated() {
  local dir=$1; shift
  unshare -n setpriv --reuid=bench --regid=bench --init-groups --reset-env -- \
    env HOME=/home/bench PATH=/usr/bin:/bin bash -c 'cd "$0" && exec "$@"' "$dir" "$@"
}
one() { # one <threads> <tag>
  sync; echo 3 > /proc/sys/vm/drop_caches
  isolated "$W/$BUILD" ./seine --bench --bench-kind backend --backend cpu --ui plain \
    --data-dir /home/bench/seine-curve --threads "$1" --disable-cpu-autotune-threads --bench-cpu-kernel "$KERNEL" \
    --bench-secs "$SECS" --bench-rounds 1 --bench-warmup-rounds 1 --bench-output "$R/$2.json" > "$R/$2.log" 2>&1
  python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(sys.argv[2], round(d['avg_hps'], 3))" "$R/$2.json" "$2" 2>/dev/null \
    || echo "$2 FAILED"
}
{
  for t in "$@"; do one "$t" "t$t-up"; done
  for t in $(printf '%s\n' "$@" | sort -rn); do one "$t" "t$t-down"; done
} | tee "$R/summary.txt"
touch "$R/COMPLETE"
