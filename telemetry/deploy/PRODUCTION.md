# Production collector

The running collector now supports schema 7, deployed October 27 at 00:25 EDT
from `f2d0217dbfd83e51c3b7eb2489806c0744d4acef`. See the
[deployment receipt](../../docs/validation/collector-schema7-deployment-20261027.md).
Its immutable build source is `/opt/seine-collector-releases/f2d0217`; the
operational `/opt/seine` checkout and its existing alert-script modification were
preserved. Use the retained image override recorded in that receipt for subsequent
`up --no-build` operations. Schemas 1–6 remain accepted; no miner release was made.

- Host: `root@2.31.36.180` (Hetzner, Falkenstein; 4 vCPU, 8 GB RAM, 80 GB disk).
- OS: Ubuntu 26.04 LTS; distro Docker Engine and Compose packages.
- Checkout: `/opt/seine`, canonical `master`.
- Ingest: `https://telemetry.seineminer.com/v1/reports`.
- DNS: direct A record, Cloudflare proxy disabled.
- Secrets: `/opt/seine/telemetry/deploy/.env`, root-only permissions.
- Published ports: SSH 22, HTTP 80 (redirect/ACME), HTTPS 443. PostgreSQL and
  collector ports are private to the Compose network. SSH is key-only.
- Docker restarts containers after reboot; unattended OS security updates are enabled.
- Recovery backups: daily under `/var/backups/seine-telemetry`, seven days of
  reports per backup, seven-day backup retention. Local storage only: server loss
  also loses these backups. Do not enable long-lived VM snapshots containing reports.

## Operations

```sh
ssh root@2.31.36.180
cd /opt/seine
docker compose -f telemetry/deploy/compose.yaml --env-file telemetry/deploy/.env ps
systemctl status seine-telemetry-backup.timer seine-telemetry-check.timer
systemctl start seine-telemetry-check.service
journalctl -u seine-telemetry-check.service -n 20
```

The five-minute check verifies local HTTPS certificate/response, database queries,
retention progress, disk headroom, backup freshness and sustained inventory-only
reporting (sample completeness). A failed check appears in
systemd/journald. The separate five-minute alert timer sends confirmed incidents
to the existing pool Discord alerts channel. Public DNS/reachability should also
be checked from outside the server:

```sh
curl -sS -o /dev/null -w '%{http_code}\n' https://telemetry.seineminer.com/healthz
```

Expect HTTP 204. This public endpoint alone does not verify the database.

Schema 6 miners require the upgraded collector; deploy it before the miner release.
The upgraded collector still accepts schemas 1–5. Deploy updated `tuning_report.sql`,
`diagnostics.sql`, `alerts.py` and `agent_report.py` with it to expose paired research
hints, recovered diagnostics and correct interrupted-release attribution. The collector must be rebuilt; scripts alone cannot
accept schema 6. No database migration or pool/daemon restart is required.
Paired-trial producer hooks need runtime integration too; collector upgrade alone
does not produce fleet trial evidence. See [the contract](../TUNING.md).
Old checkpoints with an unambiguous observed build mapping can be attributed now;
missing release/evidence fields cannot be recovered from existing payloads.
Existing records remain readable; missing cause details cannot be reconstructed. After this upgrade, the
completeness check may continue failing for old pool miners until they upgrade
or their inventory-only reports leave the six-hour window. Use the agent
briefing's per-version data-quality result to distinguish that known client
problem from a collector, backup or database failure.

The check also flags miner reliability incidents affecting at least three
installations of one version in 24 hours. `telemetry/agent_report.py` provides
aggregate issue clusters and diagnostic coverage, including lower-volume issues.
These checks are recorded in journald and evaluated independently by the alert runner.
Legacy inventory-only reports produce their own version-specific alert; they do not
prevent collector outages or miner failures from being reported.

The [October 26 schema-6 rollout proposal](ROLLOUT-SCHEMA6-20261026.md) pins the
reviewed target and records acceptance checks, exact collector-only commands and
image rollback. The approved collector-only rollout completed October 26 at
14:49 EDT on exact source `af236c276e01080ff15863d4e716dd13e07f3b9d`; see the
[deployment receipt](../../docs/validation/collector-schema6-deployment-20261026.md)
for image IDs, retained overrides and verification. Further deployments require
an explicit request.

For deployment, first review the intended commit and create a fresh recovery backup.
Then fast-forward the checkout and rebuild only the collector:

```sh
systemctl start seine-telemetry-backup.service
git pull --ff-only origin master
docker compose -f telemetry/deploy/compose.yaml --env-file telemetry/deploy/.env up -d --no-deps --build collector
systemctl start seine-telemetry-check.service
```

