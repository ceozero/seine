#!/bin/bash
# Live pool smoke test of the candidate build: mine for a fixed time, then count
# accepted/rejected shares and record the CPU kernel lines. Needs network access.
# Usage (root, /opt/cohort): remote_pool_smoke.sh <name> <seconds> <address> [seine args...]
set -u
NAME=$1 SECS=$2 ADDRESS=$3; shift 3
R=/opt/cohort/results/pool-$NAME
mkdir -p "$R"; chown -R bench:bench /opt/cohort
sync; echo 3 > /proc/sys/vm/drop_caches
setpriv --reuid=bench --regid=bench --init-groups --reset-env -- env HOME=/home/bench \
  timeout -s INT -k 30 "$SECS" bash -c 'cd /opt/cohort/candidate && exec ./seine --mode pool --ui plain \
  --data-dir /home/bench/seine-pool --telemetry off --address "$0" --pool-worker "cohort-smoke-$1" "${@:2}"' \
  "$ADDRESS" "$NAME" "$@" > "$R/mining.log" 2>&1
{
  echo "accepted $(grep -cE 'SHARE +accepted' "$R/mining.log")"
  echo "submitted $(grep -cE 'SHARE +submitted' "$R/mining.log")"
  echo "other-share-events $(grep -E 'SHARE' "$R/mining.log" | grep -cvE 'SHARE +(submitted|accepted)')"
  grep -m3 -iE 'kernel|fixed workers' "$R/mining.log" | cut -c1-160
} | tee "$R/summary.txt"
