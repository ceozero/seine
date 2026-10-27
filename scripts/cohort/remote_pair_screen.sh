#!/bin/bash
# Paired-arena screen with extra/pair/streaming_pair_experiment (research build):
# shipping single-hash streaming kernel vs two interleaved hashes per thread.
# Usage (root, /opt/cohort): remote_pair_screen.sh <seconds>
set -u
SECS=${1:-30}
R=/opt/cohort/results/pair-screen
B=/opt/cohort/extra/pair/streaming_pair_experiment
mkdir -p "$R"; chown -R bench:bench /opt/cohort
iso() { unshare -n setpriv --reuid=bench --regid=bench --init-groups --reset-env -- env HOME=/home/bench "$@"; }
iso "$B" verify > "$R/parity.log" 2>&1 && grep -q '"passed":true' "$R/parity.log" && ! grep -q '"passed":false' "$R/parity.log" \
  || { echo PARITY-FAILED | tee "$R/summary.txt"; exit 1; }
LOGICAL=$(nproc)
PHYS_LIST=$(lscpu -p=CPU,CORE | grep -v '^#' | sort -t, -k2,2n -u | cut -d, -f1 | paste -sd,)
PHYS=$(echo "$PHYS_LIST" | tr ',' '\n' | wc -l)
one() { # one <tag> <cpus> <mode> <workers>
  sync; echo 3 > /proc/sys/vm/drop_caches
  iso taskset -c "$2" "$B" bench "$3" "$4" "$SECS" 5 2 3 > "$R/$1.json" 2> "$R/$1.err"
  python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(sys.argv[2], round(d['hps_unverified'], 3))" "$R/$1.json" "$1"
}
ALL=0-$((LOGICAL - 1))
for rep in 1 2; do
  one "r$rep-single-$LOGICAL" "$ALL" single "$LOGICAL"
  one "r$rep-paired-$PHYS-phys" "$PHYS_LIST" paired "$PHYS"
  one "r$rep-paired-$LOGICAL" "$ALL" paired "$LOGICAL"
  one "r$rep-single-$PHYS-phys" "$PHYS_LIST" single "$PHYS"
done | tee "$R/summary.txt"
