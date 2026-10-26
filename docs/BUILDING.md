# Building from source

Requires [Rust](https://rustup.rs/) (the pinned toolchain in `rust-toolchain.toml`
installs automatically) and GNU Make.

## Make

```bash
# Default build (includes NVIDIA support)
make

# CPU-only build (no CUDA dependency)
make build-cpu

# Host-native CPU build (optimized for your specific CPU)
make build-native

# Run tests
make test

# Package a release zip for the current platform
make release
```

## Cargo

```bash
# Default build (includes NVIDIA support)
cargo build --release

# CPU-only build (no CUDA dependency)
cargo build --release --no-default-features

# Experimental Metal build (macOS ARM)
cargo build --release --no-default-features --features metal

# Host-native CPU build
./scripts/build_cpu_native.sh --cpu-only
```

The binary lands in `target/release/seine`.

The Linux ARM64 release archive is built on Ubuntu 24.04 and needs glibc 2.39 or
newer. On older distributions, build the CPU-only miner from source with
`cargo build --release --locked --no-default-features`.

On x86_64, every build includes the scalar, AVX2 and AVX-512 kernels and selects
one at runtime, so a portable build is already fast. On dedicated miners,
`build-native` can still add a small extra uplift.

## Releases

Tagged releases are built by GitHub Actions for Linux (x86_64, ARM64), macOS
(x86_64, ARM64) and Windows (x86_64). Each archive includes the license, the README
and an internal checksum manifest; the release also publishes a `SHA256SUMS.txt`
covering every archive.

Maintainers: see `scripts/release_tag.sh` and [CHANGELOG.md](../CHANGELOG.md); a
version without a changelog section cannot be tagged.

## Benchmarks

Offline benchmarks run without a daemon or pool:

```bash
./seine --bench --bench-kind backend --backend cpu --threads 1 --bench-secs 20 --bench-rounds 3
```

The paired A/B harness and lab controller are documented in
[benchmarks.md](benchmarks.md).
