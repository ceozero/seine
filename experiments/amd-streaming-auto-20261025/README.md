# Automatic streaming on Ryzen — native validation

Baseline: v0.2.22 (`6e54117`). Candidate production source: `a13502a1a2a76e2825c4ae1e05ee81dc0a086859`.
Owner: architecture session `01a16bd3-6dc7-70f2-a185-b86550c4dbeb`.

The only production change permits the supported streaming kernel in automatic
trials on AMD family 26/model 68. Turin remains eligible. No startup kernel,
worker count, placement, comparison threshold, cache schema or tuner state
machine changes. The candidate-list fingerprint invalidates incompatible old
kernel decisions. Repeated measurements must still select the winner.

Native fixed-kernel evidence lives on `codex/high-end-streaming-20261025` under
`experiments/high-end-streaming-20261025/`. Genoa has a confirmed explicit-kernel
gain, but automatic eligibility remains pending native productive validation.
There is no new AWS rental or budget authorization in this follow-up.

## Native Windows protocol

Build default release features using native MSVC Rust 1.93.0, two compile jobs,
and a separate target directory. Run the native workspace tests. Preserve the
actual source commit, source archive and executable hashes. An initial build
invocation had a mistyped embedded commit; it was stopped before measurements
and restarted with the exact commit read from the source manifest.

The timed runner (`native_run.py`) requires its own running gpuq exclusive job,
checks Gaming Mode, and has a 45-minute controller deadline. It uses ordinary
pages and a kill-on-close Windows Job Object with a 40 GiB aggregate commitment
ceiling. Mining arenas never exceed 32 GiB. Each native benchmark has a separate
180-second deadline; every child is task-owned and stopped in `finally`.
This reservation additionally ends before 2026-10-25 02:24 UTC so the research
session can collect and clean its expiring cloud rentals. Admission requires at
least 35 minutes remaining; a late queue start is rejected before hashing.

1. Four alternating pairs compare streaming at eight spread physical cores and
   sixteen physical cores: 20-second warmup, two 20-second measured rounds.
   Rates include the completion fence. No worker-count default is inferred from
   one pair or a short screening result.
2. Two opposite-order screens compare eight workers spread across CCDs, confined
   to the 96 MiB CCD, and confined to the 32 MiB CCD. These are placement screens,
   not sufficient evidence for a production affinity change.
3. The real native pool runtime connects only to an owned loopback fixture.
   A 540-second cold episode uses automatic tuning with an 8–16 worker safety
   range; a 150-second restart reuses only its own cache. Neither forces a kernel.
4. A separate 300-second cold episode adds two bounded CPU loads from seconds
   45–125. Preserve the complete trajectory, including inconclusive trials.
5. A 75-second restart with a 95% memory reserve checks parked startup without
   allocating pressure buffers or overwriting the saved evidence. This models a
   reduced memory budget; it is not an actual OS memory-pressure experiment.

All episodes end before the 600-second donation grace period. The fixture uses an
impossible target and no wallet with funds. No shared hosts file, firewall,
browser, GPU process or system memory policy is changed.

The first lifecycle attempt was discarded: the fixture incorrectly parsed blank
keepalive lines as JSON and repeatedly disconnected the miner. The completed 14
fixed-kernel reports and full-size parity preceded that failure and remain valid.
The owned reservation was canceled, all children exited, and the initial cold
cache was isolated. `fixture.py` now ignores blank keepalives; `test_fixture.py`
checks that later requests still work on the same connection. The lifecycle-only
resume verifies the frozen binary and each accepted file hash, preserves the first
benchmark protocol/job identity, and starts with a fresh cold cache. No discarded
productive sample is reused as automatic-selection evidence.
Because the completed benchmarks are not repeated, this resume requires 20
minutes of clean time remaining rather than the full run's 35-minute admission
minimum. The same absolute 02:24 UTC release deadline remains enforced.

The clean 540-second natural-count cold run rejected a noisy second streaming
confirmation at 293.5 seconds. Its 300-second retry delay falls outside that cold
window. This is retained as valid safety/convergence evidence, not discarded as
a fixture failure. A separate `daemon_probe.py` uses the same production binary
with a loopback HTTP/SSE daemon fixture, allowing up to 1,020 seconds for a retry
without an external donation-pool connection. Its research count bounds are
8–8 to isolate kernel/cache behavior; it does not prove unconstrained count
convergence. After a confirmed winner, it runs at least 360 seconds total and
another 30 seconds after caching, then checks a 90-second exact-context restart.
It uses a fresh cache and the same hard desktop deadline and memory ceiling.

