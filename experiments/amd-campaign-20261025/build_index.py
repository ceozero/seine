#!/usr/bin/python3
"""Index audited campaign datasets without merging incompatible measurements."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATASETS = (
    ('cherry-epyc-energy-20261025', 'measured_manual_configuration', False),
    ('genoa-streaming-20261025', 'accepted_automatic_policy', True),
    ('amd-overnight-20261025', 'accepted_automatic_policy', True),
    ('amd-ring-locality-20261025', 'rejected_kernel_candidate', False),
    ('amd-page-size-20261025', 'measured_manual_configuration', False),
    ('amd-trial-windows-20261025', 'accepted_automatic_policy', True),
)


def build():
    datasets, identifiers = [], set()
    for campaign, status, policy_changed in DATASETS:
        folder = ROOT / 'experiments' / campaign
        source = folder / 'benchmark-records.json'
        document = json.loads(source.read_text())
        assert document['schema'] == 'seine-hardware-benchmark-records/v1'
        records = document['records']
        csv_source = folder / 'benchmark-records.csv'
        with csv_source.open(newline='') as handle:
            reader = csv.DictReader(handle)
            columns = reader.fieldnames
            csv_records = list(reader)
        assert columns and len(columns) == len(set(columns)) and 'id' in columns
        assert len(csv_records) == len(records), campaign
        for row, csv_row in zip(records, csv_records):
            assert all(key in row for key in columns), (campaign, row['id'])
            expected = {key: '' if row[key] is None else str(row[key]) for key in columns}
            assert csv_row == expected, (campaign, row['id'], 'CSV differs from JSON')
        for row in records:
            assert row['id'] not in identifiers
            identifiers.add(row['id'])
            assert row['campaign'] == campaign
            assert len(row['observations']) == row['repetitions']
            assert math.isfinite(row['hps_sample_cv']) and row['hps_sample_cv'] >= 0
            hashes = row.get('completed_hashes', row.get('completed_hashes_lower_bound'))
            seconds = row.get('invocation_seconds', row.get('elapsed_seconds'))
            assert hashes > 0 and seconds > 0
            assert math.isclose(row['hps'], hashes / seconds, rel_tol=1e-12)
            if row['power_scope'] == 'unmeasured':
                assert row['package_watts'] is None
                assert row.get('package_joules_per_hash') is None
            else:
                assert row['power_scope'] == 'cpu_package'
                assert math.isclose(row['package_watts'], row['package_joules'] / seconds, rel_tol=1e-12)
                assert math.isclose(row['package_joules_per_hash'], row['package_joules'] / hashes, rel_tol=1e-12)
        datasets.append({
            'campaign': campaign, 'status': status, 'default_policy_changed': policy_changed,
            'results': str((folder / 'RESULTS.md').relative_to(ROOT)),
            'records_json': str(source.relative_to(ROOT)),
            'records_csv': str(csv_source.relative_to(ROOT)),
            'records_json_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'records_csv_sha256': hashlib.sha256(csv_source.read_bytes()).hexdigest(),
            'record_count': len(records), 'record_ids': [row['id'] for row in records],
            'metric_scopes': sorted({row['metric_scope'] for row in records}),
            'power_scopes': sorted({row['power_scope'] for row in records}),
            'selection_modes': sorted({row['selection'] for row in records}),
            'workloads': sorted({row['workload'] for row in records}),
        })
    return {'schema': 'seine-benchmark-campaign-index/v1', 'date': '2026-10-25',
        'record_count': len(identifiers), 'datasets': datasets,
        'comparison_rules': [
            'Compare only the interleaved roles within each documented phase and configuration.',
            'Keep 60-second and 120-second energy series separate, and cold discovery separate from cached restart.',
            'Ring screens at each worker count and ring variant are separate pairs; do not pool their repeated baselines.',
            'Automatic productive lower bounds, steady-state backend rates and whole-invocation energy rates are distinct metrics.',
            'A configured power cap is not measured watts; unmeasured package/wall/DRAM power must stay unmeasured.',
            'Keep VM allocation separate from bare-metal socket performance; do not fill unknown physical memory fields.',
            'Manual configuration gains are not zero-configuration shipping improvements.',
            'A rejected candidate remains research evidence, not an adopted improvement.',
            'Do not multiply independent gains or sum changes measured against different baselines.',
        ]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = build()
    contents = json.dumps(result, indent=2) + '\n'
    path = Path(__file__).with_name('benchmark-index.json')
    if args.check:
        assert path.read_text() == contents, 'Index differs from the audited source records; regenerate it.'
    else:
        path.write_text(contents)
    print(f"Verified {result['record_count']} records in {len(result['datasets'])} datasets.")


if __name__ == '__main__':
    main()
