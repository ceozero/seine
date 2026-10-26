"""Strict binding and raw-sample audit for the separately recorded resource check."""
import collections
import hashlib
import json
from pathlib import Path
import re
import tarfile


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_archive(root, archive):
    # Bind extracted manifests to the preserved archive, then every file to them.
    count = 0
    with tarfile.open(archive) as bundle:
        for name, base in (('expected-files.json', root), ('results/manifest.json', root / 'results')):
            contents = bundle.extractfile(name).read()
            assert contents == (root / name).read_bytes(), name
            for relative, sha in json.loads(contents).items():
                path = (base / relative).resolve()
                assert path.is_relative_to(base.resolve()), relative
                assert digest(path) == sha, relative
                count += 1
    return count


def counter(text, name):
    match = re.search(r'^' + re.escape(name) + r' (\d+)$', text, re.MULTILINE)
    assert match, (name, text)
    return int(match[1])


def pressure(text):
    match = re.search(r'^some .*total=(\d+)', text, re.MULTILINE)
    assert match, text
    return int(match[1])


def audit_samples(first, restart, optout, seed, constrained, logs):
    phases = collections.defaultdict(list)
    for rows in (first, restart, optout):
        assert rows and all(a['time'] < b['time'] for a, b in zip(rows, rows[1:]))
        assert all(counter(r['memory.events'], key) == 0 for r in rows
                   for key in ('oom', 'oom_kill'))
        for row in rows:
            phases[row['phase']].append(row)
    minimum = {'initial-stable': 595, 'one-arena-budget': 25, 'no-arena-budget': 25,
        'memory-recovery': 85, 'cpu-contention': 43, 'load-recovery': 85,
        'constrained-restart': 30, 'restart-recovery': 205, 'explicit-optout': 30}
    summary = {}
    for phase, seconds in minimum.items():
        rows = phases[phase]
        assert len(rows) >= 2 and rows[-1]['time'] - rows[0]['time'] >= seconds, phase
        hashes = [r['completed_hashes'] for r in rows]
        assert hashes == sorted(hashes), phase
        if phase not in ('one-arena-budget', 'no-arena-budget'):
            assert hashes[-1] > hashes[0], phase
        summary[phase] = {'samples': len(rows), 'sampled_duration_seconds': rows[-1]['time'] - rows[0]['time'],
            'sampled_hashes_delta': hashes[-1] - hashes[0],
            'requested_threads_counts': dict(collections.Counter(str(r['requested_threads']) for r in rows))}
    high = [counter(r['memory.events'], 'high') for r in first]
    psi = [pressure(r['memory.pressure']) for r in first]
    contention = [pressure(r['cpu.pressure']) for r in phases['cpu-contention']]
    assert max(high) > min(high), 'no actual memory.high events'
    assert max(psi) > min(psi), 'no actual memory PSI'
    for key, measure in (('memory.events', lambda text: counter(text, 'high')),
                         ('memory.pressure', pressure)):
        assert max(measure(r[key]) for r in phases['no-arena-budget']) > max(
            measure(r[key]) for r in phases['initial-stable']), 'injected phase did not add reclaim pressure'
    assert max(contention) > min(contention), 'no actual CPU contention'
    assert phases['no-arena-budget'][-1]['requested_threads'] == 0, 'did not park'
    assert seed['selected_threads'] > 1
    assert constrained['selected_threads'] == seed['selected_threads'], 'remembered count overwritten'
    assert all((r['requested_threads'] or 0) <= 1 for r in phases['constrained-restart'])
    assert any((r['requested_threads'] or 0) > 1 and
        int(r['smaps_rollup']['Anonymous'].split()[0]) >= 4 * 1024**2
        for r in phases['restart-recovery']), 'no real multi-arena restart recovery'
    assert 'cached starting point' in logs['restart']
    assert 'cpu-autotune |' not in logs['optout']
    assert all('quarantined' not in text.lower() for text in logs.values())
    return {'phases': summary, 'memory_high_events_increase': max(high) - min(high),
        'memory_psi_some_us_increase': max(psi) - min(psi),
        'cpu_contention_some_us_increase': max(contention) - min(contention),
        'remembered_threads': seed['selected_threads'],
        'maximum_restart_recovery_requested_threads': max(r['requested_threads'] or 0
                                                         for r in phases['restart-recovery'])}


