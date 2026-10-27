# Schema-6 collector rollout proposal — October 26, 2026

**Approved and executed October 26, 2026 at 14:49 EDT.** See the
[deployment receipt](../../docs/validation/collector-schema6-deployment-20261026.md)
for exact images, health checks and retained rollback state. These commands remain
the reviewed runbook; future deployments/restarts need a new explicit request.
No miner release is included. Deploy this collector before the next schema-6 miner
release; the new binary accepts schemas 1–6 without a database migration.

- Target source: `af236c276e01080ff15863d4e716dd13e07f3b9d`.
- Host: `root@2.31.36.180`; checkout `/opt/seine`, branch `master`.
- Compose file: `/opt/seine/telemetry/deploy/compose.yaml`; service **collector**.
- Ingest: `https://telemetry.seineminer.com/v1/reports`.
- Expected impact: brief telemetry upload interruption while replacing the
  collector. Mining continues. No pool, Stratum, daemon, database or Caddy restart.
- Previously reported checkout: `a52cdf2` at 03:30 EDT on October 26. This is an
  observation, not proof of the currently running image. Capture both at rollout.

## Reviewed acceptance evidence

At the target source, the collector package's 12 tests pass; HTTP integration
against disposable PostgreSQL 16 accepts schema 1, 2, 3, 4, 5 and 6 fixtures and
rejects invalid fields, schema downgrades, oversized reports and duplicates/rate
excess. Schema-5 recovered evidence persists. Schema-6 short/full window rules
persist and analyze correctly. A report emitted by the runtime Monitor passes
HTTP/storage/SQL boundaries: five synthetic installations qualify one research
hint; changed or unknown context cannot qualify; costs remain null when unknown.
22 SQL tests and seven briefing tests also pass.

No synthetic reports were uploaded to production. Reproduce the producer boundary
with [the validation commands](../../docs/validation/trial-placement-20261026.md).
Use `telemetry/test_integration.py` only with a disposable collector/database.
Do not use production credentials or upload fixtures to the public ingest URL.

The build must use the pinned source and `telemetry/deploy/Dockerfile`, whose
Rust 1.93 build runs `cargo build --locked --release -p seine-telemetry --features server`.
Do not substitute an unreviewed moving branch tip. The Docker image itself is built
on the server after approval; its image ID must be recorded before replacement.

## Exact deployment commands after authorization

Run in a single Bash session on the target host. Stop if the checkout is dirty,
not on master, or cannot fast-forward to the reviewed target. Never reset/force it.
No secret values are printed by these commands.

```bash
ssh root@2.31.36.180
set -euo pipefail
cd /opt/seine
umask 077
rollout_target=af236c276e01080ff15863d4e716dd13e07f3b9d
compose=(docker compose --project-directory /opt/seine/telemetry/deploy \
  --env-file /opt/seine/telemetry/deploy/.env \
  -f /opt/seine/telemetry/deploy/compose.yaml)
test "$(git branch --show-current)" = master
test -z "$(git status --porcelain)"
git fetch origin master
git merge-base --is-ancestor HEAD "$rollout_target"
git merge-base --is-ancestor "$rollout_target" origin/master
previous_commit=$(git rev-parse HEAD)
previous_container=$("${compose[@]}" ps -q collector)
test -n "$previous_container"
previous_image=$(docker inspect --format '{{.Image}}' "$previous_container")
rollback_tag="seine-telemetry-rollback:$(date -u +%Y%m%dT%H%M%SZ)"
docker image tag "$previous_image" "$rollback_tag"
rollout_state=$(mktemp -d /var/lib/seine-telemetry-rollout.XXXXXXXX)
printf '%s\n' "$previous_commit" > "$rollout_state/previous-commit"
printf '%s\n' "$previous_image" > "$rollout_state/previous-image"
printf '%s\n' "$rollout_target" > "$rollout_state/target-commit"
printf 'services:\n  collector:\n    image: %s\n' "$rollback_tag" > "$rollout_state/rollback.yaml"
printf 'Rollback state: %s\n' "$rollout_state"

systemctl start seine-telemetry-backup.service
bash telemetry/deploy/check.sh --infrastructure-only
git merge --ff-only "$rollout_target"
test "$(git rev-parse HEAD)" = "$rollout_target"
candidate_tag="seine-telemetry-reviewed:$rollout_target"
printf 'services:\n  collector:\n    image: %s\n' "$candidate_tag" > "$rollout_state/candidate.yaml"
"${compose[@]}" -f "$rollout_state/candidate.yaml" build collector
candidate_image=$(docker image inspect --format '{{.Id}}' "$candidate_tag")
printf '%s\n' "$candidate_image" > "$rollout_state/candidate-image"
"${compose[@]}" -f "$rollout_state/candidate.yaml" up -d --no-deps --no-build collector
"${compose[@]}" ps collector
candidate_container=$("${compose[@]}" ps -q collector)
test "$(docker inspect --format '{{.Image}}' "$candidate_container")" = "$candidate_image"
bash telemetry/deploy/check.sh --infrastructure-only
"${compose[@]}" exec -T db psql -X -U telemetry -d telemetry -At \
  -v ON_ERROR_STOP=1 -c "SELECT payload->>'schema_version', count(*) FROM telemetry_reports WHERE received_at >= now()-interval '1 hour' GROUP BY 1 ORDER BY 1"
```

Outside the server, confirm public HTTP 204 and run the aggregate read-only report
from a local checkout containing the target telemetry scripts:

```sh
curl --silent --show-error --max-time 10 -o /dev/null -w '%{http_code}\n' \
  https://telemetry.seineminer.com/healthz
python3 telemetry/agent_report.py
```

If the first health request races startup, inspect the collector's startup result
and retry briefly; persistent failures require rollback. Record the running image
ID and compare it with the built candidate. Check storage/backup health separately
from legacy sample quality and unclean-run warnings. Existing alerts may remain
active and are not proof of a failed collector rollout. Existing alert timers pick
up the updated scripts; do not manually send a test alert. Schema-6 trial counts
may remain zero until a compatible miner is released and completes trials.

## Rollback

Rollback if the replacement collector persistently fails health/startup or rejects
previously supported valid traffic. In the same server session, use the saved image
without rebuilding or touching volumes:

```bash
"${compose[@]}" -f "$rollout_state/rollback.yaml" \
  up -d --no-deps --no-build collector
"${compose[@]}" ps collector
bash telemetry/deploy/check.sh --infrastructure-only
restored_container=$("${compose[@]}" ps -q collector)
test "$(docker inspect --format '{{.Image}}' "$restored_container")" = "$previous_image"
```

For a new shell, reconstruct `compose` as above and set `rollout_state` to the
recorded directory; read `previous_image` from its `previous-image` file. Preserve
that directory and tagged image through rollout observation. No schema migration
or database restore is needed. Do not use `down`, `down -v`, image pruning or a
full-stack restart. The checkout and backward-compatible reporting scripts stay
at the reviewed target; this rollback replaces only the collector image. Keep the selected
image override for subsequent `up --no-build` operations; omitting it may select a
different cached image. A later authorized `up --build` rebuilds from the checkout.
Record whether candidate or rollback is currently selected.

If schema-6 miners have already shipped, an older schema-4 collector will reject
their reports. In that situation restore a known schema-6-compatible image or
forward-fix; treat the old image only as temporary ingestion recovery for legacy
clients. The collector outage/rollback still must not interrupt mining.
