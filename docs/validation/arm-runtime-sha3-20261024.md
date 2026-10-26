# Native ARM runtime SHA3 validation

The final frozen generic AArch64 candidate `f20e7bb` passed corrected native
Graviton2 and Graviton3 confirmation. Graviton4 passed longer kernel confirmation,
combined-build regression and the final x86-boundary-change check. The PR remains
draft because final-build Xeon 6975P-C confirmation retains an unresolved negative throughput signal.

Baseline: v0.2.21 (`359265e`). Current PoW: 2 GiB Argon2id, one iteration,
one lane. Rates count completed hashes and include round-end fence time. These
are measured configurations, not promised gains. Final control and candidate
binaries use Rust 1.93.0, CPU-only release builds and generic AArch64 compilation
without global `+sha3`.

## Corrected native performance confirmation

Every row below uses four pairs whose actual per-worker variant order reverses
on each pass. Large-page runs use two 30-second measured rounds after warmup;
regular-page runs use two 20-second rounds after warmup.

| Hardware / backing | Workers | Baseline H/s | Candidate H/s | Paired gain range |
| --- | ---: | ---: | ---: | ---: |
| Graviton2 / N1, HugeTLB, portable NEON fallback | 1 | 0.680 | 0.707 | +3.81% to +3.95% |
| Same | 16 | 10.609 | 11.047 | +3.83% to +4.55% |
| Graviton3 / V1, HugeTLB, SHA3 + 64-byte prefetch | 1 | 0.824 | 1.230 | +49.17% to +49.42% |
| Same | 16 | 12.520 | 18.170 | +44.31% to +45.91% |
| Graviton3 / V1, regular pages | 1 | 0.762 | 1.038 | +35.52% to +36.72% |
| Same | 8 | 5.892 | 7.807 | +32.23% to +32.86% |
| Graviton4 / V2, HugeTLB, kernel candidate `3122893` | 1 | 0.891 | 1.373 | +53.94% to +54.33% |
| Same | 16 | 13.800 | 21.503 | +55.11% to +57.00% |

Graviton2/3 use the final `f20e7bb` executable. The Graviton4 long series uses the
earlier kernel candidate explicitly named above. Two subsequent balanced pairs
of the combined `636e688` build versus baseline retained +54.61% to +54.63% at
one worker and +54.91% to +55.50% at sixteen. The final x86-only boundary change
was near-flat against that combined build: +0.003% to +0.072% / −0.712% to +0.142%.
No performance gain is attributed to that boundary change on ARM.

Graviton2 does not expose SHA3. Its improvement is in the portable NEON fallback,
not execution of unsupported instructions. A separate prefetch-only screen did
not justify an additional kernel identity.

Final Graviton2 archive SHA256:
`1e121ec86658eda068cc02f00abe4205f8e897a64be5f0182fe7cc1cb6a6bb8c`.
Final Graviton3 large/regular archive SHA256:
`935799f8c78b0507ea8f68480ca98fbf7007809db5c6a26dd32123c2d99ae6c6`.
Every archived file was checked against its manifest before rental termination.

## Correctness, automatic behavior and resource limits

Native full-size reference parity passed for nonces 0, 12345 and u64::MAX,
including dirty arena reuse and NEON/SHA3 dispatch changes on supported CPUs.
Graviton2 rejects unsupported SHA3 construction/selection while retaining NEON.
Small arena tests cover segment boundaries and guards; real full-arena worker
switches also passed. Native kernel tests and strict kernel-crate Clippy passed.

Startup remains productive on portable NEON. Runtime feature detection admits
SHA3 as a challenger; repeated productive-work confirmation is required before
promotion and caching. An earlier native Graviton3 pool run confirmed automatic
SHA3 selection and worker growth. Its constrained-restart failure was retained,
then repaired by prerequisite PR #43. Complete repaired resource lifecycles
passed on ARM and x86, including CPU load, memory pressure, zero-worker parking,
restart growth to three actual resident arenas (about 6.028 GiB), and opt-out.
The final PID-safe combined lifecycle passed on Graviton4 and Xeon 6975P-C.

