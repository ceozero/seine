# Schema-7 collector deployment receipt — October 27, 2026

Under the user's approval for additional reliability telemetry, the collector
was updated from exact tested commit
`f2d0217dbfd83e51c3b7eb2489806c0744d4acef`. Replacement began at **00:24:59 EDT**
and post-replacement infrastructure checks passed at **00:25:10 EDT**. This is
the replacement interval, not a measured client outage duration.

Only Compose service `collector` was replaced. No database migration, pool,
Stratum, daemon or HTTPS restart, miner release or test Discord message occurred.

## Source and rollback

- Immutable build inputs: `/opt/seine-collector-releases/f2d0217`, archived from
  the tested commit's manifests, lockfile, pow crates and telemetry directory.
  The production Dockerfile built the locked Rust 1.93 release collector.
- Image tag: `seine-telemetry-reviewed:f2d0217dbfd83e51c3b7eb2489806c0744d4acef`.
- Running image: `sha256:aad1940be54b94042b58916851cf802fea8196f80370c712d5c24a5feeb62a7b`.
- Previous image: `sha256:88b7e18b76a9cbef3897d987a805d39f6ded0c7455d16cb5785e8e4bfb843e5c`.
- Root-only state: `/var/lib/seine-telemetry-schema7.fJArGWXt`; its `candidate.yaml`
  selects the deployed image and `rollback.yaml` selects the saved previous image.
  `/var/lib/seine-telemetry-active-schema7-state` points to this directory.
- `/opt/seine` remains at `af236c276e01080ff15863d4e716dd13e07f3b9d`; its existing
  modified `telemetry/alerts.py` was preserved byte-for-byte. No checkout files
  were overwritten. The running image's source is the immutable archive above,
  not the operational checkout. Updated aggregate analysis is available from
  the archive's `telemetry/agent_report.py` or the latest local checkout.

Use the retained candidate override with subsequent `up --no-build` commands.
For rollback, use the same project directory, environment and base Compose file,
then append `-f /var/lib/seine-telemetry-schema7.fJArGWXt/rollback.yaml` and run
`up -d --no-deps --no-build collector`. Retest infrastructure afterward.

## Verification

- Fresh recovery backup finished successfully before replacement.
- HTTPS, database, retention, disk and backup checks passed before and after.
- Public `https://telemetry.seineminer.com/healthz` returned 204 afterward.
- Running image ID matched the built candidate exactly.
- Database and HTTPS container IDs and start timestamps matched their saved
  pre-deployment values exactly; the alert script's SHA-256 also matched.
- Archived schema and SQL SHA-256 hashes matched the committed local files.
- Schema 1–7 HTTP acceptance, persistence, privacy rejection and downgrade
  rejection were tested against a disposable collector/PostgreSQL before rollout.
  No synthetic payloads were sent to production.

Existing reliability and legacy sample-quality alerts can remain active. The
collector update cannot fix already distributed miners or reconstruct past
termination causes. A miner release and adoption are needed for the new shutdown
requests and typed loader causes. See the [fix validation](reliability-followup-20261027.md).
