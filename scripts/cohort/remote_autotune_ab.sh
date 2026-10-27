#!/bin/bash
# Cold-autotune comparison: each build sizes its own workers (the count users get).
# Usage (root, /opt/cohort): remote_autotune_ab.sh <name> [extra seine args...]
# Runs baseline then candidate with fresh data dirs; reports chosen lanes and H/s.
set -u
NAME=$1; shift
R=/opt/cohort/results/autotune-$NAME
SECS=${SECS:-60}
mkdir -p "$R"; chown -R bench:bench /opt/cohort
for build in baseline candidate; do
  sync; echo 3 > /proc/sys/vm/drop_caches
  unshare -n setpriv --reuid=bench --regid=bench --init-groups --reset-env -- env HOME=/home/bench \
    bash -c 'cd /opt/cohort/$0 && exec ./seine --bench --bench-kind backend --backend cpu --ui plain \
      --data-dir /home/bench/autotune-$0 --bench-secs "$1" --bench-rounds 2 --bench-warmup-rounds 1 \
      --bench-output "$2" "${@:3}"' "$build" "$SECS" "$R/$build.json" "$@" > "$R/$build.log" 2>&1
  python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(sys.argv[2], 'lanes', d.get('total_lanes'), 'hps', round(d['avg_hps'], 3))" "$R/$build.json" "$build"
done | tee "$R/summary.txt"
