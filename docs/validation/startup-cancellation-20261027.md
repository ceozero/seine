# Startup cancellation follow-up — October 27, 2026

The read-only fleet report at 00:27 EDT still showed the previously observed
v0.2.38 reliability events. The schema 7 collector was healthy; the miner fixes
have not been released. This follow-up establishes additional defects in the
startup code, not the historical cause of any individual unfinished run.

## Changes

- Backend initialization used an ordinary error for a requested shutdown.
  Activation then emitted driver advice, backend failure and potentially
  no-backend/run-failed diagnostics. Cancellation now has a distinct error
  type, survives error contexts, and becomes successful completion at the
  mining entry point. Actual delivered backend errors retain their failure
  details even when shutdown is requested concurrently.
- NVIDIA-only startup blocked on the deferred backend channel. It now polls
  shutdown at 100 ms intervals without requiring the initialization sender to
  finish. The synchronous and deferred initialization paths share the same
  cancellable startup helper.
- Previously, cancellation called `stop()` concurrently with an outstanding
  native `start()`. The initialization thread now owns cleanup after its call
  returns. A rendezvous result channel prevents a successful result being left
  buffered after its receiver cancels. Already activated backends are stopped
  when activation is cancelled.
- Startup error wrapping discarded the underlying error chain, preventing
  extraction of numeric OS errors. Context now preserves that chain, and
  deferred NVIDIA startup failures use the same structured failure recorder
  as synchronous activation. Existing telemetry fields suffice; raw error
  messages and paths are not added to reports.

## Verification

Six regression tests cover cancellation before startup, cancellation while a
mock native initializer is blocked, cleanup of earlier and late backends,
successful exit at the mining entry point, genuine OS errors concurrent with
shutdown, and pending/disconnected deferred channels. Tests verify that `stop()`
does not run concurrently with the blocked initializer. No real mining or GPU
kernels are needed.

- `cargo +1.93.0 test -p seine --bin seine --features amd startup_ -- --test-threads=1`:
  24 passed; one pre-existing hardware/cgroup probe intentionally ignored.
- `cargo +1.93.0 test -p seine --bin seine --features amd miner::tests:: -- --test-threads=1`:
  all 55 tests passed, including successful activation, failure quarantine,
  scheduling and the six new regressions.
- Windows GNU cross-check with NVIDIA and AMD enabled passed.
- Linux CPU-only miner check passed.

This makes the waiting control path cancellable; it cannot forcibly interrupt
a stuck native driver/compiler call. If that call never returns, its thread
ends when the process exits. No release tag or production restart is part of
this follow-up.
