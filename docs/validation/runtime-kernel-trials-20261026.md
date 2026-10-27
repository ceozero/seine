# Runtime CPU kernel trial evidence — October 26, 2026

The productive kernel tuner now records its existing A/B/A windows and outcome
through the bounded schema-6 recorder. No candidate selection, tuning threshold,
hash kernel or startup policy changes. Telemetry remains optional and performs
no network or disk work on the tuning thread.

The producer retains positive, negative, drifted and interrupted comparisons.
It records the actual duration/hash alternatives used by the tuner, allocator
page backing, CPU-list slots and current memory/parallelism observations from
the existing sizing poll. Final promotion is reported only after observing the
workers acknowledge it. A partially failed multi-backend switch captures fresh
actual settings rather than claiming the previously observed arm is still active.

The existing tuner clock has whole-second resolution. Switching, settling and
idle costs are unmeasured and remain null. Allowed CPU mask and placement digest
are also unknown: these records support coverage and diagnostics, but do not
qualify for ranked hardware hints. Worker-count and joint trial producers remain
pending. This is not evidence of a performance gain or a completed fleet-driven
default-selection system.

Validation on the pinned Rust 1.93.0 toolchain:

- 113 miner adaptive tests passed, three full-memory tests ignored locally.
- 65 configuration tests passed; ten hardware telemetry recorder tests passed.
- All-target compilation with the AMD feature passed.
- New regressions check identical decisions with telemetry enabled/disabled,
  acknowledgment before promotion, negative/drift outcomes, retained partial
  samples after backend loss, interrupted pending promotions and partial
  multi-backend switch failures.

Tests use synthetic snapshots rather than allocating local 2 GiB hash arenas.
They validate recording behavior, not native hardware performance. Collector
schema-6 validation and delivery are covered by the separate telemetry work.
Deploy the compatible collector before releasing miners with these hooks.

The existing paired-trial collector showcase uses synthetic reports and remains
a collector demonstration; it is not proof of native runtime emission. No UI
changes are introduced by this runtime integration.
