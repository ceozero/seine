# Schema-8 collector deployment receipt — October 27, 2026

Deployed under the user's explicit request to deploy the added telemetry. The
collector was built from tested commit
`c92833dd13047a5ea5760edb3563bf99d145b27a`. Replacement began at **01:22:45 EDT**;
post-replacement infrastructure checks passed at **01:22:56 EDT**. This is the
replacement interval, not a measured client outage duration.

Only Compose service `collector` was replaced. No database migration, pool,
Stratum, daemon or HTTPS restart, miner release, or test Discord message occurred.
The new fields still require adoption of a miner release containing schema 8.

## Source and rollback

- Immutable build inputs: `/opt/seine-collector-releases/c92833d`, exported from
  the tested commit's manifests, lockfile, pow crates and telemetry directory.
- Image tag: `seine-telemetry-reviewed:c92833dd13047a5ea5760edb3563bf99d145b27a`.
- Running image: `sha256:05ed598904739b0366c1b7216f564baa5df04d4720f4765e9089f1aa64c3fd5a`.
- Previous image: `sha256:aad1940be54b94042b58916851cf802fea8196f80370c712d5c24a5feeb62a7b`.
- Root-only state: `/var/lib/seine-telemetry-schema8.OVZ9oLN0`. `candidate.yaml`
  selects the deployed image; `rollback.yaml` selects the previous image.
  `/var/lib/seine-telemetry-active-schema8-state` points to this directory.
- The production checkout and its pre-existing `telemetry/alerts.py` edit remain
  unchanged. The running source is the immutable archive, not that checkout.
  Updated aggregate analysis is available in the archive or current repository.

For subsequent Compose operations, retain the candidate override. For rollback:

```sh
docker compose \
  --project-directory /opt/seine/telemetry/deploy \
  --env-file /opt/seine/telemetry/deploy/.env \
  -f /opt/seine/telemetry/deploy/compose.yaml \
  -f /var/lib/seine-telemetry-schema8.OVZ9oLN0/rollback.yaml \
  up -d --no-deps --no-build collector
/opt/seine/telemetry/deploy/check.sh --infrastructure-only </dev/null
```

Rollback restores schema-7 acceptance; schema-8 miners would then be rejected.
Do not release schema-8 miners against a rolled-back schema-7 collector.

## Verification

- Fresh recovery backup completed before replacement.
- Locked Rust 1.93 production image build succeeded. Image revision label is the
  exact tested commit; running image ID equals the built candidate.
- Archived schema and diagnostic SQL SHA-256 hashes match the committed source.
- HTTPS, database, retention, disk and backup checks passed before and after.
- Public `https://telemetry.seineminer.com/healthz` returned HTTP 204.
- Database and HTTPS container IDs, image IDs and start timestamps remained
  identical; the existing alert script's SHA-256 remained identical.
- A natural schema-4 miner report arrived at **01:23:09 EDT**, after replacement.
  No synthetic reports were inserted into production.
- The updated read-only aggregate SQL ran successfully on production. Existing
  reliability attention remained; no new shutdown-context clusters existed yet.
  Collector rollout does not resolve historical miner failures or backfill
  instrumentation absent from older miners.
- Schema-8 acceptance, persistence, legacy compatibility, private-field rejection
  and downgrade rejection were already validated with a disposable collector and
  PostgreSQL before deployment. See [implementation validation](reliability-context-20261027.md).

The root-only state directory retains the before/after receipt, aggregate report
verification and rollback override. No temporary test services were started on
production.
