# Reliability context, October 27, 2026

Implemented after the request to add stop origins, cleanup progress and CUDA
software versions. This extends observability; it does not establish the cause of
the historical unclean-run alert. No fresh production telemetry was queried for
this change, and no collector deployment or miner release was performed.

## Collected context

Schema 8 adds current-run and previous-run cleanup stages and loaded NVIDIA
software versions. Existing OS stop reasons remain; API stop/restart and TUI
quit/thread-count restart have separate fixed codes. A session-owned origin keeps
a stop that arrives before telemetry startup and prevents a replacement session
from inheriting it. Internal server teardown leaves unknown origin unknown.

Cleanup markers identify the last **entered** step: backend quiescing, event drain,
network workers, TUI teardown, autotune stop, backend stop, tip listener and telemetry
finalization. Transitions save the bounded checkpoint directly, even during a
blocked upload. Weak store ownership preserves opt-out and lock release; completed
stores reject later checkpoints. This is best-effort disk persistence, not a
power-loss guarantee or a trace of every instruction/native call.

Routine final stop context can be reported but cannot replace an older pending
report. The usual upload admission limits remain. Reporting installations are not
clean-exit counts, and an unfinished marker is not proof of a crash.

`driver_cuda_version` is the loaded driver's CUDA compatibility level from
[`cuDriverGetVersion`](https://docs.nvidia.com/cuda/archive/12.8.0/cuda-driver-api/group__CUDA__VERSION.html),
not an NVIDIA display-driver release such as 580.xx. `nvrtc_version` comes from
the loaded compiler's `nvrtcVersion`. Both use major * 1000 + minor * 10. Seine
uses the driver API and NVRTC, not cudart, so no CUDA Runtime version is invented.
Version queries resolve optional symbols from the mining libraries; missing
symbols, errors and invalid values leave metadata absent without adding a panic.
No GPU context, NVML initialization, nvidia-smi process or polling was added.
The fixed source allowlist also includes the linked cudarc 0.19.5 dependency.

## Validation

Validation completed locally October 27, 2026, EDT, using Rust 1.93.0:

- 11 diagnostics tests: recovered-run persistence, bounded context, early stop
  requests, first-request retention and session isolation.
- 17 telemetry-worker tests: transitions persisted during blocked HTTP, clean-stop
  report spooling, pending-report preservation, marker clearing and opt-out.
- 25 control-API tests, including API-origin versus internal-teardown attribution,
  SSE shutdown and stalled-client drain.
- 17 TUI tests and 55 miner orchestration/startup tests.
- 34 ordinary NVIDIA tests; no GPU kernel/parity/throughput work performed.
- Four isolated fake-library version-query cases (present, absent symbol, API error,
  invalid version), plus existing missing-driver, missing-NVRTC and unused-symbol
  loader regressions. Cached metadata populates replacement sessions too.
- 13 schema/tuning library tests and the collector's admission test.
- 11 disposable PostgreSQL diagnostic/alert SQL tests, including separation of
  loaded versions and previous-run cleanup progress; alert thresholds unchanged.
- Real disposable collector/PostgreSQL HTTP integration: legacy uploads, schema-8
  acceptance and stored context, downgrade and private-field rejection all pass.
- Windows GNU NVIDIA+AMD compile check and Linux CPU-only compile check pass.
- Changed-file pinned formatting and `git diff --check` pass.

Representative reproduction commands (from the repository root):

```sh
cargo +1.93.0 test --locked -p seine --bin seine --features amd diagnostics::tests -- --test-threads=1
cargo +1.93.0 test --locked -p seine --bin seine --features amd hardware_telemetry::tests -- --test-threads=1
cargo +1.93.0 test --locked -p seine --bin seine --features amd control_api::tests -- --test-threads=1
cargo +1.93.0 test --locked -p seine-telemetry --features server
python3 scripts/test_cuda_versions.py /path/to/compiled/seine-test-binary
python3 scripts/test_cuda_missing_library.py /path/to/compiled/seine-test-binary
python3 scripts/test_cuda_unused_symbol.py /path/to/compiled/seine-test-binary
(cd telemetry && python3 -m unittest test_diagnostics_sql test_alerts_sql)
```

HTTP integration uses `telemetry/test_integration.py` against a disposable database
and collector as described in `telemetry/README.md`, never production. Test services
and fake-library directories were removed after validation.

## Rollout

Deploy a schema-8 collector before releasing miners that emit schema 8. A schema-7
collector rejects those reports. There is no SQL migration. Existing schemas remain
accepted; absent context stays unknown. Windows runtime queries were compile-checked;
fleet adoption and on-machine version values still require release validation.