def verify_supplement(original, supplement):
    original_archive = original.parent / 'productive-evidence.tar.gz'
    supplement_archive = supplement.parent / 'evidence.tar.gz'
    original_count = verify_archive(original, original_archive)
    supplement_count = verify_archive(supplement, supplement_archive)
    failed = read(original / 'results/outcome.json')
    assert failed['status'] == 'FAILED' and failed['settings_restored'] and not failed['cleanup_failures']
    assert failed['failure'] == "AssertionError('resource-lifecycle failed; inspect its log')"
    assert (original / 'results/resource-lifecycle.log').read_text().strip().endswith(
        'AssertionError: memory.high did not produce actual reclaim pressure')
    original_samples = read(original / 'results/lifecycle/seine-overnight-lifecycle-first.service-samples.json')
    assert all(counter(r['memory.events'], 'high') == 0 and pressure(r['memory.pressure']) == 0
               for r in original_samples), 'original failure differs from recorded fixture failure'
    provenance = read(supplement / 'supplement-provenance.json')
    assert provenance['original_archive_sha256'] == digest(original_archive)
    expected_candidate = read(original / 'binary-provenance.json')['candidate']['binary_sha256']
    assert provenance['original_candidate_sha256'] == expected_candidate == digest(supplement / 'candidate')
    assert provenance['original_lifecycle_sha256'] == digest(original / 'lifecycle.py')
    assert provenance['original_lifecycle_sha256'] == digest(supplement / 'original-lifecycle.py')
    assert provenance['supplement_lifecycle_sha256'] == digest(supplement / 'lifecycle.py')
    assert provenance['patch_sha256'] == digest(supplement / 'lifecycle-reclaim.patch')
    outcome = read(supplement / 'results/outcome.json')
    assert outcome['status'] == 'COMPLETE' and outcome['settings_restored'] and not outcome['cleanup_failures']
    vm = read(supplement / 'results/vm-checks.json')
    assert all(vm[key] == 0 for key in ('pswpin', 'pswpout', 'oom_kill'))
    protocol = read(supplement / 'results/protocol.json')
    assert protocol['candidate_sha256'] == expected_candidate
    assert protocol['cpus'] == '0-3' and protocol['page_mode'] == 'regular' and protocol['worker_ceiling'] == 4
    assert protocol['initial_seconds'] == 600 and protocol['memory_recovery_seconds'] == 90
    original_hardware = read(original / 'results/protocol.json')['hardware']
    for key in ('Vendor ID', 'CPU family', 'Model', 'CPU(s)', 'Socket(s)', 'NUMA node(s)'):
        assert protocol['hardware'][key] == original_hardware[key], key
    folder = supplement / 'results/lifecycle'
    assert (folder / 'COMPLETE').exists()
    assert read(folder / 'reclaim-load-exit.json')['exit_code'] is not None
    prefix = 'seine-overnight-supplement-lifecycle-'
    samples = {role: read(folder / (prefix + role + '.service-samples.json'))
               for role in ('first', 'restart', 'optout')}
    logs = {role: (folder / (prefix + role + '.service.log')).read_text() for role in samples}
    audited = audit_samples(samples['first'], samples['restart'], samples['optout'],
        read(folder / 'seed-before-restart.json'), read(folder / 'seed-during-constrained-restart.json'), logs)
    return {'status': 'COMPLETE_WITH_SEPARATE_RESOURCE_SUPPLEMENT',
        'original_outcome': failed, 'original_archive_sha256': digest(original_archive),
        'supplement_archive_sha256': digest(supplement_archive),
        'supplement_manifest_sha256': digest(supplement / 'results/manifest.json'),
        'candidate_sha256': expected_candidate, 'original_verified_entries': original_count,
        'supplement_verified_entries': supplement_count, **audited,
        'scope': 'Original fixture remains FAILED. All productive windows unchanged; same candidate passed a separately bound, fully repeated resource fixture with measurable reclaim pressure.'}