## Takeover results (2026-10-25, after Codex usage ran out)

Both checks used the same binary (`f7ef9fdc…`) and were launched through the gpuq
Windows runner, which starts processes hidden (`CreateNoWindow`), rather than
`powershell.exe` from WSL. `takeover_daemon.py` resolves its own gpuq job id and
then runs `daemon_probe.py` unchanged. Evidence and SHA-256 lists are in the
ignored `data/amd-streaming-auto-20261025/functional-results/` and `daemon-results/`.

- **Functional restore/park/recovery: passed.** The unmodified load-run cache
  restored `avx512-256-stream` 2.2 s into a warm restart. A 95%-reserve start
  parked at 0 hashes, waiting for RAM, without changing the cache. A recovery
  restart restored streaming at 2.0 s and mined. Codex's 02:10 UTC attempt was
  interrupted before its recovery phase and is kept separately.
- **Long daemon retry probe: failed. No streaming winner in 1,021 s.** Kernel
  trials ran at 2 s (avx2: no gain), 100 s (streaming: reported "no confirmed
  gain"), 496 s (avx2: no gain) and 594 s (streaming: first cycle passed, second
  cycle "confirmation was noisy"). Steady 5-second rates on the busy desktop
  wander between about 6.4 and 7.5 H/s, and the 5% baseline-drift gate tripped.

**Open blocker: the 100 s streaming trial.** Global 5-second stats show about
7.7 H/s before, 10.1 during and 7.6 after the candidate window. That's about +30%
with about 2% drift, which `comparison()` should score as `Gain`. Yet the tuner
logged "no confirmed gain". Two findings:

1. `Tuner::tick` logs "keeping current kernel; no confirmed gain" for every
   first-cycle non-gain, including `Comparison::Inconclusive` (drift above 5%).
   The message cannot distinguish a real loss from a drifted baseline.
2. The tuner logs no A/B/A sample values, so this run cannot show whether its
   windows fell outside the visible streaming interval or whether per-backend
   snapshot hashes undercount the streaming kernel.

Fixed-kernel evidence still shows streaming about 46% faster on this desktop. In
three productive cold runs, automatic selection confirmed it once (the CPU-load
run). Do not promote Ryzen eligibility on this evidence. Next step: log each
trial's three samples and the comparison outcome, fix the message for
`Inconclusive`, then rerun this probe.

### Identity startup path (`aecc267`): passed

Following the user's direction to allow per-architecture behaviour, uncached
contexts with 8 or more workers on this identity now start on streaming. The
other paths are then compared against it, and every decision logs its A/B/A
rates. Native MSVC build of `aecc267` (`fdab54f9…`): build, 528 native tests
(7 ignored) and verifier builds passed. `daemon_probe_startup.py`, the same
probe with the startup assertion replacing "confirmed faster", passed:

- Streaming started 3.2 s into a fresh cold run.
- streaming 10.40 / avx512 7.77 / streaming 10.13 H/s gave "no confirmed gain"
  for avx512. streaming 10.43 / avx2 7.57 / streaming 9.97 H/s gave the same for
  avx2. Streaming was cached after the complete sweep at 197.5 s.
- An exact-context restart restored streaming in 2.1 s.
- The cold run averaged 9.71 H/s over 362 s, against 7.21 H/s over 1,020 s for
  the earlier probe that started on AVX-512. The runs are unpaired, so treat the
  gap as indicative; the A/B/A rates within this run show streaming about 33%
  ahead of AVX-512.

Evidence: ignored `data/amd-streaming-auto-20261025/startup-probe-results/`.

## Integration and handoff

The research session owns PR50 joint tuning in `seine-cpu-followups`; do not alter
its state machine independently. It released the desktop after its builds and
upload completed. Native timings require that hold until an explicit release.
Stop all owned processes, collect/check raw evidence, remove the owned native
temporary tree, release the reservation, and notify research before completion.

Production eligibility is a review candidate until native results are recorded.
Failures and unconfirmed convergence must remain visible; do not replace them
with a forced streaming default or silently reuse older measurements.
