#!/usr/bin/python3
"""Collect a quiescent energy campaign; retain private inventory only under data/."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('data', type=Path)
    args = parser.parse_args()
    assert hasattr(tarfile, 'data_filter'), 'Use /usr/bin/python3 (3.12+) for safe extraction'
    root = args.data.resolve()
    assert not (root / 'collected').exists()
    ssh = ['ssh', '-F', str(root / 'ssh-config'), 'cherry-energy']
    script = r'''
import hashlib,json,pathlib,subprocess,time
root=pathlib.Path('/root/seine-energy-20261025')
for unit in ['seine-cherry-energy.service','seine-cherry-smt.service','seine-cherry-power.service']:
    state=subprocess.check_output(['systemctl','show',unit,'--property=ActiveState','--value'],text=True).strip()
    assert state == 'inactive', (unit,state)
for phase in ['results','smt-results','power-results']:
    outcome=json.loads((root/phase/'outcome.json').read_text())
    assert outcome['status'].startswith('COMPLETE') and not outcome['cleanup_failures'],(phase,outcome)
cap=int(pathlib.Path('/sys/devices/platform/AMDI0097:00/hwmon/hwmon4/power1_cap').read_text())
pool=int(pathlib.Path('/proc/sys/vm/nr_hugepages').read_text())
swaps=pathlib.Path('/proc/swaps').read_text().splitlines()
assert cap==280000000 and pool==0
assert len(swaps)==2 and swaps[1].split()[0]=='/swap.img' and int(swaps[1].split()[3])==0
(root/'collection-state.json').write_text(json.dumps({'collected_at_epoch':time.time(),
    'restored_cap_uw':cap,'restored_hugepages':pool,'unused_swap_restored':True},indent=2)+'\n')
manifest={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
    for p in root.rglob('*') if p.is_file() and p.name!='archive-manifest.json' and '__pycache__' not in p.parts}
(root/'archive-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
archive='/root/seine-energy-evidence-20261025.tar.gz'
subprocess.run(['tar','--exclude=__pycache__','-czf',archive,'-C',str(root),'.'],check=True,timeout=90)
print(json.dumps({'sha256':hashlib.sha256(pathlib.Path(archive).read_bytes()).hexdigest(),'files':len(manifest)}))
'''
    remote = subprocess.run([*ssh, 'python3 -'], input=script, capture_output=True,
                            text=True, check=True, timeout=150)
    verification = json.loads(remote.stdout)
    temporary = root / 'energy-evidence.tar.gz.partial'
    subprocess.run(['scp', '-q', '-F', str(root / 'ssh-config'),
        'cherry-energy:/root/seine-energy-evidence-20261025.tar.gz', str(temporary)],
        check=True, timeout=150)
    assert hashlib.sha256(temporary.read_bytes()).hexdigest() == verification['sha256']
    archive = root / 'energy-evidence.tar.gz'
    temporary.replace(archive)
    destination = root / 'collected.partial'
    destination.mkdir(exist_ok=False)
    with tarfile.open(archive) as file:
        file.extractall(destination, filter='data')
    manifest = json.loads((destination / 'archive-manifest.json').read_text())
    assert len(manifest) == verification['files']
    for name, digest in manifest.items():
        assert hashlib.sha256((destination / name).read_bytes()).hexdigest() == digest, name
    expected = json.loads((destination / 'expected-files.json').read_text())
    for name, digest in expected.items():
        assert hashlib.sha256((destination / name).read_bytes()).hexdigest() == digest, name
    destination.rename(root / 'collected')
    verification['manifest_sha256'] = hashlib.sha256((root / 'collected/archive-manifest.json').read_bytes()).hexdigest()
    (root / 'archive-verification.json').write_text(json.dumps(verification, indent=2) + '\n')
    print(json.dumps(verification))


if __name__ == '__main__':
    main()
