# Zen 3 release comparison

**18.09 H/s** on an AMD EPYC 7R13 AWS c6a.8xlarge instance with the official
Seine v0.2.39 Linux x86-64 release, 16 fixed mining threads and full transparent
huge-page backing. The allocation exposes 32 vCPUs / 16 physical cores and
64 GiB of RAM. This is a VM allocation, not a complete EPYC socket.

Measured October 27, 2026, starting at approximately 4:14 a.m. EDT. The official
v0.2.29 and v0.2.39 executables ran in baseline/current/current/baseline order:

| Order | Version and kernel | Counted H/s |
|---|---|---:|
| 1 | v0.2.29, AVX2 | 12.09545 |
| 2 | v0.2.39, AVX2 streaming | 17.69380 |
| 3 | v0.2.39, AVX2 streaming | 18.47948 |
| 4 | v0.2.29, AVX2 | 12.08756 |

The current mean is **18.08664 H/s**, versus **12.09151 H/s** for the baseline.
The geometric mean of the adjacent paired ratios is **+49.54610%**. This is an
overall release/configuration comparison on the same instance; it does not
attribute the gain to one patch or infer a gain over an earlier different VM.
The two current measurements span 17.69–18.48 H/s. Two paired observations do
not establish a cross-host confidence interval.

## Method

Each invocation used a 120-second warmup round followed by one 120-second
backend round. The rate is the report's `avg_hps`: counted hashes divided by
actual measured elapsed time including the final fence. Allocation, warmup and
shutdown are outside that interval. Completed late hashes and complete process
timings are retained separately; dividing measured-round hashes by the process
time would include an uncounted warmup and is not the chart metric.

All measured rounds verified 16 workers / 32 GiB of transparent huge-page arenas
and zero allocation failures during the measured round. Automatic page mode can
record a failed explicit HugeTLB attempt during startup before successfully
falling back to THP; the warmup logs retain those attempts. There was no swap I/O
or OOM event, and CPU steal was below 0.001% in each invocation.

The full-size independent Argon2 reference checker built from each release's
source passed every supported kernel, including AVX2 streaming in v0.2.39.
These checks cover the verifier's full 2 GiB test input; they are not a claim
that every timed benchmark hash was independently reverified.

The executable SHA-256 values are:

- v0.2.29: `c922c41bfe01a8c34d7eb7d2b754d3032b9beb055a0c1941d04293164ab4d18d`
- v0.2.39: `decf8613f8f900932b0fa88bd269f5fca15267dc51f3b65aa66bdfeb664cf094`

Both release archives were checked against their published checksums.
[summary.json](summary.json) records all rates and original/published report
hashes. Published benchmark reports remove only `environment.hostname`.
[remote_measure.py](remote_measure.py) contains the exact runner and validation.
The rented instance was terminated and its temporary security group/key removed.

## Reproduction

On an otherwise idle matching instance with sufficient available RAM and THP:

```sh
seine --bench --bench-kind backend --backend cpu --threads 16 \
  --disable-cpu-autotune-threads --bench-cpu-kernel avx2-stream \
  --cpu-page-mode auto --bench-secs 120 --bench-rounds 1 \
  --bench-warmup-rounds 1 --bench-output result.json \
  --data-dir ./benchmark-data --telemetry off --ui plain
```

Use `avx2` for the v0.2.29 baseline and preserve the alternating run order.
These fixed-setting results do not measure automatic startup or pool-credited work.
