# Zen 2 and Zen 3 chart measurements

The existing server chart rows now use these native Linux measurements:

| CPU | AWS instance | Threads | H/s |
|---|---|---:|---:|
| AMD EPYC 7R32 | c5a.8xlarge | 16 | 17.42 |
| AMD EPYC 7R13 | c6a.8xlarge | 16 | 16.89 |

Both use `avx2-stream`, automatic affinity and 16 full 2 GiB arenas backed
by transparent huge pages. Each experiment ran baseline, candidate, candidate,
baseline, with one warmup round and one 20-second measured round per invocation.
The chart value is the arithmetic mean of the two candidate reports' `avg_hps`.
The measured changes shipped by v0.2.39; these are fixed-setting backend
benchmarks, not automatic cold-start or pool measurements.

`avg_hps` divides counted hashes by actual elapsed time including the final
fence. Completed late hashes are retained in the reports but excluded from
this metric's numerator. Allocation, warmup and teardown are outside the timed
interval. Two short candidate runs describe these configurations; no confidence
interval or cross-host percentage improvement is inferred from the old chart.

[summary.json](summary.json) binds each chart value to all four reports,
source revisions and SHA-256 hashes. The reports preserve the original benchmark
fields except `environment.hostname`, which was removed. Both original and
published checksums are recorded. The original workspace evidence is under
`benchmark-evidence/hashrate-20261026/{zen2-nt16,zen3-stores}/results/bin-ab-nt16/`.

To reproduce the chart calculation without running a benchmark:

```python
import json
from pathlib import Path
from statistics import mean

for record in json.loads(Path('summary.json').read_text())['records']:
    reports = [json.loads(Path(r['file']).read_text())
               for r in record['reports'] if '-cand.' in r['file']]
    measured = mean(report['avg_hps'] for report in reports)
    assert measured == record['hps']
    print(record['cpu'], f'{measured:.2f} H/s')
```
