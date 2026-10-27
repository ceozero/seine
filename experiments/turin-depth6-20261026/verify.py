"""Audit the published capture against supplied independent reference outputs."""
import csv
import hashlib
import json
from pathlib import Path
from run_ab import validate

root = Path(__file__).resolve().parent
manifest = json.loads((root / 'manifest.json').read_text())
for name, expected in manifest['sha256'].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name
references = json.loads((root / 'reference-subset.json').read_text())
count = 0
for stage, pairs, seconds in [('screen', 2, 20), ('confirm', 3, 30)]:
    rows = list(csv.DictReader((root / stage / 'results.tsv').open(), delimiter='\t'))
    assert len(rows) == pairs * 2
    assert {(int(r['pair']), r['variant']) for r in rows} == {
        (p, v) for p in range(1, pairs + 1) for v in ['baseline', 'candidate']}
    for row in rows:
        path = root / stage / f"pair{row['pair']}-{row['variant']}.json"
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == row['report_sha256']
        report = json.loads(raw)
        assert report.get('fence_policy') == 'reference-demand'
        rate = validate(report, 64, 6 if row['variant'] == 'candidate' else 4, 32, seconds, 5)
        assert abs(rate - float(row['avg_hps'])) < 1e-10
        header = bytes(report['header_base']).hex()
        for worker in report['workers_results']:
            for nonce, digest in worker['claims']:
                assert references[header + ':' + str(nonce)] == bytes(digest).hex()
                count += 1
assert count == 13119
print(f'Passed: {count:,} captured hashes match {len(references):,} independent reference values; all manifest checksums match.')
