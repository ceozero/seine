# seine v0.2.43 release drift review

Checked October 27, 2026, 9:32 PM EDT. Read-only source and archive inspection; no mining workload or fresh performance benchmark was run.

## Release identity and unchanged contracts

- Official release: https://github.com/zpalmtree/seine/releases/tag/v0.2.43
- Published October 27, 2026, 8:05:29 PM EDT (`2026-10-28T00:05:29Z`).
- Tag commit verified against GitHub: `fe0db458f170951df46c4d46a11cc4565d7a9759`.
- Fee implementation, NVIDIA guide, configuration guide and release workflow are byte-identical to v0.2.42. The flat 2% miner fee and all five platform archive names are unchanged. The pool calculator consumes the fee value, so this identity refresh does not change its generated output.
- Both official Linux archives were downloaded and verified against the release SHA256SUMS.txt and GitHub asset digests. Their internal executable hashes also matched their packaged manifests. `readelf --version-info` reports maximum required GLIBC_2.39 for both architectures. Archive files remain seine, README.md, PRIVACY.md, SEINE-LICENSE.txt and SHA256SUMS.txt.
- Linux ARM64 archive SHA-256: `8c94d9d729b8651be001258783f03e44782f35818f662bafc1f74c1a32c3669f`.
- Linux x86_64 archive SHA-256: `8b8e761f24b7a1d164e5fc6f991ad83199684dc7fcea845b71fc10f113dd2b56`.

### Reproducible Linux artifact evidence

Release checksum manifest: https://github.com/zpalmtree/seine/releases/download/v0.2.43/SHA256SUMS.txt

Downloaded artifacts:

- https://github.com/zpalmtree/seine/releases/download/v0.2.43/seine-linux-aarch64.tar.gz
- https://github.com/zpalmtree/seine/releases/download/v0.2.43/seine-linux-x86_64.tar.gz

For each downloaded tarball, SHA-256 was compared with both the release manifest and the GitHub release asset digest. The extracted executable SHA-256 was also compared with the archive's internal SHA256SUMS.txt. ELF version requirements were inspected with `readelf --version-info` without executing the miner. Both architectures reported a maximum GLIBC requirement of `GLIBC_2.39`.

Observed verification results:

```text
seine-linux-aarch64.tar.gz: archive SHA-256 PASS; internal executable SHA-256 PASS; maximum GLIBC_2.39
seine-linux-x86_64.tar.gz: archive SHA-256 PASS; internal executable SHA-256 PASS; maximum GLIBC_2.39
```

## Actual behavior change and copy correction

Pinned source: https://github.com/zpalmtree/seine/blob/v0.2.43/src/config.rs

`memory_reserve_bytes` now reserves `min(effective_total / 100 * 5, 1 GiB)` when no percentage is explicitly supplied. An explicit percentage still uses `effective_total / 100 * percentage` without the cap. The reserve is deducted from available memory after any GPU reservation. This applies to automatic sizing across platforms; it is not restricted to the Windows benchmark highlighted in the release notes. Integer arithmetic occurs in bytes, so prose percentages are approximate at byte granularity.

Source SHA-256: `f524aec27033b327a6537f27a23b8ba8525662cb8c8d032c558153aeae00684b`.

Updated current guidance in all 20 languages for:

- mine-blocknet-on-servers
- argon2id-proof-of-work-explained
- blocknet-mining-hardware-hashrate
- mine-blocknet-on-mac
- cpu-mining-2026
- mine-crypto-on-old-pc-or-laptop

Existing version-labeled v0.2.26 RAM planning remains historical. The separate 5% extra huge-page provisioning margin is unrelated and unchanged.

The hardware table remains an illustrative memory budget, not a measured thread allocation. Using the existing upper-end 3 GiB system-use assumption and the new 1 GiB cap gives floor((64−3−1)/2)=30 and floor((128−3−1)/2)=62 slots. Its 16/32 GiB estimates remain 6/14. The Mac table is a memory-only upper bound before current usage and CPU limits: floor((48−1)/2)=23 and floor((64−1)/2)=31; smaller rows are unchanged. GB labels remain the original approximate marketed memory sizes; arena and reserve sizes are binary GiB. No new hashrate claim is inferred from these counts.

The release also changes the Linux transparent-huge-page startup path to fault memory during the first hash rather than synchronously prefaulting it. Existing setup instructions remain applicable. Published measured startup and Windows gains are retained in the release notes; this copy correction adds no new performance claims.
