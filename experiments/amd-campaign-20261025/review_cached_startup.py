#!/usr/bin/python3
"""Review preserved startup snapshots; estimates are not a new performance result."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'amd-overnight-20261025'))
from audit_resource import verify_archive


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def review(root):
    archive = root.parent / 'productive-evidence.tar.gz'
    verified = verify_archive(root, archive)
    rows = []
    for role in ('control', 'candidate'):
        for pair in range(1, 5):
            label = f'joint-warm-{role}-{pair}'
            folder = root / 'results' / label
            assert (folder / 'COMPLETE').is_file()
            log = (folder / 'miner.log').read_text()
            workers = int(re.search(r'starting with (\d+) threads \(cached starting point\)', log)[1])
            reserve_pct = int(re.search(r'automatic sizing reserves (\d+)%', log)[1])
            samples = json.loads((folder / 'samples.json').read_text())
            # First observed fully allocated starting point, before the count probe.
            sample = next(s for s in samples if
                int(s.get('smaps_rollup', {}).get('Private_Hugetlb', '0 kB').split()[0]) * 1024
                == workers * 2**31)
            memory = sample['meminfo']
            free_pool = max(0, memory['HugePages_Free'] - memory['HugePages_Rsvd'])
            host_available = (memory['MemAvailable'] + free_pool * memory['Hugepagesize']) * 1024
            limit = min(int(sample[key]) for key in ('memory.high', 'memory.max'))
            total = min(memory['MemTotal'] * 1024, limit)
            available = min(host_available, max(0, limit - int(sample['memory.current'])))
            reserve = total // 100 * reserve_pct
            without_owned = max(0, available - reserve) // 2**31
            with_owned = max(0, min(total, available + workers * 2**31) - reserve) // 2**31
            count_probe = re.search(
                r'([\d.]+)s\s+INFO\s+MINER\s+cpu-autotune \| (\d+) threads per CPU backend: '
                r'measuring useful mining work \(available=(\d+), effective cap=(\d+)\)', log)
            restore = re.search(
                r'([\d.]+)s\s+INFO\s+MINER\s+cpu-autotune \| restoring confirmed avx512-256-stream', log)
            assert count_probe and restore
            # Even ignoring both the reserve and cgroup constraint, the observed
            # host headroom without owned arenas is below the existing count.
            assert host_available // 2**31 < workers
            rows.append({
                'label': label, 'starting_workers': workers,
                'snapshot_seconds_after_first_observation': sample['time'] - samples[0]['time'],
                'observed_private_hugetlb_bytes': workers * 2**31,
                'host_available_plus_unreserved_hugetlb_bytes': host_available,
                'host_zero_reserve_upper_workers_without_owned': host_available // 2**31,
                'child_cgroup_no_reclaim_estimate_without_owned_workers': without_owned,
                'child_cgroup_no_reclaim_estimate_with_owned_workers': with_owned,
                'logged_count_probe_seconds': float(count_probe[1]),
                'logged_count_probe_workers': int(count_probe[2]),
                'logged_count_probe_available_workers': int(count_probe[3]),
                'logged_count_probe_effective_cap': int(count_probe[4]),
                'logged_cached_stream_restore_seconds': float(restore[1]),
                'miner_log_sha256': digest(folder / 'miner.log'),
                'samples_sha256': digest(folder / 'samples.json'),
            })
    return {
        'kind': 'diagnostic_snapshot_review_not_performance_comparison',
        'source_experiment': 'amd-overnight-20261025',
        'archive_sha256': digest(archive), 'verified_manifest_entries': verified,
        'observations': rows,
        'interpretation': 'All eight observed cached starting allocations exceed host headroom computed without crediting owned arenas. This supports investigating inconsistent initial versus periodic capacity accounting.',
        'limitations': [
            'Snapshots are approximately 10 seconds after launch, not at Controller::start. Initial capacity and recovery_pending were not traced.',
            'Child-cgroup estimates assume no reclaimable-cache credit and no tighter ancestor; they are calculations, not captured controller values.',
            'Private HugeTLB mappings identify the observed starting allocation; they do not directly capture the controller committed_bytes field.',
            'Logged probe and restore times are observations from existing runs. No fix, causal A/B, predicted gain, or new benchmark record is claimed.',
            'The original archive remains FAILED because its separate resource fixture did not create reclaim pressure; this review uses only its completed cached windows.',
        ],
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('collected', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = review(args.collected)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(f"Reviewed {len(result['observations'])} complete cached windows; no performance comparison added.")
