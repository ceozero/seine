"""Adapt the frozen demand-fence example to the repository benchctl TSV contract.

Full-size reference parity precedes timing. All measured claims remain in raw
reports for independent verification after the rental; rates here are provisional.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
import time


def validate(report, ring, depth, workers, seconds, warmup):
    assert report['kind'] == 'ring_grid_experiment' and report['schema'] == 1
    assert report['workers'] == workers
    assert report['memory_kib_per_worker'] == 2097152
    assert (report['ring'], report['depth']) == (ring, depth)
    assert report['requested_seconds'] == seconds and report['warmup_seconds'] == warmup
    assert report['header_base'] == [0x42] * 92
    elapsed = report['hashing_seconds']
    assert math.isfinite(elapsed) and elapsed >= seconds
    assert report['wall_seconds'] > elapsed
    assert report['os'] == 'windows'
    assert report['backing_before_measurement'] is None
    memory = report['memory_observation']
    assert memory['allocator'] == 'VirtualAlloc'
    assert memory['allocation_flags'] == 0x3000
    assert memory['large_pages_requested'] is False
    assert memory['working_set_bytes'] >= workers * 2097152 * 1024
    assert memory['private_usage_bytes'] >= workers * 2097152 * 1024
    rows = report['workers_results']
    assert len(rows) == workers and {r['worker'] for r in rows} == set(range(workers))
    seen = set()
    for row in rows:
        assert row['first_hash_reference_passed'] is True
        assert seconds <= row['hashing_seconds'] <= elapsed + 1e-6
        assert row['hashes'] == len(row['claims']) and row['hashes'] > 0
        for nonce, digest in row['claims']:
            assert type(nonce) is int and 0 <= nonce < 2**64 and nonce not in seen
            assert len(digest) == 32 and all(type(x) is int and 0 <= x < 256 for x in digest)
            seen.add(nonce)
    assert report['hashes'] == len(seen)
    rate = len(seen) / elapsed
    assert math.isclose(report['hps_unverified'], rate, rel_tol=1e-12)
    return rate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--pairs', type=int, choices=[2, 3], required=True)
    parser.add_argument('--seconds', type=int, choices=[20, 30], required=True)
    args = parser.parse_args()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    assert not (out / 'results.tsv').exists(), 'Preserve existing evidence'
    binaries = {'baseline': args.baseline, 'candidate': args.candidate}
    digests = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name,path in binaries.items()}
    with (out / 'results.tsv').open('w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['pair', 'order', 'variant', 'avg_hps', 'report_sha256'], delimiter='\t')
        writer.writeheader()
        for pair in range(1, args.pairs + 1):
            order = ['baseline', 'candidate'] if pair % 2 else ['candidate', 'baseline']
            for position, label in enumerate(order, 1):
                ring, depth = 8, 2
                binary = binaries[label]
                workers = 32
                assert hashlib.sha256(binary.read_bytes()).hexdigest() == digests[label]
                path = out / f'pair{pair}-{label}.json'
                command = [str(binary), 'bench', str(ring), str(depth), str(workers), str(args.seconds), '5']
                with path.open('w') as log, path.with_suffix('.stderr').open('w') as errors:
                    subprocess.run(command, check=True, stdout=log, stderr=errors, timeout=120)
                raw = path.read_bytes()
                report = json.loads(raw)
                assert report.get('fence_policy') == ('reference-demand' if label == 'candidate' else None)
                rate = validate(report, ring, depth, workers, args.seconds, 5)
                writer.writerow({'pair': pair, 'order': position, 'variant': label,
                                 'avg_hps': rate, 'report_sha256': hashlib.sha256(raw).hexdigest()})
                file.flush()
                time.sleep(3)


if __name__ == '__main__':
    main()
