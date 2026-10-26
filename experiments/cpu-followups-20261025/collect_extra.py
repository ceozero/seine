#!/usr/bin/env python3
"""Download and verify post-controller evidence before rental cleanup."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile


def main():
    p = argparse.ArgumentParser()
    p.add_argument('host', choices=['intel', 'skylake', 'epyc'])
    p.add_argument('experiment', choices=['alignment', 'lifecycle'])
    args = p.parse_args()
    root = Path(__file__).resolve().parents[2]/'data/followups-20261025'/(args.host+'-lease')
    target = root/args.experiment
    target.mkdir(exist_ok=False)
    archive = target/'results.tar.gz'
    subprocess.run(['scp','-q','-F',str(root/'ssh-config'),
        'ep:/home/ubuntu/followups/'+args.experiment+'/results.tar.gz',str(archive)],check=True,timeout=120)
    out = target/'collected'
    out.mkdir()
    with tarfile.open(archive) as bundle:
        bundle.extractall(out,filter='data')
    manifest = json.loads((out/'result-manifest.json').read_text())
    for name, digest in manifest.items():
        assert hashlib.sha256((out/name).read_bytes()).hexdigest() == digest, name
    record = {'files_verified':len(manifest),'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
        'outcome':json.loads((out/'results/outcome.json').read_text())}
    (target/'archive-verification.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record,indent=2))


if __name__ == '__main__':
    main()
