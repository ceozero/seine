#!/usr/bin/env python3
"""Export reviewable measurement records without cloud/SSH state or app data."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('collected', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    source, target = args.collected.resolve(), args.destination.resolve()
    manifest = json.loads((source/'result-manifest.json').read_text())
    for name, digest in manifest.items():
        assert hashlib.sha256((source/name).read_bytes()).hexdigest() == digest, name
    target.mkdir(parents=True, exist_ok=False)
    kept = {}
    omitted = {}
    private_files = 0
    for name, digest in manifest.items():
        path = Path(name)
        # Detailed raw process samples remain in the verified local archive.
        # App runtime state is never part of public measurement evidence.
        if 'config' in path.parts:
            private_files += 1
            continue
        if path.name == 'samples.json':
            omitted[name] = digest
            continue
        dest = target/path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source/path, dest)
        assert hashlib.sha256(dest.read_bytes()).hexdigest() == digest
        kept[name] = digest
    for name in ['expected-binaries.json']:
        if (source/name).exists():
            shutil.copy2(source/name, target/name)
            kept[name] = hashlib.sha256((target/name).read_bytes()).hexdigest()
    (target/'manifest.json').write_text(json.dumps(kept,indent=2)+'\n')
    (target/'omitted-sample-hashes.json').write_text(json.dumps(omitted,indent=2)+'\n')
    print(json.dumps({'exported_files':len(kept),'omitted_files':len(omitted),
        'omitted_runtime_state_files':private_files,
        'exported_bytes':sum((target/name).stat().st_size for name in kept)}))


if __name__ == '__main__':
    main()
