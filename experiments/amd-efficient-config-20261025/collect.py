#!/usr/bin/python3
"""Preserve finished ring/page experiments, including rejected or unavailable runs."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile

EXPERIMENTS = {
    'efficient-config': ('/root/seine-efficient-config-20261025', ['seine-amd-efficient-config.service']),
}
LIVE = {'active', 'activating', 'deactivating', 'reloading'}


def verify(base, manifest):
    count = 0
    for name, digest in manifest.items():
        path = (base / name).resolve()
        assert path.is_relative_to(base.resolve()), name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, name
        count += 1
    return count


def inspect_collected(root):
    expected = json.loads((root / 'expected-files.json').read_text())
    verified = verify(root, expected)
    outcomes = {}
    for name in ('results', 'confirmation-results'):
        folder = root / name
        if not folder.exists():
            continue
        verified += verify(folder, json.loads((folder / 'manifest.json').read_text()))
        outcomes[name] = json.loads((folder / 'outcome.json').read_text())
    assert 'results' in outcomes, 'no completed primary evidence'
    restored = all(o['settings_restored'] and not o['cleanup_failures'] for o in outcomes.values())
    complete = all(o['status'].startswith('COMPLETE') or o['status'] == 'UNAVAILABLE'
                   for o in outcomes.values())
    return {'verified_manifest_entries': verified, 'outcomes': outcomes,
            'settings_restored': restored, 'ready_for_followup': restored and complete}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment', choices=EXPERIMENTS)
    parser.add_argument('--ssh-config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert hasattr(tarfile, 'data_filter'), 'Use /usr/bin/python3 with safe extraction support'
    remote, units = EXPERIMENTS[args.experiment]
    ssh = ['ssh', '-F', str(args.ssh_config), 'cherry-energy']
    for unit in units:
        state = subprocess.check_output(ssh + [f'systemctl show {unit} --property=ActiveState --value'],
                                        text=True, timeout=30).strip()
        if state in LIVE:
            print(unit + ' is still ' + state + '; no collection started.')
            return 75
        assert state in ('inactive', 'failed'), state
    assert not args.output.exists(), 'Use a fresh output directory'
    source = '''
import hashlib, json, pathlib, subprocess, tarfile
root = pathlib.Path(REMOTE)
for unit in UNITS:
    state = subprocess.check_output(['systemctl', 'show', unit, '--property=ActiveState', '--value'], text=True).strip()
    assert state in ('inactive', 'failed'), (unit, state)
expected = json.loads((root / 'expected-files.json').read_text())
files = set(expected) | {'expected-files.json'}
for name in ('results', 'confirmation-results'):
    folder = root / name
    if folder.exists():
        assert (folder / 'outcome.json').is_file()
        manifest = json.loads((folder / 'manifest.json').read_text())
        for path, digest in manifest.items():
            target = (folder / path).resolve()
            assert target.is_relative_to(folder)
            assert hashlib.sha256(target.read_bytes()).hexdigest() == digest, path
        files.add(name)
assert 'results' in files
for name in ('controller.log', 'confirmation-controller.log', 'prior-evidence-collected.json', 'run-authorization.json', 'prepared-files.json'):
    if (root / name).is_file(): files.add(name)
for name, digest in expected.items():
    target = (root / name).resolve()
    assert target.is_relative_to(root)
    assert hashlib.sha256(target.read_bytes()).hexdigest() == digest, name
with tarfile.open(root / 'evidence.tar.gz.tmp', 'w:gz') as archive:
    for name in sorted(files):
        target = (root / name).resolve()
        assert target.is_relative_to(root)
        archive.add(target, arcname=name)
(root / 'evidence.tar.gz.tmp').replace(root / 'evidence.tar.gz')
'''.replace('REMOTE', repr(remote)).replace('UNITS', repr(units))
    subprocess.run(ssh + ['python3 -c ' + shlex.quote(source)], check=True, timeout=240)
    args.output.mkdir(parents=True)
    archive = args.output / 'evidence.tar.gz'
    subprocess.run(['scp', '-q', '-F', str(args.ssh_config), 'cherry-energy:' + remote + '/evidence.tar.gz',
                    str(archive)], check=True, timeout=240)
    collected = args.output / 'collected'
    collected.mkdir()
    with tarfile.open(archive) as bundle:
        bundle.extractall(collected, filter='data')
    report = inspect_collected(collected)
    report['archive_sha256'] = hashlib.sha256(archive.read_bytes()).hexdigest()
    (args.output / 'collection-verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
