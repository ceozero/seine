#!/bin/bash
# Build the miner and the full-size parity checker from the current tree and
# copy both to <out-dir>, with the source state recorded in BUILD_INFO.
# Always rebuilds, so a candidate can never be a stale binary from an earlier edit.
# Usage: scripts/cohort/build_candidate.sh <out-dir>
set -euo pipefail
OUT=$1
cd "$(git rev-parse --show-toplevel)"
cargo +1.93.0 build --release --locked
cargo +1.93.0 build --release --locked -p blocknet-pow-kernel --features cpu-research --example verify_cpu_kernels
mkdir -p "$OUT"
cp target/release/seine target/release/examples/verify_cpu_kernels "$OUT/"
{
  echo "commit $(git rev-parse HEAD)"
  echo "dirty $(git status --porcelain -- src pow-kernel | wc -l) files"
  git diff --stat -- src pow-kernel | tail -1
  sha256sum "$OUT/seine" "$OUT/verify_cpu_kernels"
} > "$OUT/BUILD_INFO"
cat "$OUT/BUILD_INFO"
