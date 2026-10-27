#!/bin/bash
# Windows A/B driver: lease (aws.py --windows) -> upload candidate dir -> run a
# remote PowerShell script -> collect -> delete. Signals keep the lease (timer backstop).
# Usage: scripts/cohort/win_ab.sh <lease> <out-dir> <candidate-dir> <ps1> [ps1 args...]
# The candidate dir holds seine.exe and verify_cpu_kernels.exe.
set -euo pipefail
if [ -z "${COHORT_RUN_COPY:-}" ]; then
  copy=$(mktemp); cp "$0" "$copy"
  COHORT_RUN_COPY=1 COHORT_HERE=$(cd "$(dirname "$0")" && pwd) exec bash "$copy" "$@"
fi
NAME=$1 OUT=$2 CAND=$3 PS1=$4; shift 4
HERE=$COHORT_HERE
LEASE=$HOME/.cache/seine-hashrate/leases/$NAME.json
KEY=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['key'])" "$LEASE")
mkdir -p "$OUT"
trap 'python3 "$HERE/aws.py" down "$NAME" || echo "DELETE FAILED for $NAME" >&2' EXIT
trap 'trap - EXIT; echo "interrupted: keeping $NAME for its timer" >&2; exit 130' INT TERM HUP
IP=$(python3 "$HERE/aws.py" ip "$NAME")
echo "$NAME at $IP"
OPTS=(-i "$KEY" -o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=30 -o LogLevel=ERROR
      -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile="$OUT/known_hosts")
for _ in $(seq 90); do timeout 20 ssh "${OPTS[@]}" "Administrator@$IP" 'echo ready' 2>/dev/null | grep -q ready && break; sleep 10; done
ssh "${OPTS[@]}" "Administrator@$IP" 'New-Item -ItemType Directory -Force C:\cohort\candidate | Out-Null'
scp "${OPTS[@]}" "$CAND"/seine.exe "$CAND"/verify_cpu_kernels.exe "Administrator@$IP:C:/cohort/candidate/"
scp "${OPTS[@]}" "$HERE/$PS1" "Administrator@$IP:C:/cohort/"
ssh "${OPTS[@]}" "Administrator@$IP" "powershell -ExecutionPolicy Bypass -File C:\\cohort\\$PS1 $*" || true
ssh "${OPTS[@]}" "Administrator@$IP" 'Compress-Archive -Force C:\cohort\results C:\cohort\results.zip'
scp "${OPTS[@]}" "Administrator@$IP:C:/cohort/results.zip" "$OUT/"
# PowerShell 5.1 archives use backslash separators; normalise while extracting.
python3 - "$OUT" <<'PY'
import pathlib, sys, zipfile
out = pathlib.Path(sys.argv[1])
with zipfile.ZipFile(out / 'results.zip') as z:
    for info in z.infolist():
        target = out / info.filename.replace('\\', '/')
        if info.filename.endswith(('/', '\\')):
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(z.read(info))
PY
find "$OUT" -name summary.txt -exec sh -c 'echo "== $1"; cat "$1"' _ {} \;
