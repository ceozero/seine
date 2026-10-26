# README hardware benchmarks, 2026-10-25

Whole-VM CPU hashrates for the README, one AWS us-east-1 instance size per CPU
generation (all 32 vCPU) so the bars are comparable. Miner under test:
**seine v0.2.22** (`6e5411768d5d`, release assets checksum-verified with
`gh release download`), CPU backend only, current PoW (Argon2id v1.3, 2 GiB, one
pass, one lane per hash). On Graviton, the upcoming runtime-guarded SHA3+prefetch
NEON kernel from draft PR #44 (`f20e7bb`) is measured alongside the release NEON.

All leases were on-demand (spot was unavailable to this account), one 32-vCPU
instance at a time, us-east-1, 2026-10-25 02:29-14:00 UTC: 17 host runs, 404 benchmark
invocations, **0 rejected**, conservative total cost **$14.72**. Raw evidence is in the
ignored `data/readme-hardware-20261025/`; `summary.json` is the machine-readable result.

<!-- RESULTS -->
## Results

Completed H/s (completed hashes / elapsed incl. round-end fence), mean of the best cell's accepted invocations (2 grid + 2 confirmation). "Threads" = `--threads`. Whole 32-vCPU VM per row.

### Best measured configuration per CPU generation (marketing numbers)

