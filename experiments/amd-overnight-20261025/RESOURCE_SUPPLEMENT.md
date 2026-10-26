# Separate resource validation after an unexercised pressure fixture

Recorded 2026-10-25 before the supplementary run. The first native campaign
completed all sixteen productive windows but ended **FAILED** in its resource
fixture. Lowering `memory.high` led the miner to release arenas: 3 → 1 → 0
workers, followed by resumed work. Neither `memory.events:high` nor memory PSI
increased. The fixture's mandatory actual-reclaim check therefore stopped the
test before constrained restart and opt-out. This is incomplete validation;
it must not be silently relabelled as a successful original campaign.

Original verified archive SHA-256:
`57a24c115e41b315427fc831e64c30dfb1127d9e8dae9d0f8c8426c87641176b`.
All 281 manifest entries verified, settings restored, no cleanup failures.
Keep its outcomes, checksums and all measured productive windows unchanged.

The supplement uses the **same frozen candidate executable** in a fresh remote
directory, fresh caches and separate service names. It repeats the complete
ordinary-page, four-CPU lifecycle with its original 600-second initial phase.
During the 30-second zero-arena phase, a bounded helper joins the task-owned
miner's cgroup and writes each page of at most 2 GiB. Its requested lifetime is
20 seconds, with bounded termination at the end of the 30-second phase.
This crosses the 1 GiB soft limit even after the miner releases its own arenas;
the 16 GiB hard limit remains unchanged. The helper is stopped before recovery.
Memory recovery is observed for 90 seconds, allowing the real pressure backoff
to clear. The subsequent CPU-contention, load-recovery, constrained process
restart, 210-second restart recovery and explicit opt-out checks are unchanged.

Retain the mandatory increase in actual `memory.events:high`; additionally
require memory PSI totals to increase. Keep all original no-OOM, productive
progress, worker parking, remembered-count preservation, real arena allocation,
CPU scheduling-pressure and explicit opt-out assertions. Do not treat helper
allocations as miner arenas: restart recovery checks the miner process's own
anonymous RSS after the helper has exited.

The helper and controller have process-group cleanup, service runtime bounds
and explicit restoration checks. Keep swap disabled during this resource run,
then restore the original unused swap; both hugepage pools remain zero. No
power, affinity, kernel, worker policy or performance interval changes.

Only a separately collected, fully verified successful supplement can complete
the missing resource gate for these same frozen builds. Reports must identify
the failed original fixture and the additional evidence. Do not rerun or choose
between productive performance samples. The existing $9.60 Cherry / $12.85 total
reservation covers a 30-minute resource/cleanup window and collection; the running
throughput protocol is already terminal and no original deadline is extended.
