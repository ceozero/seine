#!/usr/bin/env python3
"""WSL-side admission and evidence collection for the owned native controller."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / 'data/amd-streaming-auto-20261025'
ROOT = Path('/mnt/c/Users/zp/AppData/Local/Temp/seine-auto-20261025-archdispatch')


def main():
    for _ in range(100):
        if (DATA / 'queue.json').exists():
            break
        time.sleep(.1)
    job = json.loads((DATA / 'queue.json').read_text())['id']
    subprocess.run(['gpuq', 'gaming', 'check', '--quiet'], check=True)
    status = json.loads(subprocess.check_output(['gpuq', 'status'], text=True))
    assert status['activeJobId'] == job
    scripts = ['native_run.py', 'run-native.ps1', 'fixture.py']
    hashes = {}
    for name in scripts:
        source = Path(__file__).with_name(name)
        hashes[name] = hashlib.sha256(source.read_bytes()).hexdigest()
        shutil.copy2(source, ROOT / name)
    (DATA / 'harness.json').write_text(json.dumps(hashes, indent=2) + '\n')
    native = subprocess.check_output(['wslpath', '-w', str(ROOT)], text=True).strip()
    try:
        subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive',
                        '-ExecutionPolicy', 'Bypass', '-File', native + '\\run-native.ps1',
                        '-Root', native, '-JobId', job], check=True, timeout=2800)
    finally:
        if (ROOT / 'results').exists():
            shutil.copytree(ROOT / 'results', DATA / 'results', dirs_exist_ok=True)
        for pattern in ['native-driver.*', 'build.*', 'test.*', 'source.json']:
            for path in ROOT.glob(pattern):
                shutil.copy2(path, DATA / path.name)
        hashes = {str(p.relative_to(DATA / 'results')): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in (DATA / 'results').rglob('*') if p.is_file()}
        (DATA / 'file-checksums.json').write_text(json.dumps(hashes, indent=2) + '\n')


if __name__ == '__main__':
    main()
