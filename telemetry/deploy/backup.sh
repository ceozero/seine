#!/usr/bin/env bash
# Local recovery backup: seven days of reports, kept for seven days at most.
set -euo pipefail
umask 077
deploy_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
backup_dir="${TELEMETRY_BACKUP_DIR:-/var/backups/seine-telemetry}"
mkdir -p -- "$backup_dir"
chmod 700 "$backup_dir"
exec 9>"$backup_dir/.lock"
flock -n 9 || exit 0
# Purge before connecting so an unavailable database does not prevent expiry.
find "$backup_dir" -mindepth 1 -maxdepth 1 -type d -name 'telemetry-*' -mmin +10080 -exec rm -rf -- {} +
compose=(docker compose --project-directory "$deploy_dir" --env-file "$deploy_dir/.env" -f "$deploy_dir/compose.yaml")
temporary="$(mktemp -d "$backup_dir/.partial-XXXXXXXX")"
trap 'rm -rf -- "$temporary"' EXIT
"${compose[@]}" exec -T db pg_dump -U telemetry -d telemetry --schema-only --no-owner --no-privileges > "$temporary/schema.sql"
"${compose[@]}" exec -T db psql -U telemetry -d telemetry -v ON_ERROR_STOP=1 -c "COPY (SELECT report_id, installation_id, received_at, payload FROM telemetry_reports WHERE received_at >= now() - interval '7 days') TO STDOUT WITH (FORMAT csv)" | gzip > "$temporary/reports.csv.gz"
gzip -t "$temporary/reports.csv.gz"
mv -T -- "$temporary" "$backup_dir/telemetry-$(date -u +%Y%m%dT%H%M%SZ)"
trap - EXIT
echo 'Telemetry recovery backup completed.'
