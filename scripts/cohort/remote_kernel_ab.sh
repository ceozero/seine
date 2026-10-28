#!/bin/bash
# Kernel A/B screen on a cohort host after remote_bench.sh (reuses its user/isolation).
# Usage (root, /opt/cohort): remote_kernel_ab.sh <baseline-kernel> <candidate-kernel> <threads...>
# Expects candidate/seine and candidate/verify_cpu_kernels. Full-size reference
# parity runs first; timing is skipped if it fails. One ABBA pair per thread count.
# SEINE_ARGS adds flags to every run, e.g. SEINE_ARGS="--cpu-page-mode regular".
set -u
W=/opt/cohort
R=$W/results/ab-$1-vs-$2
BASE=$1 CAND=$2; shift 2
SECS=${SECS:-20}
mkdir -p "$R"; chown -R bench:bench "$W"
isolated() {
  local dir=$1; shift
  unshare -n setpriv --reuid=bench --regid=bench --init-groups --reset-env -- \
    env HOME=/home/bench PATH=/usr/bin:/bin bash -c 'cd "$0" && exec "$@"' "$dir" "$@"
}
isolated "$W/candidate" ./verify_cpu_kernels > "$R/parity.log" 2>&1 || { echo PARITY-FAILED; touch "$R/COMPLETE"; exit 1; }
grep -q "^$CAND: PASS" "$R/parity.log" || { echo "PARITY-MISSING $CAND"; touch "$R/COMPLETE"; exit 1; }
one() { # one <kernel> <threads> <tag>
  sync; echo 3 > /proc/sys/vm/drop_caches
  isolated "$W/candidate" ./seine --bench --bench-kind backend --backend cpu --ui plain \
    --data-dir /home/bench/seine-ab --threads "$2" --disable-cpu-autotune-threads --bench-cpu-kernel "$1" ${SEINE_ARGS:-} \
    --bench-secs "$SECS" --bench-rounds "${ROUNDS:-1}" --bench-warmup-rounds 1 --bench-output "$R/$3.json" > "$R/$3.log" 2>&1
  python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(sys.argv[2], round(d['avg_hps'], 3))" "$R/$3.json" "$3"
}
for t in "$@"; do
  one "$BASE" "$t" "t$t-1-$BASE"; one "$CAND" "$t" "t$t-2-$CAND"
  one "$CAND" "$t" "t$t-3-$CAND"; one "$BASE" "$t" "t$t-4-$BASE"
done | tee "$R/summary.txt"
touch "$R/COMPLETE"
