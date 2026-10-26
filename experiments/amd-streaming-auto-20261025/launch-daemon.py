#!/usr/bin/env python3
"""Stage the same native binary for a longer, loopback-only kernel/cache check."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

REPO=Path(__file__).resolve().parents[2]
DATA=REPO/'data/amd-streaming-auto-20261025'
BASE=Path('/mnt/c/Users/zp/AppData/Local/Temp/seine-auto-20261025-archdispatch')
ROOT=BASE/'daemon-check'


def main():
    for _ in range(100):
        if (DATA/'queue-daemon.json').exists():break
        time.sleep(.1)
    job=json.loads((DATA/'queue-daemon.json').read_text())['id']
    subprocess.run(['gpuq','gaming','check','--quiet'],check=True)
    status=json.loads(subprocess.check_output(['gpuq','status'],text=True));assert status['activeJobId']==job
    ROOT.mkdir(exist_ok=False);(ROOT/'target/release').mkdir(parents=True)
    binary=BASE/'target/release/seine.exe'
    expected=json.loads((DATA/'binaries.json').read_text())['target/release/seine.exe']
    assert hashlib.sha256(binary.read_bytes()).hexdigest()==expected
    shutil.copy2(binary,ROOT/'target/release/seine.exe')
    for name in ['source.json','deadline.json']:shutil.copy2(BASE/name,ROOT/name)
    (ROOT/'resume.json').write_text(json.dumps({'binary_sha256':expected,'source_directory':'../first-run-results','accepted_files':{},'job_id':'2ddf27a78f5141f1985419367ca894f6'},indent=2)+'\n')
    hashes={}
    for name in ['native_run.py','fixture.py','daemon_fixture.py','daemon_probe.py']:
        p=Path(__file__).with_name(name);shutil.copy2(p,ROOT/name);hashes[name]=hashlib.sha256(p.read_bytes()).hexdigest()
    script=Path(__file__).with_name('run-native.ps1').read_text().replace("'native_run.py'","'daemon_probe.py'")
    (ROOT/'run-native.ps1').write_text(script);hashes['run-native.ps1']=hashlib.sha256((ROOT/'run-native.ps1').read_bytes()).hexdigest()
    (DATA/'daemon-harness.json').write_text(json.dumps(hashes,indent=2)+'\n')
    native=subprocess.check_output(['wslpath','-w',str(ROOT)],text=True).strip()
    try:
        subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',native+'\\run-native.ps1','-Root',native,'-JobId',job],check=True,timeout=1500)
    finally:
        if (ROOT/'results').exists():shutil.copytree(ROOT/'results',DATA/'daemon-results',dirs_exist_ok=True)
        for p in ROOT.glob('native-driver.*'):shutil.copy2(p,DATA/('daemon-'+p.name))
        hashes={str(p.relative_to(DATA/'daemon-results')):hashlib.sha256(p.read_bytes()).hexdigest() for p in (DATA/'daemon-results').rglob('*') if p.is_file()}
        (DATA/'daemon-file-checksums.json').write_text(json.dumps(hashes,indent=2)+'\n')


if __name__=='__main__':main()