| Generation | Instance | CPU (guest-reported) | Physical cores | SMT | Best kernel | Threads | H/s (n) | Best with published v0.2.22 binary | On-demand $/h | H/s per $/h |
| --- | --- | --- | ---: | --- | --- | ---: | ---: | --- | ---: | ---: |
| Zen 1 Naples | m5a.8xlarge | AMD EPYC 7571 | 16 | 2-way | `avx2` | 16 | 9.38 (4) | same | 1.3760 | 6.82 |
| Zen 2 Rome | c5a.8xlarge | AMD EPYC 7R32 | 16 | 2-way | `avx2` | 16 | 10.96 (4) | same | 1.2320 | 8.90 |
| Zen 3 Milan | c6a.8xlarge | AMD EPYC 7R13 Processor | 16 | 2-way | `avx2` | 16 | 11.63 (4) | same | 1.2240 | 9.50 |
| Zen 4 Genoa | m7a.8xlarge | AMD EPYC 9R14 | 32 | no | `avx512-256-stream` | 32 | 38.18 (4) | same | 1.8547 | 20.58 |
| Zen 5 Turin | m8a.8xlarge | AMD EPYC 9R45 | 32 | no | `avx512-256-stream` | 32 | 49.39 (4) | same | 1.9475 | 25.36 |
| Broadwell | r4.8xlarge | Intel(R) Xeon(R) CPU E5-2686 v4 @ 2.30GHz | 16 | 2-way | `avx2` | 32 | 12.95 (4) | same | 2.1280 | 6.09 |
| Skylake | m5.8xlarge | Intel(R) Xeon(R) Platinum 8175M CPU @ 2.50GHz | 16 | 2-way | `avx512-256-stream` | 32 | 15.64 (4) | same | 1.5360 | 10.18 |
| Cascade Lake | m5n.8xlarge | Intel(R) Xeon(R) Platinum 8259CL CPU @ 2.50GHz | 16 | 2-way | `avx512-256-stream` | 24 | 15.68 (4) | same | 1.9040 | 8.24 |
| Ice Lake | m6i.8xlarge | Intel(R) Xeon(R) Platinum 8375C CPU @ 2.90GHz | 16 | 2-way | `avx512-256-stream` | 32 | 24.32 (4) | same | 1.5360 | 15.83 |
| Sapphire Rapids | m7i.8xlarge | Intel(R) Xeon(R) Platinum 8488C | 16 | 2-way | `avx512-256-stream` | 32 | 26.00 (4) | same | 1.6128 | 16.12 |
| Granite Rapids | m8i.8xlarge | Intel(R) Xeon(R) 6975P-C | 16 | 2-way | `avx512-256-stream` | 32 | 24.42 (4) | same | 1.6934 | 14.42 |
| Graviton2 | m6g.8xlarge | Neoverse-N1 | 32 | no | `neon` (PR #44 `f20e7bb`, unreleased) | 30 | 18.63 (4) | `neon` t32: 18.37 (n=2) | 1.2320 | 15.12 |
| Graviton3 | m7g.8xlarge | Neoverse-V1 | 32 | no | `neon-sha3` (PR #44 `f20e7bb`, unreleased) | 32 | 27.70 (4) | `neon` t32: 21.82 (n=4) | 1.3056 | 21.22 |
| Graviton4 | m8g.8xlarge | Neoverse-V2 | 32 | no | `neon-sha3` (PR #44 `f20e7bb`, unreleased) | 32 | 39.29 (4) | `neon` t32: 26.29 (n=4) | 1.4362 | 27.36 |

### Every host run

| Host | Instance | CPU identity | RAM GiB | NUMA nodes / L3 | Threads swept | Best (variant, threads) | H/s (n, stdev) | Runner-up confirmed | Rejected runs |
| --- | --- | --- | ---: | --- | --- | --- | ---: | --- | ---: |
| Zen 1 Naples | m5a.8xlarge | AMD EPYC 7571<br>AuthenticAMD fam 23 model 1 step 2 | 123.8 | 2 / 4x8192K | 16, 20, 24, 32 | `v022-avx2` t16 | 9.38 (n=4, 0.009) | `v022-avx2` t24: 9.31 | 0 |
| Zen 2 Rome | c5a.8xlarge | AMD EPYC 7R32<br>AuthenticAMD fam 23 model 49 step 0 | 62.1 | 1 / 4x16384K | 16, 20, 24, 26 | `v022-avx2` t16 | 10.96 (n=4, 0.020) | `v022-avx2` t20: 10.82 | 0 |
| Zen 3 Milan | c6a.8xlarge | AMD EPYC 7R13 Processor<br>AuthenticAMD fam 25 model 1 step 1 | 61.5 | 2 / 2x32768K | 16, 24, 26 | `v022-avx2` t16 | 11.63 (n=4, 0.020) | `v022-avx2` t24: 10.62 | 0 |
| Zen 4 Genoa | m7a.8xlarge | AMD EPYC 9R14<br>AuthenticAMD fam 25 model 17 step 1 | 123.1 | 1 / 4x32768K | 16, 24, 30, 32 | `v022-avx512-256-stream` t32 | 38.18 (n=4, 0.037) | `v022-avx2` t32: 28.77 | 0 |
| Zen 5 Turin | m8a.8xlarge | AMD EPYC 9R45<br>AuthenticAMD fam 26 model 2 step 1 | 123.5 | 1 / 4x32768K | 16, 24, 30, 32 | `v022-avx512-256-stream` t32 | 49.39 (n=4, 0.008) | `v022-avx2` t32: 37.72 | 0 |
| Broadwell | r4.8xlarge | Intel(R) Xeon(R) CPU E5-2686 v4 @ 2.30GHz<br>GenuineIntel fam 6 model 79 step 1 | 239.8 | 1 / 1x46080K | 16, 20, 24, 32 | `v022-avx2` t32 | 12.95 (n=4, 0.007) | `v022-avx2` t24: 12.49 | 0 |
| Skylake | m5.8xlarge | Intel(R) Xeon(R) Platinum 8175M CPU @ 2.50GHz<br>GenuineIntel fam 6 model 85 step 4 | 123.1 | 1 / 1x33792K | 16, 20, 24, 32 | `v022-avx512-256-stream` t32 | 15.64 (n=4, 0.040) | `v022-avx2` t32: 12.51 | 0 |
| Cascade Lake | m5n.8xlarge | Intel(R) Xeon(R) Platinum 8259CL CPU @ 2.50GHz<br>GenuineIntel fam 6 model 85 step 7 | 124.4 | 1 / 1x36608K | 16, 20, 24, 32 | `v022-avx512-256-stream` t24 | 15.68 (n=4, 0.031) | `v022-avx512` t24: 12.45 | 0 |
| Ice Lake | c6i.8xlarge | Intel(R) Xeon(R) Platinum 8375C CPU @ 2.90GHz<br>GenuineIntel fam 6 model 106 step 6 | 61.8 | 1 / 1x55296K | 16, 20, 24, 26 | `v022-avx512-256-stream` t26 | 22.48 (n=4, 0.071) | `v022-avx2` t26: 17.82 | 0 |
| Ice Lake (m6i) | m6i.8xlarge | Intel(R) Xeon(R) Platinum 8375C CPU @ 2.90GHz<br>GenuineIntel fam 6 model 106 step 6 | 123.8 | 1 / 1x55296K | 16, 20, 24, 32 | `v022-avx512-256-stream` t32 | 24.32 (n=4, 0.029) | `v022-avx2` t32: 19.10 | 0 |
| Sapphire Rapids | c7i.8xlarge | Intel(R) Xeon(R) Platinum 8488C<br>GenuineIntel fam 6 model 143 step 8 | 61.8 | 1 / 1x107520K | 16, 20, 24, 26 | `v022-avx512-256-stream` t26 | 22.09 (n=4, 0.093) | `v022-avx512` t26: 20.01 | 0 |
| Sapphire Rapids (m7i) | m7i.8xlarge | Intel(R) Xeon(R) Platinum 8488C<br>GenuineIntel fam 6 model 143 step 8 | 123.8 | 1 / 1x107520K | 16, 20, 24, 32 | `v022-avx512-256-stream` t32 | 26.00 (n=4, 0.034) | `v022-avx512` t32: 23.93 | 0 |
| Granite Rapids | c8i.8xlarge | Intel(R) Xeon(R) 6975P-C<br>GenuineIntel fam 6 model 173 step 1 | 61.8 | 1 / 1x491520K | 16, 20, 24, 26 | `v022-avx512-256-stream` t26 | 21.64 (n=4, 0.062) | `v022-avx512` t26: 19.23 | 0 |
| Granite Rapids (m8i) | m8i.8xlarge | Intel(R) Xeon(R) 6975P-C<br>GenuineIntel fam 6 model 173 step 1 | 123.8 | 1 / 1x491520K | 16, 20, 24, 32 | `v022-avx512-256-stream` t32 | 24.42 (n=4, 0.163) | `v022-avx2` t32: 21.75 | 0 |
| Graviton2 | m6g.8xlarge | Neoverse-N1<br>MIDR part 0xd0c r0x3p1 | 123.0 | 1 / 1x32768K | 16, 24, 30, 32 | `f20-neon` t30 | 18.63 (n=4, 0.171) | `v022-neon` t30: 17.88 | 0 |
| Graviton3 | m7g.8xlarge | Neoverse-V1<br>MIDR part 0xd40 r0x1p1 | 123.5 | 1 / 1x32768K | 16, 24, 30, 32 | `f20-neon-sha3` t32 | 27.70 (n=4, 0.029) | `v022-neon` t32: 21.82 | 0 |
| Graviton4 | m8g.8xlarge | Neoverse-V2<br>MIDR part 0xd4f r0x0p1 | 123.5 | 1 / 1x36864K | 16, 24, 30, 32 | `f20-neon-sha3` t32 | 39.29 (n=4, 0.060) | `v022-neon` t32: 26.29 | 0 |

### Full grids (H/s per grid pass, opposite order; mean)

| Host | Kernel (binary) | Results by threads |
| --- | --- | --- |
| Zen 1 Naples | `avx2` (v0.2.22) | t16: 9.37/9.39 (9.38); t20: 9.27/9.27 (9.27); t24: 9.31/9.31 (9.31); t32: 9.17/9.18 (9.18) |
| Zen 2 Rome | `avx2` (v0.2.22) | t16: 10.95/10.98 (10.97); t20: 10.83/10.81 (10.82); t24: 10.61/10.62 (10.61); t26: 10.49/10.51 (10.50) |
| Zen 3 Milan | `avx2` (v0.2.22) | t16: 11.64/11.61 (11.62); t24: 10.63/10.62 (10.63); t26: 10.40/10.40 (10.40) |
| Zen 4 Genoa | `avx2` (v0.2.22) | t16: 25.64/25.68 (25.66); t24: 28.63/28.57 (28.60); t30: 28.66/28.74 (28.70); t32: 28.83/28.75 (28.79) |
| Zen 4 Genoa | `avx512` (v0.2.22) | t16: 25.31/25.29 (25.30); t24: 27.91/27.92 (27.91); t30: 27.98/27.98 (27.98); t32: 28.03/27.98 (28.01) |
| Zen 4 Genoa | `avx512-256-stream` (v0.2.22) | t16: 29.07/29.07 (29.07); t24: 36.30/36.33 (36.32); t30: 37.95/37.99 (37.97); t32: 38.15/38.14 (38.15) |
| Zen 5 Turin | `avx2` (v0.2.22) | t16: 33.08/32.83 (32.95); t24: 36.74/36.78 (36.76); t30: 37.72/37.67 (37.70); t32: 37.68/37.73 (37.71) |
| Zen 5 Turin | `avx512` (v0.2.22) | t16: 32.72/32.67 (32.70); t24: 36.12/36.19 (36.16); t30: 37.38/37.37 (37.38); t32: 37.62/37.62 (37.62) |
| Zen 5 Turin | `avx512-256-stream` (v0.2.22) | t16: 37.77/37.75 (37.76); t24: 46.06/46.10 (46.08); t30: 48.59/48.57 (48.58); t32: 49.40/49.38 (49.39) |
| Broadwell | `avx2` (v0.2.22) | t16: 12.03/12.04 (12.03); t20: 12.38/12.37 (12.38); t24: 12.48/12.53 (12.50); t32: 12.96/12.95 (12.96) |
| Skylake | `avx2` (v0.2.22) | t16: 11.64/11.53 (11.58); t20: 12.04/11.89 (11.96); t24: 12.25/12.27 (12.26); t32: 12.63/12.59 (12.61) |
| Skylake | `avx512` (v0.2.22) | t16: 12.16/12.10 (12.13); t20: 12.29/12.17 (12.23); t24: 12.27/12.28 (12.28); t32: 12.42/12.43 (12.43) |
| Skylake | `avx512-256-stream` (v0.2.22) | t16: 14.89/14.92 (14.90); t20: 14.72/14.94 (14.83); t24: 15.40/15.35 (15.37); t32: 15.64/15.70 (15.67) |
| Cascade Lake | `avx2` (v0.2.22) | t16: 11.92/11.75 (11.84); t20: 12.19/12.12 (12.16); t24: 12.43/12.36 (12.40); t32: 12.78/12.82 (12.80) |
| Cascade Lake | `avx512` (v0.2.22) | t16: 12.25/12.21 (12.23); t20: 12.43/12.35 (12.39); t24: 12.55/12.43 (12.49); t32: 12.48/12.59 (12.54) |
| Cascade Lake | `avx512-256-stream` (v0.2.22) | t16: 14.89/14.91 (14.90); t20: 15.05/15.31 (15.18); t24: 15.73/15.67 (15.70); t32: 15.83/15.46 (15.65) |
| Ice Lake | `avx2` (v0.2.22) | t16: 16.34/16.28 (16.31); t20: 16.82/16.88 (16.85); t24: 17.61/17.60 (17.61); t26: 17.85/17.77 (17.81) |
| Ice Lake | `avx512` (v0.2.22) | t16: 17.24/17.26 (17.25); t20: 17.40/17.37 (17.39); t24: 17.46/17.43 (17.45); t26: 17.44/17.43 (17.43) |
| Ice Lake | `avx512-256-stream` (v0.2.22) | t16: 20.13/20.11 (20.12); t20: 20.84/21.05 (20.94); t24: 22.18/22.19 (22.19); t26: 22.50/22.54 (22.52) |
| Ice Lake (m6i) | `avx2` (v0.2.22) | t16: 16.86/16.81 (16.83); t20: 17.37/17.34 (17.36); t24: 17.95/17.96 (17.95); t32: 19.12/19.12 (19.12) |
| Ice Lake (m6i) | `avx512` (v0.2.22) | t16: 17.77/17.75 (17.76); t20: 17.84/17.51 (17.67); t24: 17.76/17.77 (17.77); t32: 18.05/18.04 (18.04) |
| Ice Lake (m6i) | `avx512-256-stream` (v0.2.22) | t16: 20.15/20.16 (20.15); t20: 20.97/20.98 (20.98); t24: 22.34/22.35 (22.34); t32: 24.31/24.36 (24.33) |
| Sapphire Rapids | `avx2` (v0.2.22) | t16: 17.86/17.79 (17.82); t20: 18.59/18.73 (18.66); t24: 19.32/19.37 (19.35); t26: 19.65/19.48 (19.57) |
| Sapphire Rapids | `avx512` (v0.2.22) | t16: 18.01/18.01 (18.01); t20: 18.52/18.64 (18.58); t24: 19.69/19.56 (19.62); t26: 20.03/20.06 (20.05) |
| Sapphire Rapids | `avx512-256-stream` (v0.2.22) | t16: 19.54/19.57 (19.56); t20: 20.44/20.38 (20.41); t24: 21.76/21.74 (21.75); t26: 22.17/22.04 (22.10) |
| Sapphire Rapids (m7i) | `avx2` (v0.2.22) | t16: 19.53/19.76 (19.64); t20: 20.83/20.95 (20.89); t24: 21.72/21.77 (21.75); t32: 23.50/23.14 (23.32) |
| Sapphire Rapids (m7i) | `avx512` (v0.2.22) | t16: 20.43/20.45 (20.44); t20: 21.28/21.16 (21.22); t24: 22.31/22.32 (22.31); t32: 23.93/23.92 (23.93) |
| Sapphire Rapids (m7i) | `avx512-256-stream` (v0.2.22) | t16: 21.59/21.65 (21.62); t20: 22.50/22.55 (22.53); t24: 23.65/23.61 (23.63); t32: 25.95/26.02 (25.98) |
| Granite Rapids | `avx2` (v0.2.22) | t16: 16.48/16.63 (16.56); t20: 17.68/17.68 (17.68); t24: 18.57/18.73 (18.65); t26: 19.23/18.96 (19.09) |
| Granite Rapids | `avx512` (v0.2.22) | t16: 16.86/16.86 (16.86); t20: 17.95/17.97 (17.96); t24: 18.63/19.09 (18.86); t26: 19.25/19.22 (19.24) |
| Granite Rapids | `avx512-256-stream` (v0.2.22) | t16: 18.44/18.42 (18.43); t20: 19.60/19.56 (19.58); t24: 20.87/20.89 (20.88); t26: 21.67/21.69 (21.68) |
| Granite Rapids (m8i) | `avx2` (v0.2.22) | t16: 17.54/17.03 (17.28); t20: 18.61/18.51 (18.56); t24: 19.60/19.67 (19.64); t32: 21.83/21.60 (21.71) |
| Granite Rapids (m8i) | `avx512` (v0.2.22) | t16: 17.84/17.82 (17.83); t20: 19.20/18.99 (19.09); t24: 19.85/19.95 (19.90); t32: 21.57/21.59 (21.58) |
| Granite Rapids (m8i) | `avx512-256-stream` (v0.2.22) | t16: 19.63/19.41 (19.52); t20: 20.49/20.49 (20.49); t24: 21.51/21.26 (21.39); t32: 24.53/24.55 (24.54) |
| Graviton2 | `neon` (f20e7bb) | t16: 11.11/11.12 (11.11); t24: 16.15/16.12 (16.13); t30: 18.83/18.42 (18.63); t32: 18.53/18.45 (18.49) |
| Graviton2 | `neon` (v0.2.22) | t16: 10.65/10.64 (10.64); t24: 15.41/15.40 (15.41); t30: 18.00/17.71 (17.85); t32: 18.33/18.42 (18.37) |
| Graviton3 | `neon-sha3` (f20e7bb) | t16: 18.47/18.46 (18.47); t24: 25.15/25.12 (25.13); t30: 27.20/27.18 (27.19); t32: 27.68/27.74 (27.71) |
| Graviton3 | `neon` (v0.2.22) | t16: 12.58/12.58 (12.58); t24: 17.74/17.81 (17.78); t30: 21.02/21.04 (21.03); t32: 21.76/21.78 (21.77) |
| Graviton4 | `neon-sha3` (f20e7bb) | t16: 21.64/21.64 (21.64); t24: 31.58/31.51 (31.54); t30: 37.63/37.59 (37.61); t32: 39.23/39.35 (39.29) |
| Graviton4 | `neon` (v0.2.22) | t16: 13.92/13.92 (13.92); t24: 20.48/20.46 (20.47); t30: 24.99/24.93 (24.96); t32: 26.33/26.34 (26.33) |

### Cost ledger

| Host | Instance | Lifecycle | Launched (UTC) | Termination verified (UTC) | Billable min (rounded up) | On-demand $/h | Conservative $ |
| --- | --- | --- | --- | --- | ---: | ---: | ---: |
| Zen 1 Naples | m5a.8xlarge | on-demand | 13:44:12 | 14:00:01 | 16 | 1.3760 | 0.469 |
| Zen 2 Rome | c5a.8xlarge | on-demand | 08:16:29 | 08:31:48 | 16 | 1.2320 | 0.430 |
| Zen 3 Milan | c6a.8xlarge | on-demand | 02:29:35 | 02:42:14 | 13 | 1.2240 | 0.367 |
| Zen 4 Genoa | m7a.8xlarge | on-demand | 04:57:37 | 05:29:49 | 33 | 1.8547 | 1.124 |
| Zen 5 Turin | m8a.8xlarge | on-demand | 04:02:58 | 04:34:44 | 32 | 1.9475 | 1.142 |
| Broadwell | r4.8xlarge | on-demand | 13:26:44 | 13:44:00 | 18 | 2.1280 | 0.740 |
| Skylake | m5.8xlarge | on-demand | 09:31:53 | 10:07:33 | 36 | 1.5360 | 1.026 |
| Cascade Lake | m5n.8xlarge | on-demand | 08:55:54 | 09:31:38 | 36 | 1.9040 | 1.246 |
| Ice Lake | c6i.8xlarge | on-demand | 07:42:34 | 08:16:11 | 34 | 1.3600 | 0.874 |
| Ice Lake (m6i) | m6i.8xlarge | on-demand | 12:52:24 | 13:26:22 | 34 | 1.5360 | 0.974 |
| Sapphire Rapids | c7i.8xlarge | on-demand | 05:30:11 | 06:04:08 | 34 | 1.4280 | 0.913 |
| Sapphire Rapids (m7i) | m7i.8xlarge | on-demand | 11:44:53 | 12:18:32 | 34 | 1.6128 | 1.018 |
| Granite Rapids | c8i.8xlarge | on-demand | 07:08:48 | 07:42:15 | 34 | 1.4994 | 0.953 |
| Granite Rapids (m8i) | m8i.8xlarge | on-demand | 12:18:47 | 12:52:12 | 34 | 1.6934 | 1.063 |
| Graviton2 | m6g.8xlarge | on-demand | 08:32:07 | 08:55:41 | 24 | 1.2320 | 0.596 |
| Graviton3 | m7g.8xlarge | on-demand | 06:44:58 | 07:08:35 | 24 | 1.3056 | 0.625 |
| Graviton4 | m8g.8xlarge | on-demand | 06:04:31 | 06:20:11 | 16 | 1.4362 | 0.485 |
| Graviton4 | m8g.8xlarge | on-demand | 06:21:15 | 06:44:45 | 24 | 1.4362 | 0.677 |

**Total: 18 leases, $14.72 conservative** (per-lease launch -> verified termination, rounded up to the minute; on-demand rate (spot unavailable), + 16 GiB gp3 + public IPv4 + $0.10 transfer contingency per lease). Cap $70 (initially $30 (stop $28); raised to $70 by the user ~03:55 UTC); launch stop $67.

<!-- /RESULTS -->

## Protocol

Fixed in `hostrun.py` before any launch; identical on every host.

1. Fresh instance (Ubuntu 24.04, 16 GiB gp3), nothing else running. The guest
   schedules `shutdown -h +50` (+40 for Milan) as its first user-data action and EC2
   shutdown behaviour is `terminate`; both are verified before work begins.
2. Every bundle file is SHA256-checked on the guest before and after timing.
3. Full-size (2 GiB) reference parity against RustCrypto `argon2` for every
   kernel that gets timed (`verify_cpu_kernels`; `verify_neon_dispatch` for the PR #44 build). A kernel is timed only if its
   covering verifier passed it.
4. Thread counts: SMT hosts 16, 20, 24 and the largest count *W*; 32-core hosts
   16, 24, 30, 32 (each only if <= *W*). *W* is the largest count for which
   `ceil(1.05 * W * 1024)` 2 MiB HugeTLB pages plus 5 GiB of ordinary RAM fit in
   `MemAvailable` (capped at the vCPU count). Milan ran before the sweep was widened
   (16, 24, 26; 16 was clearly best, so it was not repeated). The pool starts empty, is reserved once for the
   largest count (+5%), verified (`HugePages_Free`), and restored to 0 at the end.
5. Each invocation: `seine --bench --bench-kind backend --backend cpu --threads N
   --cpu-page-mode large --cpu-affinity auto --bench-cpu-kernel K
   --disable-cpu-autotune-threads --bench-secs 20 --bench-rounds 2
   --bench-warmup-rounds 1 --bench-output report.json` with a fresh `--data-dir`
   and `SEINE_*`/`BNMINER_*` variables scrubbed from the environment.
6. The kernel x thread-count grid is run once, then again in exactly reversed order.
7. The best grid cell is then confirmed with best / runner-up / runner-up / best
   invocations, the runner-up being the second-best kernel at the same thread
   count (on hosts with only one kernel: the same kernel at the second-best thread count).
8. An invocation is accepted only if its report proves the requested
   thread count, kernel (`cpu_kernel == cpu_kernel_requested`), `large` page mode,
   `auto` affinity, autotune off, CPU-only backend, native runtime, current PoW,
   full explicit-HugeTLB backing of `threads x 2 GiB` with zero regular/heap/THP
   arenas, zero allocation/dropped-event/assignment/control failures,
   `hashes == counted + late`, all lanes active, plus no swap-in/out or OOM kill,
   steal below 2%, and no change to the HugeTLB pool during the run.
9. **Metric:** completed H/s = sum(completed hashes) / sum(actual elapsed seconds
   *including* the round-end fence) over the two measured rounds. The report's
   `avg_hps` counts only hashes inside the configured window and is not used.
   The headline per host is the mean over all accepted invocations of the
   best cell (2 grid + 2 confirmation = n 4).

## Cleanup proof

- Every lease (18: 17 host runs + Graviton4 attempt 1) was terminated by
  `campaign.py` in `finally` after evidence collection; for each, the controller
  waited for EC2 state `terminated` and for the root volume to disappear
  (`describe-volumes` by ID returns nothing) before recording
  `verified_terminated_at`. All 18 ledger records carry `terminated=true` and
  `volumes_deleted=true`. Two launch attempts (Milan at 01:11, Naples at 10:07)
  were refused before any instance existed (spot role / quota taken by another
  session), and Broadwell attempt 1 was stopped while still waiting for quota
  (no instance) when the m-variant reruns were moved ahead of it.
- Every downloaded evidence archive matched the guest-computed SHA-256, and every
  extracted file matched the guest manifest (`collection-verification.json`).
- Final audit (`campaign.py cleanup`, 2026-10-25 14:00:44 UTC): no live
  instances and no volumes tagged `Experiment=readme-hardware-20261025` or
  `Campaign=seine-readme-benchmarks`; security group `sg-0ae9195e0861bed03`
  deleted (none remain by tag or name); no matching EC2 key pairs (none were
  created); local private key, public key and known-hosts files removed. Older
  terminated instance IDs had already aged out of `describe-instances`; their
  termination was verified individually at the time.
- The guest HugeTLB pool was restored to 0 on every host. No GPU work and no local
  builds were run; other sessions' instances were never touched.

## Binaries and parity provenance

| File on guest | SHA-256 | Identity |
| --- | --- | --- |
| `seine-v022` | `d336f33f6f610b868a2f0f6ccedfa7316481c62fb4e209db4a8b5d891a6df260` | v0.2.22 `seine-linux-x86_64.tar.gz` (archive SHA256SUMS verified). Reports: source fingerprint `7ad8df30888fb8f1`, `build_features=default,nvidia` (only `--backend cpu` used) |
| `seine-v022-arm` | `347195791061cc0820628517e5f9f5097b7b1d0ab1ebeefb9b11817f0d117021` | v0.2.22 `seine-linux-aarch64.tar.gz` |
| `seine-f20-arm` | `4e4b0bbdba495a44d7605a2bbc453b4f1d6d6761e1374761835a2de2fa74455e` | Draft PR #44 final commit `f20e7bb`, frozen `portable-codegen-arm` bundle (`release --no-default-features`, Rust 1.93.0, generic aarch64, no RUSTFLAGS); digest matches `cpu-campaign-20261024/evidence/binary-provenance.json`. Its report `git_commit` label is an inherited annotation, not executable identity |
| `verify-v022-x86` | `8e1e21ea79e5784b05787164e3ee647aca260545588f828d4dbd121d2f969b1b` | Frozen `verify_cpu_kernels` built at `4f5fec9`; `pow-kernel`/`pow-spec` trees identical to v0.2.22 (see `high-end-streaming-20261025/evidence/verifier-provenance.json`) |
| `verify-v022-arm` | `3b9db6ee3ed14ad339990f75c24f00c7619536efe9f944933460000a96862ae9` | `verify_cpu_kernels` built natively on the first Graviton4 guest from `git archive 6e54117` (Rust 1.93.0, `--locked --release`, isolated target, 30 s), then frozen for Graviton3/2 |
| `verify-f20-arm` | `bfb079866282221bd0c1ea0cbe06a9512b0ff1279b33be1f1468ddc6579847ce` | Frozen `verify_neon_dispatch` from `f20e7bb`: full-size RustCrypto reference parity for 3 nonces with dirty-arena `neon`/`neon-sha3`/`neon` switches; on hosts without SHA3 it checks that `neon-sha3` is rejected |

**How the PR #44 build selects SHA3 in bench mode:** explicitly. `--bench-cpu-kernel neon-sha3`
names the runtime-guarded kernel (`CpuKernel::NeonSha3`, available only when
`is_aarch64_feature_detected!("sha3")`; the build itself is generic, no target-feature
RUSTFLAGS). Graviton3/4 passed `neon-sha3` parity and timed it; Graviton2 (Neoverse-N1,
no SHA3) rejected it, so the same `f20e7bb` build was timed with portable `neon` instead.

Every timed kernel passed full-size parity on its own host before timing (see each
host's `parity.json`). Hosts without AVX-512 (Rome, Milan) passed `avx2` only.

## Deviations from the original brief (and why)

- **No spot.** `RunInstances` with spot options fails with
  `AuthFailure.ServiceLinkedRoleCreationNotPermitted`: the account has no
  `AWSServiceRoleForEC2Spot` and the SeineBenchmark role may not create it (dry-run
  does not detect this). Spot was retried, free of charge, on every launch; every
  lease is therefore **on-demand**, launched only when the shared 32-vCPU on-demand
  quota was actually free, one instance at a time, with hand-offs to other sessions
  coordinated through the parent session.
- **Tags.** The role only allows `Project=seine-avx2-validation` (shared with other
  sessions), so ownership is carried by `Experiment=readme-hardware-20261025` +
  `Campaign=seine-readme-benchmarks` (+ `Name=seine-readme-<label>`, `ExpiresAt`), and
  only ledger-recorded instance IDs carrying those tags are ever terminated.
- **SSH key.** EC2 `CreateKeyPair`/`ImportKeyPair` are denied, so a temporary local
  ed25519 key was injected through user-data and deleted at the end.
- **Instance choices (coordinator update).** For 32-physical-core generations the
  128 GiB m-variants (m7a, m8a, m6g, m7g, m8g) were used so all 32 cores could run a
  thread; SMT Intel generations whose best cell sat at the 64 GiB thread cap (26) were
  re-run on the 128 GiB m-variant and the higher result is the marketing number
  (both are retained). The sweep was widened to 16/20/24/max on SMT hosts and
  16/24/30/32 on 32-core hosts; the guest timer became 50 minutes accordingly.
- **Graviton4 needed two attempts.** Attempt 1 parsed the `f20e7bb` verifier's output
  format incorrectly and timed only release `neon`; the parser was fixed and the host
  re-run in full (both attempts retained; numbers use attempt 2).

## Limitations

- These are 32-vCPU cloud VM slices, not whole processors: clocks, turbo policy,
  memory channels and L3 share are whatever AWS gives that size. Numbers describe
  these instance types, not each architecture's best desktop or full-socket result.
- Thread counts are bounded by RAM (2 GiB per thread). 64 GiB SMT instances top out
  at 26 threads; c-variant numbers that peak there are lower bounds.
- One instance per generation, n = 4 for the headline cell; stdev shows
  within-instance repeatability only, not host-to-host variation.
- Most guests are one NUMA node with one L3 domain. Exceptions: Naples (2 NUMA
  nodes, 4x8 MiB L3), Milan (2 NUMA nodes, 2x32 MiB L3), Rome (1 node, 4x16 MiB L3),
  Genoa and Turin (1 node, 4x32 MiB L3). `--cpu-affinity auto` placed threads
  NUMA/L3-aware, physical cores first.
- Graviton headline numbers use the unreleased PR #44 build; the published v0.2.22
  result is shown alongside. x86 numbers are all the published binary.
- Explicit kernel/thread selection benchmarks; users get automatic selection, which
  may differ (e.g. `avx512-256-stream` is not yet automatic on every AVX-512 CPU).

## Reproduction

- `campaign.py run <label>`: launch, verify timer, upload, run `hostrun.py`,
  collect + verify, terminate + verify root-volume deletion (in `finally`).
- `run_queue.py <labels...>`: sequential priority queue with a budget stop.
- `cloud.py`: lease ledger, pricing, quota checks, tag-verified termination,
  audit and final cleanup (adapted from `cpu-campaign-20261024/cloud.py`).
- `summarize.py`: builds `summary.json` from verified evidence and the ledger.

Raw evidence (reports, logs, hardware dumps, archives, ledger) is kept in the
ignored `data/readme-hardware-20261025/`.
