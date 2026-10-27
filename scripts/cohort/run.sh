#!/bin/bash
# One command per cohort host: wait for lease -> upload -> remote_bench.sh -> collect -> delete.
# Usage: scripts/cohort/run.sh <lease-name> <artifacts-dir> <out-dir> [--keep]
# The artifacts dir holds seine/, and optionally longhorn/, ntm/, pair/ (see remote_bench.sh).
# The lease is deleted on exit unless --keep; its systemd timer remains the backstop.
set -euo pipefail
# Run from a private copy: bash reads scripts incrementally, so editing this file
# mid-run would otherwise execute a mix of versions (and the EXIT trap deletes the lease).
if [ -z "${COHORT_RUN_COPY:-}" ]; then
  copy=$(mktemp); cp "$0" "$copy"
  COHORT_RUN_COPY=1 COHORT_HERE=$(cd "$(dirname "$0")" && pwd) exec bash "$copy" "$@"
fi
NAME=$1 ART=$2 OUT=$3 KEEP=${4:-}
HERE=$COHORT_HERE
LEASE=$HOME/.cache/seine-hashrate/leases/$NAME.json
KEY=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['key'])" "$LEASE")
PROVIDER=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('provider', 'cherry'))" "$LEASE")
TOOL=$HERE/$PROVIDER.py
mkdir -p "$OUT"

cleanup() {
  if [ "$KEEP" != --keep ]; then python3 "$TOOL" down "$NAME" || echo "DELETE FAILED for $NAME" >&2; fi
}
trap cleanup EXIT

IP=$(python3 "$TOOL" ip "$NAME")
echo "$NAME at $IP"
SSH=(ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=30
     -o StrictHostKeyChecking=accept-new -o LogLevel=ERROR -o UserKnownHostsFile="$OUT/known_hosts" "root@$IP")
for _ in $(seq 60); do "${SSH[@]}" true 2>/dev/null && break; sleep 10; done

tar -C "$ART" -czf - . | "${SSH[@]}" 'mkdir -p /opt/cohort && tar -C /opt/cohort -xzf -'
"${SSH[@]}" 'cat > /opt/cohort/remote_bench.sh' < "$HERE/remote_bench.sh"
"${SSH[@]}" "cd /opt/cohort && SECS=${SECS:-60} nohup bash remote_bench.sh > results-progress.log 2>&1 &"

# Poll; the remote job is detached, so a dropped SSH session does not stop it.
until "${SSH[@]}" test -e /opt/cohort/results/COMPLETE 2>/dev/null; do
  "${SSH[@]}" 'tail -1 /opt/cohort/results-progress.log' 2>/dev/null || true
  sleep 60
done
"${SSH[@]}" 'tar -C /opt/cohort -czf - results results-progress.log' | tar -C "$OUT" -xzf -
echo "results in $OUT/results"
