#!/usr/bin/env python3
"""Build isolated streaming-ring prototypes, verify them, then restore source."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
BASE = 'd92abe5872bf215a2f001af4e3891c4afa1a3fcc'
FILES = ['pow-kernel/src/fixed_argon.rs', 'pow-kernel/src/fixed_argon/avx512_256.rs']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, log, env, timeout):
    print('Starting:', ' '.join(command), flush=True)
    with log.open('w') as file:
        subprocess.run(command, cwd=ROOT, env=env, stdout=file, stderr=subprocess.STDOUT,
                       check=True, timeout=timeout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path, required=True)
    parser.add_argument('--rings', nargs='+', type=int, choices=[64, 32, 16], default=[64, 32, 16])
    args = parser.parse_args()
    os.chdir(ROOT)
    branch = subprocess.check_output(['git', 'branch', '--show-current'], text=True).strip()
    assert branch.startswith('codex/amd-ring-'), 'Use an owned experimental worktree'
    assert not subprocess.check_output(['git', 'status', '--porcelain', '--', *FILES], text=True)
    assert not os.environ.get('RUSTFLAGS') and not os.environ.get('CARGO_ENCODED_RUSTFLAGS')
    original = {name: (ROOT / name).read_bytes() for name in FILES}
    for name, contents in original.items():
        assert contents == subprocess.check_output(['git', 'show', BASE + ':' + name]), name
    source_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    target = args.target.resolve()
    env = dict(os.environ, CARGO_TARGET_DIR=str(target))
    output = ROOT / 'data/amd-ring-locality-20261025'
    output.mkdir(parents=True, exist_ok=True)
    for ring in args.rings:
        variant = output / f'ring-{ring}'
        variant.mkdir(exist_ok=False)
        start = time.time()
        status, failure = 'FAILED', None
        try:
            check = subprocess.run(['gpuq', 'gaming', 'check', '--quiet'])
            assert check.returncode in (0, 75), 'GPU coordinator state unavailable; inspect before bulk work'
            fixed = original[FILES[0]].decode()
            assert fixed.count('const RING: usize = 64;') == 1
            fixed = fixed.replace('const RING: usize = 64;', f'const RING: usize = {ring};')
            fixed = fixed.replace('At cur % 64 == 0', f'At cur % {ring} == 0')
            inner = original[FILES[1]].decode()
            assert inner.count('if next_index - next_ref < 64 {') == 1
            assert inner.count('ring_base.add(next_ref & 63)') == 1
            inner = inner.replace('if next_index - next_ref < 64 {', f'if next_index - next_ref < {ring} {{')
            inner = inner.replace('ring_base.add(next_ref & 63)', f'ring_base.add(next_ref & {ring - 1})')
            for name, contents in zip(FILES, (fixed, inner)):
                (ROOT / name).write_text(contents)
                saved = variant / name
                saved.parent.mkdir(parents=True, exist_ok=True)
                saved.write_text(contents)
            (variant / 'candidate.patch').write_bytes(subprocess.check_output(['git', 'diff', '--', *FILES]))
            run(['cargo', '+1.93.0', 'test', '--locked', '-p', 'blocknet-pow-kernel',
                 '--test', 'streaming_ring', '--', '--nocapture'], variant / 'boundary-tests.log', env, 300)
            run(['cargo', '+1.93.0', 'build', '--locked', '--release', '--no-default-features',
                 '--bin', 'seine'], variant / 'build.log', env, 600)
            run(['cargo', '+1.93.0', 'build', '--locked', '--release', '-p', 'blocknet-pow-kernel',
                 '--example', 'verify_streaming_dispatch'], variant / 'verifier-build.log', env, 300)
            shutil.copy2(target / 'release/seine', variant / 'seine')
            shutil.copy2(target / 'release/examples/verify_streaming_dispatch', variant / 'verify_streaming_dispatch')
            run([str(variant / 'verify_streaming_dispatch')], variant / 'reference-parity.log', env, 180)
            passes = [line for line in (variant / 'reference-parity.log').read_text().splitlines()
                      if line.startswith('PASS nonce=')]
            assert len(passes) == 21
            assert all('full_size_bytes=2147483648 dirty_reuse=true guards=true' in line for line in passes)
            boundary = (variant / 'boundary-tests.log').read_text()
            assert 'test result: ok. 1 passed' in boundary
            for kib in [12, 16, 17, 20, 28, 32, 33, 36]:
                assert f'memory={kib}: 3 nonces, dirty reuse, boundary guards PASS' in boundary
            status = 'COMPLETE'
        except BaseException as error:
            failure = repr(error)
            raise
        finally:
            for name, contents in original.items():
                (ROOT / name).write_bytes(contents)
            record = {'status': status, 'failure': failure, 'ring_blocks': ring,
                'ring_bytes_per_worker': ring * 1024, 'source_commit': source_commit,
                'kernel_source_base': BASE, 'source_restored': all((ROOT / n).read_bytes() == b for n, b in original.items()),
                'local_validation_only': True, 'elapsed_seconds': time.time() - start,
                'artifact_sha256': {p.name: digest(p) for p in variant.iterdir() if p.is_file()}}
            (variant / 'provenance.json').write_text(json.dumps(record, indent=2) + '\n')
            assert record['source_restored']
        print('Ring', ring, 'prepared with full-size parity; no native performance claim.', flush=True)


if __name__ == '__main__':
    main()
