#!/bin/bash
# A/B driver: lease -> upload baseline/candidate builds -> run remote steps -> collect -> delete.
# Usage: scripts/cohort/ab.sh <lease-name> <out-dir> <baseline-dir> <candidate-dir> <remote-step>...
# Each build dir holds seine and verify_cpu_kernels. Remote steps run in order on
# the host from /opt/cohort as root, e.g. "remote_bin_ab.sh depth avx2-stream 12 24".
# Optional EXTRA_DIR (for example competitor binaries) is uploaded as /opt/cohort/extra.
# The lease is deleted on exit; its systemd timer remains the backstop.
# KEEP_LEASE=1 keeps it on success for a follow-up screen (rerun ab.sh with the same
# name; each run uploads into a fresh /opt/cohort/results and steps).
set -euo pipefail
if [ -z "${COHORT_RUN_COPY:-}" ]; then  # run from a private copy (safe to edit mid-run)
  copy=$(mktemp); cp "$0" "$copy"
  COHORT_RUN_COPY=1 COHORT_HERE=$(cd "$(dirname "$0")" && pwd) exec bash "$copy" "$@"
fi
NAME=$1 OUT=$2 BASE=$3 CAND=$4; shift 4
HERE=$COHORT_HERE
LEASE=$HOME/.cache/seine-hashrate/leases/$NAME.json
KEY=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['key'])" "$LEASE")
PROVIDER=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('provider', 'cherry'))" "$LEASE")
TOOL=$HERE/$PROVIDER.py
mkdir -p "$OUT"
# Delete on completion or error. A signal (e.g. an interrupted agent turn) keeps
# the lease so the remote job can finish; its systemd timer still deletes it.
if [ "${KEEP_LEASE:-0}" = 1 ]; then
  trap '[ $? = 0 ] && echo "kept $NAME for a follow-up run" >&2 || python3 "$TOOL" down "$NAME" || echo "DELETE FAILED for $NAME" >&2' EXIT
else
  trap 'python3 "$TOOL" down "$NAME" || echo "DELETE FAILED for $NAME" >&2' EXIT
fi
trap 'trap - EXIT; echo "interrupted: keeping $NAME for its timer" >&2; exit 130' INT TERM HUP

IP=$(python3 "$TOOL" ip "$NAME")
echo "$NAME at $IP"
SSH=(ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=30 -o LogLevel=ERROR
     -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile="$OUT/known_hosts" "root@$IP")
retry() { for i in 1 2 3 4 5 6 7 8; do timeout 300 "$@" && return 0; sleep $((i * 5)); done; return 1; }
for _ in $(seq 60); do timeout 20 "${SSH[@]}" true 2>/dev/null && break; sleep 10; done

stage=$(mktemp -d)
mkdir -p "$stage/baseline" "$stage/candidate"
cp "$BASE"/seine "$BASE"/verify_cpu_kernels "$stage/baseline/"
cp "$CAND"/seine "$CAND"/verify_cpu_kernels "$stage/candidate/"
cp "$HERE"/remote_*.sh "$HERE"/pool_fixture.py "$stage/"
if [ -n "${EXTRA_DIR:-}" ]; then cp -r "$EXTRA_DIR" "$stage/extra"; fi
retry bash -c "tar -C '$stage' -czf - . | $(printf '%q ' "${SSH[@]}") 'mkdir -p /opt/cohort && tar -C /opt/cohort -xzf -'"
id bench >/dev/null 2>&1 || true
STEPS=$(printf '%s; ' "$@")
retry "${SSH[@]}" "id bench >/dev/null 2>&1 || useradd -m bench; cd /opt/cohort && rm -rf results AB-DONE && (nohup bash -c '$STEPS touch /opt/cohort/AB-DONE' > ab-progress.log 2>&1 &)"

until timeout 20 "${SSH[@]}" test -e /opt/cohort/AB-DONE 2>/dev/null; do sleep 30; done
retry bash -c "$(printf '%q ' "${SSH[@]}") 'tar -C /opt/cohort -czf - results ab-progress.log' | tar -C '$OUT' -xzf -"
find "$OUT/results" -name summary.txt -exec sh -c 'echo "== $1"; cat "$1"' _ {} \;