Keep the previous collector image ID before an upgrade for rollback. Do not run
`docker compose down -v`: the volumes hold reports and TLS certificates.
See [the operator guide](../README.md#recovery-backups) for restore procedures;
always verify a restore in a separate database before replacing live data.

Official miner builds use the GitHub repository variable `SEINE_TELEMETRY_URL`.
Changing it affects future builds; shipped clients keep their saved endpoint and
opt-out preference. The policy is published at <https://seineminer.com/privacy/>.

## Discord fleet alerts

`seine-telemetry-alerts.timer` runs `telemetry/alerts.py` every five minutes.
It uses the pool's existing Discord alerts destination, stored separately as
`DISCORD_WEBHOOK_URL` in root-only `/etc/seine/telemetry-alerts.env`. Never commit
or print that file. It is independent of the collector container and does not
restart miners, Stratum, the daemon, or the collector.

The runner evaluates these independent categories:

- Infrastructure: HTTPS, database, retention, disk and recovery backup checks.
- Ingestion: no periodic release reports for two hours (including an empty DB).
- Sample quality: five installations of one version with three inventory-only
  reports spanning two hours within the last six hours.
- Reliability: errors/quarantines or unclean previous runs on three distinct
  installations of one version in 24 hours. Interrupted runs use their previous
  release, resolved from the checkpoint or an unambiguous observed build mapping.
  Unattributed runs use an explicitly unknown-version bucket. The restart version
  is never substituted. An unclean run is not proof of a crash.
- Performance: matching installation, hardware/environment, build target/features
  and backend settings across the recent 36 hours versus the preceding part of
  the seven-day window. Each period/version requires three reports spanning 24
  hours. At least five paired installations, a median rate ratio at or below
  0.8, and at least 60% (minimum three) down 20% are required. Each installation
  has equal weight; duplicate devices cannot inflate the population. This is
  an observational screening alert, not proof of a release regression.
- Monitor: a query times out or cannot be read. Failed queries do not clear
  previously reported incidents in the affected categories.

Opening and clearing require two observations at least four minutes apart;
normal delivery occurs on the next five-minute tick. Sample quality, reliability
and performance incidents notify once when opened and once when cleared, with no
periodic reminders while active. Counts and descriptions continue updating in
state and reports. A new version/cohort or a confirmed recurrence after clearing
can notify again. Infrastructure, ingestion and monitor outages retain four-hour
reminders. Existing delivered incidents become quiet immediately without resetting
state. A gap longer than 15 minutes resets pending confirmation.
Clearing means the threshold cleared or its observations aged out, not that
all affected miners demonstrably recovered. Missing diagnostic coverage is
not evidence of healthy miners; inspect coverage with `agent_report.py`.

State is stored atomically in `/var/lib/seine-telemetry-alerts/state.json` with
an exclusive process lock. Only successful HTTP delivery acknowledges a notice;
HTTP failures (including rate limits) retry on the next timer tick. Delivery
is at least once: a process crash between HTTP success and saving state can
repeat a notice. At most ten messages are sent per run, oldest unsent first.
Messages contain aggregate counts and bounded hardware/version labels, never
installation IDs, raw logs or credentials. Mentions and redirects are disabled.

Notifications use Discord embed cards with the pool relay's blue informational,
orange warning, red critical and green cleared colors. The incident key and
Eastern timestamp appear in the footer. Known v0.2.24/v0.2.25 pool sampling gaps
are informational and recommend v0.2.26 or later; other versions remain warnings.
Thresholds, confirmation and incident identities are preserved. Missing samples do not establish lost mining or earnings.

Preview the real formatter's synthetic payloads locally (no Discord sends):

```sh
python3 telemetry/showcase/serve.py --port 9081
# http://localhost:9081/alerts.json
# Select ?state=legacy|warning|reminder|cleared|critical|setup|old-state|quiet-lifecycle
# Interrupted runs: ?state=unclean-upgrade|unclean-unknown|unclean-cleared
```

The preview labels the current source revision. It shows actual webhook JSON,
not a reproduction of Discord's rendering. Loading/empty/disabled states are not
outgoing messages; HTTP failures remain pending for retry. A native Discord visual
check requires an explicitly authorized test message. Updating only `alerts.py`
needs no collector rebuild or service restart; the next timer tick loads it.

To inspect without writing state or sending messages:

```sh
python3 /opt/seine/telemetry/alerts.py --dry-run
systemctl status seine-telemetry-alerts.timer
journalctl -u seine-telemetry-alerts.service -n 20
```

To install after configuring the root-only environment file and reviewing the
commit (no collector rebuild needed):

```sh
install -m 0644 telemetry/deploy/seine-telemetry-alerts.{service,timer} /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now seine-telemetry-alerts.timer
systemctl start seine-telemetry-alerts.service
```

Disable with `systemctl disable --now seine-telemetry-alerts.timer`; retain state
unless intentionally resetting incident deduplication. The original health timer
continues independently. The alert runner can run when Docker is stopped, but
cannot deliver during host/network loss or a Discord outage. Journald records
delivery failures. Outside-in uptime checks and off-host backups remain separate
operational gaps; this change does not claim to cover them.
