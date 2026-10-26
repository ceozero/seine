#!/usr/bin/env python3
"""Drive one README benchmark host end to end: launch spot -> verify timer ->
upload frozen bundle -> run hostrun.py -> collect + SHA256-verify -> terminate
and verify instance + root-volume deletion. Termination runs in `finally`.

    python3 campaign.py run <label>      # one host
    python3 campaign.py audit            # tag-scoped audit
    python3 campaign.py cleanup          # SG + local key removal, final audit
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import sys
import tarfile
import time
import traceback

import cloud

HERE = Path(__file__).resolve().parent
ROOT = cloud.ROOT
RELEASE_COMMIT = '6e5411768d5d67365ecaff3abc30d280fb30cb0d'
F20_COMMIT = 'f20e7bb1772be024a12ac5cdcc92685ba89d3ddd'
VERIFIER_X86_COMMIT = '4f5fec9119fdfe6c9d24608fe9bc2a42eec49b4f'

HOSTS = {  # label: (preferred type, arch, fallback type if preferred has no capacity)
    'zen1-naples': ('m5a.8xlarge', 'amd64', None), 'zen2-rome': ('c5a.8xlarge', 'amd64', None),
    'zen3-milan': ('c6a.8xlarge', 'amd64', None),
    'zen4-genoa': ('m7a.8xlarge', 'amd64', 'c7a.8xlarge'), 'zen5-turin': ('m8a.8xlarge', 'amd64', 'c8a.8xlarge'),
    'broadwell': ('r4.8xlarge', 'amd64', None),
    'skylake': ('m5.8xlarge', 'amd64', None), 'skylake-r5': ('r5.8xlarge', 'amd64', None),
    'cascadelake': ('m5n.8xlarge', 'amd64', None), 'icelake': ('c6i.8xlarge', 'amd64', None),
    'sapphirerapids': ('c7i.8xlarge', 'amd64', None), 'graniterapids': ('c8i.8xlarge', 'amd64', None),
    # 128 GiB reruns for SMT Intel hosts whose best cell sat at the 64 GiB thread cap.
    'sapphirerapids-m7i': ('m7i.8xlarge', 'amd64', None), 'icelake-m6i': ('m6i.8xlarge', 'amd64', None),
    'graniterapids-m8i': ('m8i.8xlarge', 'amd64', None),
    'graviton2': ('m6g.8xlarge', 'arm64', 'c6g.8xlarge'), 'graviton3': ('m7g.8xlarge', 'arm64', 'c7g.8xlarge'),
    'graviton4': ('m8g.8xlarge', 'arm64', 'c8g.8xlarge'),
}

X86_FILES = {'seine-v022': ROOT / 'release/x-x86_64/seine',
             'verify-v022-x86': Path('/home/zp/Code/blocknet/seine-high-end-streaming/data/'
                                     'high-end-streaming-20261025/genoa-v022/artifacts/verify_cpu_kernels')}
ARM_FILES = {'seine-v022-arm': ROOT / 'release/x-aarch64/seine',
             'seine-f20-arm': Path('/home/zp/Code/blocknet/seine-architecture-campaign/data/cpu-campaign-20261024/'
                                   'portable-codegen-arm/seine-arm-candidate'),
             'verify-f20-arm': Path('/home/zp/Code/blocknet/seine-architecture-campaign/data/cpu-campaign-20261024/'
                                    'portable-codegen-arm/verify-arm-candidate')}
EXPECTED = {  # independently recorded digests
    'seine-v022': 'd336f33f6f610b868a2f0f6ccedfa7316481c62fb4e209db4a8b5d891a6df260',
    'verify-v022-x86': '8e1e21ea79e5784b05787164e3ee647aca260545588f828d4dbd121d2f969b1b',
    'seine-v022-arm': '347195791061cc0820628517e5f9f5097b7b1d0ab1ebeefb9b11817f0d117021',
    'seine-f20-arm': '4e4b0bbdba495a44d7605a2bbc453b4f1d6d6761e1374761835a2de2fa74455e',
    'verify-f20-arm': 'bfb079866282221bd0c1ea0cbe06a9512b0ff1279b33be1f1468ddc6579847ce',
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def host_config(label, arch):
    if arch == 'amd64':
        files = dict(X86_FILES)
        variants = [{'name': f'v022-{k}', 'binary': 'seine-v022', 'kernel': k}
                    for k in ('avx2', 'avx512', 'avx512-256-stream')]
        verifiers = [{'file': 'verify-v022-x86', 'covers': ['seine-v022'],
                      'provenance': f'frozen verify_cpu_kernels built at {VERIFIER_X86_COMMIT}; '
                                    'pow-kernel/pow-spec trees identical to v0.2.22'}]
        conditional = []
        build = False
    else:
        files = dict(ARM_FILES)
        frozen = ROOT / 'bundle/verify-v022-arm'
        build = not frozen.exists()
        if build:
            files['v022-source.tar'] = ROOT / 'bundle/v022-source.tar'
        else:
            files['verify-v022-arm'] = frozen
            EXPECTED['verify-v022-arm'] = json.loads((ROOT / 'bundle/verify-v022-arm-provenance.json').read_text())['sha256']
        variants = [{'name': 'v022-neon', 'binary': 'seine-v022-arm', 'kernel': 'neon'},
                    {'name': 'f20-neon-sha3', 'binary': 'seine-f20-arm', 'kernel': 'neon-sha3'}]
        conditional = [{'name': 'f20-neon', 'binary': 'seine-f20-arm', 'kernel': 'neon',
                        'when_missing': 'f20-neon-sha3'}]
        verifiers = [{'file': 'verify-v022-arm', 'covers': ['seine-v022-arm'],
                      'provenance': f'verify_cpu_kernels from v0.2.22 source {RELEASE_COMMIT}, native build'},
                     {'file': 'verify-f20-arm', 'covers': ['seine-f20-arm'],
                      'provenance': f'frozen portable-codegen-arm verify_neon_dispatch (full-size RustCrypto reference parity, 3 nonces, dirty-arena neon/neon-sha3 switches), source {F20_COMMIT}'}]
    digests = {}
    for name, path in files.items():
        digest = sha256(path)
        if name in EXPECTED:
            assert digest == EXPECTED[name], (name, digest)
        digests[name] = digest
    digests['hostrun.py'] = sha256(HERE / 'hostrun.py')
    config = {'label': label, 'arch': arch, 'release_commit': RELEASE_COMMIT, 'variants': variants,
              'conditional_variants': conditional, 'verifiers': verifiers, 'build_v022_verifier': build,
              'sha256': digests}
    return files, config


def collect(ip, label, attempt):
    """Archive the guest bundle (minus binaries), download, verify every file."""
    code = r"""import hashlib,json,pathlib,tarfile,sys
