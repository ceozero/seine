# Schema-6 collector deployment receipt — October 26, 2026

The user approved the exact reviewed collector revision. Deployment completed on
`root@2.31.36.180` with `/opt/seine` on `master` at
`af236c276e01080ff15863d4e716dd13e07f3b9d`. Later master changes, including the
kernel retry admission change, were not included in this deployment.

Collector replacement began at **14:49:28 EDT**; the new container started and
infrastructure verification passed at **14:49:39 EDT**. This is the replacement
window, not a measured client outage duration. Only Compose service `collector`
was replaced with `up -d --no-deps --no-build` using the reviewed image override.

## Image and rollback receipt

- Previous source: `a52cdf215b37a16d0929c1d805ed145cbb59ed8d`.
- Previous image: `sha256:784e0c0d77f9eb7b7c7cdb4720832067cfcb4ef935e49aeba8f4cbdf3c89d4a5`.
- Running image: `sha256:88b7e18b76a9cbef3897d987a805d39f6ded0c7455d16cb5785e8e4bfb843e5c`.
- Candidate tag: `seine-telemetry-reviewed:af236c276e01080ff15863d4e716dd13e07f3b9d`.
- Saved old tag: `seine-telemetry-rollback:20261026T184733Z`.
- Root-only rollback state: `/var/lib/seine-telemetry-rollout.Iv8IqsIs`.

The running image ID exactly matched the built candidate; status was `running`
and restart count zero. The state directory retains previous/target commits,
image IDs, image override files, service identity snapshots and timestamps.
`candidate.yaml` selects the deployed image; `rollback.yaml` selects the saved
old image. Keep the selected override for later `up --no-build` operations.
Rollback was not needed. See [the reviewed commands](../../telemetry/deploy/ROLLOUT-SCHEMA6-20261026.md).

## Verification

- The existing checkout was clean and fast-forwarded to the exact approved SHA.
  Its pinned Rust 1.93 locked release collector build succeeded on the server.
- A fresh recovery backup completed successfully at **14:47:34 EDT**, exit zero.
- HTTPS, database queries, retention, disk headroom and backup freshness passed
  before replacement and after startup.
- Public `https://telemetry.seineminer.com/healthz` returned HTTP **204**.
- Database and Caddy container IDs and start timestamps matched their saved
  pre-deployment values exactly. Neither service restarted.
- Read-only agent briefing at **14:49:47 EDT** completed all aggregate queries.
  Infrastructure and inventory/performance query status were healthy.
- Four naturally arriving schema-1 reports were stored after replacement, between
  **14:49:59 and 14:50:04 EDT**. No synthetic report or test alert was sent to production.
- Schema 1–6 acceptance and rejection behavior had already passed the disposable
  collector integration suite at the approved source. No schema-5/6 production
  acceptance is claimed from this short post-deployment observation.

## Remaining client evidence

The agent briefing exits 1 because existing fleet conditions still need attention,
not because the collector or SQL queries failed. In its six-hour quality window,
135 v0.2.24 and 45 v0.2.25 installations met the sustained inventory-only threshold;
v0.2.26 had one such installation. Newer reported versions had none. Existing miner
reliability incidents still exceeded the diagnostic threshold. An unclean previous
run remains evidence of interruption, not proof of a crash or its cause.

There were zero paired trials in the analysis window. A compatible miner release
and adoption are still needed before new checkpoint/trial evidence can arrive.
This deployment included no miner or site release, pool/daemon/Stratum restart,
database migration/restore, manual Discord alert or changes to mining policy.
The approved deployment task is complete; further work is paused at the user's request.
