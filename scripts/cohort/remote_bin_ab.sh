#!/bin/bash
# Binary A/B on a cohort host: same kernel, baseline/ vs candidate/ builds.
# Usage (root, /opt/cohort): remote_bin_ab.sh <name> <kernel> <threads...>
# Expects baseline/seine, candidate/seine and candidate/verify_cpu_kernels.
# Screen defaults (~45 s per run, ~3 min per count): SECS=20, ROUNDS=1. Run-to-run
# noise at fixed counts is ~0.3%; raise ROUNDS only to confirm an unclear result.
set -u
W=/opt/cohort
R=$W/results/bin-ab-$1
KERNEL=$2; shift 2
SECS=${SECS:-20}
mkdir -p "$R"; chown -R bench:bench "$W"
isolated() {
  local dir=$1; shift
  unshare -n setpriv --reuid=bench --regid=bench --init-groups --reset-env -- \
    env HOME=/home/bench PATH=/usr/bin:/bin bash -c 'cd "$0" && exec "$@"' "$dir" "$@"
}
isolated "$W/candidate" ./verify_cpu_kernels > "$R/parity.log" 2>&1 && grep -q "^$KERNEL: PASS" "$R/parity.log" \
  || { echo "PARITY-FAILED $KERNEL"; touch "$R/COMPLETE"; exit 1; }
one() { # one <dir> <threads> <tag>
  sync; echo 3 > /proc/sys/vm/drop_caches
  isolated "$W/$1" ./seine --bench --bench-kind backend --backend cpu --ui plain \
    --data-dir /home/bench/seine-ab --threads "$2" --disable-cpu-autotune-threads --bench-cpu-kernel "$KERNEL" \
    --bench-secs "$SECS" --bench-rounds "${ROUNDS:-1}" --bench-warmup-rounds 1 --bench-output "$R/$3.json" > "$R/$3.log" 2>&1
  python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(sys.argv[2], round(d['avg_hps'], 3))" "$R/$3.json" "$3"
}
for t in "$@"; do
  one baseline "$t" "t$t-1-base"; one candidate "$t" "t$t-2-cand"
  one candidate "$t" "t$t-3-cand"; one baseline "$t" "t$t-4-base"
done | tee "$R/summary.txt"
touch "$R/COMPLETE"
