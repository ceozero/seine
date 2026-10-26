#!/usr/bin/python3
"""Collect Turin evidence only after its measurement controller is inactive."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile


REMOTE = '/root/seine-overnight-20261025'
UNIT = 'seine-amd-productive.service'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ssh-config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert hasattr(tarfile, 'data_filter'), 'Use /usr/bin/python3 with safe extraction support'
    ssh = ['ssh', '-F', str(args.ssh_config), 'cherry-energy']
    state = subprocess.check_output(ssh + [
        f'systemctl show {UNIT} --property=ActiveState --value'], text=True, timeout=30).strip()
    if state in ('active', 'activating', 'deactivating', 'reloading'):
        print('Measurement controller is still ' + state + '; no archive or collection started.')
        return 75
    assert state in ('inactive', 'failed'), state
    assert not args.output.exists(), 'Use a fresh evidence directory; never overwrite an earlier collection'
    # The second state check closes the gap between the preflight and archiving.
    # Preserve failed experiments too, but never mark them ready for follow-up.
    source = '''
import hashlib, json, pathlib, subprocess, tarfile
root = pathlib.Path('/root/seine-overnight-20261025')
state = subprocess.check_output(['systemctl', 'show', 'seine-amd-productive.service',
    '--property=ActiveState', '--value'], text=True).strip()
assert state in ('inactive', 'failed'), state
manifest = json.loads((root / 'results/manifest.json').read_text())
for name, digest in manifest.items():
    path = (root / 'results' / name).resolve()
    assert path.is_relative_to(root / 'results')
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, name
files = ['results', 'expected-files.json', 'binary-provenance.json', 'controller.log']
files += list(json.loads((root / 'expected-files.json').read_text()))
with tarfile.open(root / 'productive-evidence.tar.gz.tmp', 'w:gz') as archive:
    for name in sorted(set(files)):
        path = root / name
        assert path.resolve().is_relative_to(root)
        archive.add(path, arcname=name)
(root / 'productive-evidence.tar.gz.tmp').replace(root / 'productive-evidence.tar.gz')
'''
    subprocess.run(ssh + ['python3 -c ' + shlex.quote(source)], check=True, timeout=180)
    args.output.mkdir(parents=True)
    archive = args.output / 'productive-evidence.tar.gz'
    subprocess.run(['scp', '-q', '-F', str(args.ssh_config),
        'cherry-energy:' + REMOTE + '/productive-evidence.tar.gz', str(archive)],
        check=True, timeout=180)
    collected = args.output / 'collected'
    collected.mkdir()
    with tarfile.open(archive) as bundle:
        bundle.extractall(collected, filter='data')
    manifests = [(collected / 'results', collected / 'results/manifest.json'),
                 (collected, collected / 'expected-files.json')]
    verified = 0
    for base, manifest in manifests:
        for name, digest in json.loads(manifest.read_text()).items():
            path = (base / name).resolve()
            assert path.is_relative_to(base.resolve()), name
            assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, name
            verified += 1
    outcome = json.loads((collected / 'results/outcome.json').read_text())
    report = {'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
              'verified_manifest_entries': verified, 'outcome': outcome,
              'ready_for_followup': outcome['status'] == 'COMPLETE' and
                  outcome['settings_restored'] and not outcome['cleanup_failures']}
    (args.output / 'collection-verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