`--disable-cpu-autotune-threads` disables count and kernel tuning. Explicit fixed
counts keep the startup ISA unless tuning is explicitly enabled. Experimental
AVX-512/256 remains outside automatic candidates.

The separate combined integration branch passed 497 workspace tests (five
resource-dependent tests ignored), all-feature/all-target Linux compilation,
Windows GNU test cross-compilation, scoped formatting and strict kernel Clippy.
Strict repository-wide Clippy still reports existing diagnostics. Cross-compiling
for Windows or `aarch64-apple-darwin` is not native execution; Apple candidate
performance remains untested, and no Apple cache-line policy change is made.

## x86 isolation and residual differences

The combined `636e688` build exposed a Cascade Lake regression. Four balanced
pairs at twelve workers measured 9.303 H/s for the matching CPU-only baseline
and 9.036 for `636e688` (−2.60% to −3.34%). The ARM wrapper refactor also caused
x86 fill loops to inline into a larger dispatch function.

The x86-only no-inline boundary in `f20e7bb` restores the baseline's normalized
dispatch/fill instruction sequences. This is not whole-program equivalence.
Four native pairs measured 9.267 H/s, with baseline-relative differences −0.93%
to +0.004% (mean about −0.39%), consistently ahead of the regressed build.
Full-size native reference parity passed. Both the original regression and
residual small negative remain disclosed. Archive SHA256:
`22d2258d66fd292aaf998b86b753800bc0bc091b5eb450c1a39e4a7a545e0fdb`.

Fresh Xeon 6975P-C final-build checks at twelve workers retain a negative signal.
Two short full AVX-512 pairs were −0.271% and −1.274%. Four longer, actually
alternating pairs measured 12.486 → 12.324 H/s (−1.304% ratio of means), with
paired differences −0.063%, −0.071%, −3.719% and −1.480%. Independent audit
verified all reports, both archives, identities, full-size parity, page backing
and zero allocation/control errors, swap or OOM. Throughput drift on both sides
limits causal interpretation and stable effect-size claims. The combined-stack
comparison does not isolate the causal change to this PR, but normalized x86
instruction equivalence has not established performance equivalence. **Keep this
PR draft until that signal is understood.** Positive results elsewhere do not
remove this gate.

Fresh final Sapphire Rapids checks passed full-size parity. At one/twelve
workers, AVX2 paired differences were +0.116% to +0.129% / +0.471% to +0.700%;
full AVX-512 was +0.202% to +0.286% / −0.783% to +0.154%. These small or mixed
differences do not remove the separate Xeon 6975P-C integration gate.

Haswell, Zen 1 and Zen 2 final AVX2 checks were near-flat. Earlier Ice Lake
ARM-change checks were order-limited and retain small negatives. Fresh final
Ice Lake comparisons now completed with negative differences in all eight
pairs: one/twelve-worker AVX2 −2.640% to −1.691% / −1.721% to −0.920%, and
full AVX-512 −0.782% to −0.413% / −1.334% to −1.280%. Independent order, binary,
archive and full-size parity audit passed. This reinforces the combined-stack
regression gate. Following the user's merge instruction, PRs #40/#41/#43/#45
are being confirmed separately before runtime changes are merged; #44 stays draft.

## Review and retained limitations

Independent review covered runtime guards, target-feature boundaries, fallback,
prefetch bounds/non-aliasing, supported cache choices and automatic candidate
limits. No blocking source issue remained. Runtime source matches frozen
`f20e7bb`; documentation and commit history differ.

Earlier ARM matrices had an order-reversal bug. Their original data remains
labelled order-limited; the corrected confirmations above replace that evidence
for acceptance. Some older controllers also inherited an overridable Git label
into both executables. Raw labels are preserved, while actual binary SHA256,
compiled source fingerprints and source archives establish the build identities.

The [architecture evidence PR](https://github.com/zpalmtree/seine/pull/42) retains
normalized rounds, actual order, binary/source mappings, failures, exclusions and
archive digests. This ARM candidate remains unmerged; PRs #40/#45 were merged separately and no release was published.
