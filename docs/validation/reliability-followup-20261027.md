# Reliability follow-up — October 27, 2026

## Production evidence

Read-only briefing at 00:09 EDT found healthy collector HTTPS, PostgreSQL,
retention, disk and backups. The v0.2.38 unfinished-run population had grown
from four to five installations, all reporting Windows and build `e4f05927df3f`.
The new Xeon E3-1231 v3 checkpoint was at 220 seconds, with CPU page warnings
and a failed NVIDIA initialization/tuning attempt. CPU hashes appeared after
restart. The other checkpoint uptimes remain 25, 87, 100 and 1106 seconds.
The Xeon E5-2673 v4 still had no newer report at the follow-up query; absence
does not establish whether it stopped, lost connectivity or opted out.

The separate Linux CUDA loader reports point to cudarc 0.19.2's missing-library
panic path. They contain CPU hashes despite the failed NVIDIA initialization.
Installation IDs are not proof of distinct people or physical machines.

## Confirmed defects and changes

- The previous Windows `ctrlc` handler returns immediately after waking its
  helper thread. Windows ends a console process when its close handler returns,
  so the normal cleanup thread can lose that race. The replacement handler sets
  the shared shutdown flag and waits for completion for up to four seconds of
  elapsed time, below the usual five-second close deadline. It performs no
  allocation, locking, logging or disk/network IO. A second interrupt still
  forces exit 130. Windows can impose shorter deadlines for other OS events.
- An already completed mining run left its marker present while the reporting
  worker waited for final HTTP delivery. The marker now clears before that wait;
  pending evidence remains bounded and recoverable. Final shutdown does not
  first retry an older pending upload.
- Missing driver or NVRTC libraries previously reached cudarc's panic accessor.
  The backend now probes the dependency's own library search before tuning or
  context creation and returns a typed startup error. CPU mining can continue.
  This handles unavailable libraries; incompatible exported symbols can still
  be genuine dependency panics and are not suppressed.
- Automatic Windows large-page fallback now records its numeric OS error and
  requested bytes at the source, while retaining the ordinary-page fallback.

[Microsoft's console handler contract](https://learn.microsoft.com/en-us/windows/console/handlerroutine)
documents termination on handler return and the applicable timeouts. These
reproductions establish defects, not the historical termination cause of each
reporting installation. No kernel or tuning policy was changed.

## New telemetry and limits

Schema 7 adds fixed `interrupt`, `console_close`, `logoff` and `system_shutdown`
request codes to previous-run checkpoints and fixed NVIDIA-driver/NVRTC-unavailable
failure reasons. Schema 1–6 reports remain accepted. New fields/reasons cannot
masquerade as schema 6. Raw signal input, library paths and error contents remain
excluded. Privacy disclosure was updated.

Ordinary checkpoint writes remain five seconds apart. The reporting worker
checks once a second for a newly observed shutdown request and checkpoints it
without IO in the OS callback. Ongoing disk/network work, a native crash, a forced
kill or an OS deadline may prevent that save. A request does not establish
successful cleanup, and no request does not establish a crash. Unfinished runs
with requests remain in the existing alert threshold and are separated in the
aggregate briefing. Older clients have unknown request context.

## Verification

- Native Windows probe uses the production shutdown module, creates its own
  hidden console and posts `WM_CLOSE` only to that console. All disposable
  processes and consoles are closed by the bounded harness.

  | Scenario | Result | Observed elapsed time |
  | --- | --- | --- |
  | Old handler | Windows terminated before cleanup; unfinished marker remained | 959 ms |
  | New handler | Cleanup completed, marker removed, exit 0 | 412 ms |
  | Stuck cleanup | Close request observed; bounded forced termination, marker retained | 4157 ms |
  | Interrupt | Cleanup completed, exit 0 | 415 ms |
  | Second interrupt | Forced exit 130, marker retained | 260 ms |

  Reproduce with `cargo +1.93.0 build --example console_shutdown_probe --target
  x86_64-pc-windows-gnu`, then on Windows run
  `powershell -File scripts/test_console_shutdown.ps1 -Probe <probe.exe>`.
  The probe starts no miner and uses no GPU.
- Real Linux cudarc loader tests hide the driver or NVRTC using a disposable
  `dlopen` shim. Both return one precise backend error and no panic. Reproduce
  with `python3 scripts/test_cuda_missing_library.py <seine-test-binary>`.
  Library loading is tested; no GPU kernels are launched.
- Ten diagnostics tests, twelve reporting-worker tests, twelve schema tests,
  the typed loader test and five disposable PostgreSQL grouping tests passed.
  The slow final HTTP test checks that the run marker is gone before the server
  responds. Recovery preserves the shutdown request across an interrupted run.
- Disposable collector HTTP/PostgreSQL integration passes schema 1–7 acceptance,
  persistence, throttling, privacy rejection, downgrade rejection and analysis.
- Linux workspace/all-target checks passed with NVIDIA, AMD and collector server
  features; CPU-only miner and Windows NVIDIA/AMD miner checks also passed.

## Rollout

Deploy the schema-7 collector before a miner release containing these changes.
The approved collector-only update completed at 00:25 EDT; see its
[deployment receipt](collector-schema7-deployment-20261027.md).
There is no database migration or pool, daemon or Stratum change. Existing miner
binaries cannot send the new evidence; a later miner release and adoption are
required. No historical crash cause can be reconstructed from these new fields.
