# Shutdown during an in-flight telemetry upload — October 27, 2026

The earlier shutdown fix removed the running marker before the final HTTP
upload. A request already in progress could still delay that removal: the
worker had to finish a pending-report replay or periodic upload before it
received the completion signal. Its HTTP timeout can outlast the Windows
console-close cleanup allowance, leaving a false unfinished-run marker even
though mining had completed.

## Reproduction and fix

A local TCP fixture holds a pending-report replay open, then drops the mining
telemetry worker. Before the fix, the running marker remains throughout the
one-second observation window. The new regression test failed on the original
code and passes after the change. It also verifies that a live run retains its
marker, spool ownership remains exclusive during upload, a failed replay
preserves its exact report ID, and reopening the store sees a clean previous
exit.

The mining thread now marks completion independently of the upload loop. It
clears only the running marker and checkpoint; the uploader retains its OS
file lock and pending report. Store completion and checkpoint writes share a
mutex, so a racing or later checkpoint cannot recreate the finished marker.
If shutdown precedes background store initialization, attaching the store
immediately finishes it. No completion lock spans HTTP work.

## Verification

- All 16 reporting-worker tests pass, including the slow replay reproduction,
  slow final upload, late store attachment, concurrent checkpoints, pending
  delivery, privacy, opt-out and restart throttling. An exited uploader releases
  its OS lock, and the old mining worker cannot clear a subsequent run's marker.
- All 10 diagnostics tests pass, including abnormal-exit recovery and exclusive
  store ownership.
- Windows GNU miner compilation passes with NVIDIA and AMD enabled.
- Pinned formatting and whitespace checks pass for the changed files.

This removes a reproduced source of false unfinished-run reports; it does not
establish the historical cause of the original fleet alert. Native crashes,
forced termination before mining cleanup, or failed filesystem writes can
still leave an unfinished marker. Upload waits remain subject to their
existing timeout. There is no telemetry schema change, release tag or
production deployment in this follow-up.
