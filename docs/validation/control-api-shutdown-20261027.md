# Control API shutdown with connected clients — October 27, 2026

## Confirmed defect

The control API awaited Axum's graceful HTTP shutdown before forwarding process
shutdown to the active mining session. Its SSE endpoint waited indefinitely on
the supervisor's broadcast channel, which remained open during that wait. An
attached dashboard could therefore prevent HTTP draining and indefinitely
delay the mining stop signal. This affects runs using the control API; it does
not establish the cause of the earlier fleet reports.

## Change

Process shutdown now reaches the mining session before HTTP draining. SSE
streams select on process shutdown as well as incoming events, prioritizing
shutdown when both are ready. Ordinary live events retain their existing
format. HTTP draining has a two-second allowance before the API proceeds to
its existing session cleanup and runtime teardown.

The allowance bounds the asynchronous HTTP drain stage, not the entire process
exit. It cannot preempt synchronous handlers, blocked native backend calls, or
the existing session-cleanup waits. No API request/response schema or telemetry
schema changes are required.

## Verification

- A local HTTP client keeps the real SSE route connected while setting the
  process stop flag. The regression test failed before the fix: mining never
  received its stop signal while the server waited for the stream. It passes
  after the fix, with live event delivery verified before shutdown and a clean
  end of stream afterwards.
- A second local server fixture holds a request pending indefinitely. Mining
  receives its stop signal before the drain deadline, and the server wait
  returns after the bounded drain. Neither test starts mining or GPU work.
- All 24 control API tests pass, covering authentication, loopback host checks,
  configuration validation, restart coordination and the new shutdown cases.
- Windows GNU miner compilation passes with NVIDIA and AMD enabled.
- Pinned formatting and whitespace checks pass.

The fix is intended for the next miner release. No release tag, collector
deployment or production restart is part of this follow-up.