root=pathlib.Path('/home/ubuntu/rh')
skip={'seine-v022','seine-v022-arm','seine-f20-arm','verify-v022-x86','verify-f20-arm','v022-source.tar'}
manifest={}
files=[]
for f in sorted(root.rglob('*')):
  rel=f.relative_to(root)
  if f.is_file() and not f.is_symlink() and rel.parts[0] not in skip and rel.parts[0]!='build-v022' and not str(rel).startswith('evidence.tar.gz'):
    manifest[str(rel)]=hashlib.sha256(f.read_bytes()).hexdigest(); files.append(rel)
(root/'evidence.tar.gz.manifest.json').write_text(json.dumps(manifest,indent=1))
with tarfile.open(root/'evidence.tar.gz','w:gz') as t:
  for rel in files+[pathlib.Path('evidence.tar.gz.manifest.json')]: t.add(root/rel,arcname=str(rel))
print(json.dumps({'sha256':hashlib.sha256((root/'evidence.tar.gz').read_bytes()).hexdigest(),'files':len(manifest)}))
"""
    expected = json.loads(cloud.ssh(ip, 'python3 -c ' + shlex.quote(code), timeout=180).strip().splitlines()[-1])
    dest = ROOT / label / f'attempt{attempt}'
    dest.mkdir(parents=True, exist_ok=True)
    archive = dest / 'evidence.tar.gz'
    cloud.scp(ip, '/home/ubuntu/rh/evidence.tar.gz', str(archive), download=True)
    assert sha256(archive) == expected['sha256'], 'archive digest mismatch'
    out = dest / 'evidence'
    out.mkdir(exist_ok=False)
    with tarfile.open(archive) as t:
        assert all((m.isfile() or m.isdir()) and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
                   for m in t.getmembers())
        t.extractall(out)
    manifest = json.loads((out / 'evidence.tar.gz.manifest.json').read_text())
    for f, digest in manifest.items():
        assert sha256(out / f) == digest, f
    # A natively built ARM verifier is frozen for later Graviton hosts.
    built = out / 'verify-v022-arm'
    if built.exists() and not (ROOT / 'bundle/verify-v022-arm').exists():
        prov = json.loads((out / 'verify-v022-arm-provenance.json').read_text())
        assert sha256(built) == prov['sha256']
        (ROOT / 'bundle').mkdir(exist_ok=True)
        (ROOT / 'bundle/verify-v022-arm').write_bytes(built.read_bytes())
        (ROOT / 'bundle/verify-v022-arm').chmod(0o755)
        (ROOT / 'bundle/verify-v022-arm-provenance.json').write_text(json.dumps(prov | {'frozen_from': label}, indent=2))
    result = expected | {'archive': str(archive.relative_to(ROOT)), 'every_file_verified': True,
                         'verified_at': cloud.now().isoformat()}
    cloud.save(dest / 'collection-verification.json', result)
    return result


def run(label, attempt):
    instance_type, arch, fallback = HOSTS[label]
    files, config = host_config(label, arch)
    hostdir = ROOT / label
    hostdir.mkdir(parents=True, exist_ok=True)
    stage = hostdir / f'attempt{attempt}' / 'upload'
    stage.mkdir(parents=True, exist_ok=False)
    for name, path in files.items():
        (stage / name).write_bytes(Path(path).read_bytes())
        (stage / name).chmod(0o755)
    (stage / 'hostrun.py').write_text((HERE / 'hostrun.py').read_text())
    cloud.save(stage / 'host-config.json', config)
    (ROOT / 'known-hosts').unlink(missing_ok=True)  # IPs are recycled between leases
    if cloud.ledger().get('spot_blocked'):
        # On-demand fallback only while the shared on-demand quota is actually free.
        waited = time.monotonic()
        while not (q := cloud.quota_room('on-demand', 32))['fits']:
            assert time.monotonic() - waited < 4 * 3600, 'on-demand quota never became free'
            print('waiting for free on-demand quota', json.dumps(q), cloud.now().isoformat(), flush=True)
            time.sleep(120)
    try:
        record = cloud.launch(label, instance_type, arch)
    except RuntimeError as error:
        if not fallback or 'no capacity' not in str(error):
            raise
        print('preferred type unavailable; falling back to', fallback, str(error)[:300], flush=True)
        record = cloud.launch(label, fallback, arch)
    ident = record['instance_id']
    print('launched', json.dumps({k: record[k] for k in ('instance_id', 'lifecycle', 'zone',
          'spot_price_at_launch_usd_per_hour', 'ondemand_usd_per_hour')}), flush=True)
    outcome = {'label': label, 'attempt': attempt, 'instance_id': ident, 'status': 'started'}
    try:
        rec = cloud.ready(ident)
        ip = rec['ip']
        print('timer verified', rec['timer_evidence'].replace('\n', ' '), flush=True)
        cloud.ssh(ip, 'mkdir -p /home/ubuntu/rh')
        cloud.scp(ip, str(stage) + '/.', '/home/ubuntu/rh/')
        cloud.ssh(ip, 'cd /home/ubuntu/rh && chmod +x seine* verify* 2>/dev/null; '
                      'setsid nohup python3 hostrun.py > driver.log 2>&1 < /dev/null & echo started')
        last = ''
        while True:
            time.sleep(30)
            try:
                state = cloud.owned_info(ident)['State']['Name']
            except RuntimeError as error:
                print('describe failed', error, flush=True)
                continue
            if state != 'running':
                outcome['status'] = f'instance {state} during run'
                raise RuntimeError(outcome['status'])
            try:
                text = cloud.ssh(ip, 'cd /home/ubuntu/rh; ls COMPLETE FAILED 2>/dev/null; tail -n 3 driver.log', timeout=60)
            except (RuntimeError, Exception) as error:
                print('poll failed', repr(error)[:200], flush=True)
                continue
            tail = text.strip()
            if tail != last:
                print(tail.splitlines()[-1] if tail else '', flush=True)
                last = tail
            if text.startswith('COMPLETE') or text.startswith('FAILED') or '\nCOMPLETE' in text or '\nFAILED' in text:
                break
            if time.time() > rec['shutdown_at_unix'] - 4 * 60:
                outcome['status'] = 'guest deadline reached before completion'
                break
        result = collect(ip, label, attempt)
        outcome.update(collection=result)
        ev = hostdir / f'attempt{attempt}' / 'evidence'
        outcome['status'] = 'complete' if (ev / 'COMPLETE').exists() else 'failed-on-guest'
    except BaseException as error:
        outcome.setdefault('error', repr(error))
        outcome['traceback'] = traceback.format_exc()
        if outcome['status'] == 'started':
            outcome['status'] = 'error'
        try:
            if 'ip' in locals():
                outcome['late_collection'] = collect(ip, label, attempt)
        except BaseException as error2:
            outcome['late_collection_error'] = repr(error2)
    finally:
        rec = cloud.terminate(ident)
        outcome['termination'] = {k: rec.get(k) for k in ('verified_terminated_at', 'terminated', 'volumes_deleted',
                                                          'volume_ids', 'cost', 'spot_request_final')}
        cloud.save(hostdir / f'attempt{attempt}' / 'outcome.json', outcome)
        print('terminated+verified', json.dumps(outcome['termination']['cost']), flush=True)
        s = cloud.ledger()
        print('committed conservative USD', round(cloud.committed_usd(s), 4), flush=True)
    print('OUTCOME', outcome['status'], flush=True)
    return outcome


def main():
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['run', 'audit', 'cleanup', 'ledger'])
    p.add_argument('label', nargs='?')
    p.add_argument('--attempt', type=int, default=1)
    a = p.parse_args()
    if a.action == 'run':
        run(a.label, a.attempt)
    elif a.action == 'audit':
        print(json.dumps(cloud.audit(), indent=2))
    elif a.action == 'cleanup':
        print(json.dumps(cloud.cleanup(), indent=2))
    else:
        s = cloud.ledger()
        print(json.dumps({'committed_conservative_usd': cloud.committed_usd(s),
                          'leases': [{k: r.get(k) for k in ('label', 'instance_id', 'lifecycle', 'cost')} for r in s['leases']]},
                         indent=2))


if __name__ == '__main__':
    main()
