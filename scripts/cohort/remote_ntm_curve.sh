#!/bin/bash
# Reference curve for the NTM CPU miner (extra/NTMminer-BNT) at given thread counts.
# Usage (root, /opt/cohort): remote_ntm_curve.sh <threads...>. Offline bench, no network.
set -u
R=/opt/cohort/results/ntm-curve
mkdir -p "$R"; chown -R bench:bench /opt/cohort
for t in "$@"; do
  sync; echo 3 > /proc/sys/vm/drop_caches
  unshare -n setpriv --reuid=bench --regid=bench --init-groups --reset-env -- env HOME=/home/bench \
    bash -c 'cd /opt/cohort/extra && exec ./NTMminer-BNT --bench 90 -t "$0"' "$t" > "$R/t$t.log" 2>&1
  echo "t$t $(grep -oE '[0-9.]+ H/s（' "$R/t$t.log" | tail -1 | cut -d' ' -f1)"
done | tee "$R/summary.txt"
