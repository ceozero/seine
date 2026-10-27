# Telemetry-led CUDA loader fix — October 27, 2026

## Evidence and attribution

The read-only production briefing at 00:56 EDT reported healthy collection
infrastructure and six installations with unfinished v0.2.38 previous runs in
the last 24 hours. Their causes remain unconfirmed. All reporting v0.2.38
clients still used schema 6; there was no adoption evidence for the unreleased
fixes or schema 7 client instrumentation.

A targeted aggregate query over all current-version events found one Windows
installation reporting an Intel Core i5-10300H with a `rust_panic` during tuning
at `deps/cudarc-0.19.2/src/driver/sys/mod.rs:21540`, last received October 26 at
23:34:14 EDT. The general briefing's top-30 cluster limit omitted this event.
This location is the dependency's unconditional symbol-resolution assertion
for `cuCtxGetId`. Seine does not call that function. Driver version and the
machine's full configuration are not available from this report.

This is a separate issue from the 13 installation IDs reporting the known
missing-library panic on Linux and from the six unfinished-run reports.
Installation IDs do not establish distinct physical machines or people.

## Reproduction and change

`scripts/test_cuda_unused_symbol.py` builds a disposable fake driver that
exports the 28 names preceding `cuCtxGetId` in the old loader but deliberately
omits that symbol. The old dependency reproduced the exact production panic
at line 21540. No real GPU is accessed: all placeholder functions abort if
called, and the one callable entry point, `cuInit`, returns `NO_DEVICE`.

The dependency is updated from cudarc 0.19.2 to 0.19.5, with no other lockfile
package changes. Its [upstream fix](https://github.com/chelsea0x3b/cudarc/pull/573)
resolves symbols when used instead of requiring every exported function during
library initialization. The same reproduction now loads successfully and
receives the expected driver error from `cuInit`, without a panic. CUDA 12.0
bindings and the miner's kernels and tuning defaults remain unchanged.

This removes the observed unused-symbol failure mechanism. It does not prove
that the affected installation can mine with its current driver: required
functions, compilation and kernel compatibility still have to succeed. No
performance or on-device recovery claim is made.

## Validation

- The exact missing-`cuCtxGetId` reproduction fails before the update and passes
  afterward against the compiled Seine test binary.
- Existing isolated missing-driver and missing-NVRTC tests pass, retaining
  typed startup errors and no panic.
- All 34 ordinary NVIDIA tests pass. The two loader probes run separately
  through their harnesses; the existing real-GPU parity test remains ignored.
- Linux NVIDIA/AMD test compilation and Windows GNU NVIDIA/AMD compilation pass.
- Formatting and whitespace checks pass.

The existing collector remains compatible. Unlisted dependency panic locations
from the newer cudarc version normalize to `unknown`, as required by the fixed
privacy allowlist; legacy 0.19.2 source IDs remain useful for current clients.
No telemetry schema change, release tag or production deployment is included.
