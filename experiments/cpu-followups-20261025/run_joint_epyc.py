#!/usr/bin/env python3
"""Bounded native follow-up campaign on an exclusively owned disposable guest."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import time
from bench import paired, counters

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'results'
child = None
started = time.monotonic()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def run(name, argv, timeout):
    global child
    if time.monotonic() - started + timeout > 98 * 60:  # 105-minute takeover lease
        raise RuntimeError('insufficient bounded campaign time for ' + name)
    with (OUT / (name + '.log')).open('w') as log:
        child = subprocess.Popen(argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = child.wait(timeout=timeout)
            if code:
                raise RuntimeError(f'{name}: exit {code}')
        finally:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
                try: child.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=5)
            child = None


def memory_run(label, threshold, workers, hashes, kernel='avx512'):
    before = counters()
    run(label, ['/usr/bin/time', '-v', '-o', str(OUT / (label + '-time.txt')),
                str(ROOT / 'mine-reduced'), '2097152', str(hashes), str(threshold), kernel,
                '100' if threshold == 1 else '70', str(workers), '0'], 180)
    rows = [json.loads(line) for line in (OUT / (label + '.log')).read_text().splitlines()]
    assert len(rows) == workers + 1 and rows[-1]['type'] == 'summary'
    assert rows[-1]['hashes'] == workers * hashes and rows[-1]['hps'] > 0
    after = counters(); delta = {k: after[k]-before[k] for k in before}
    assert all(delta[k] == 0 for k in ('pswpin','pswpout','oom_kill')), delta
    assert 100 * delta['steal'] / max(1,delta['ticks']) < 2, delta
    save(OUT / (label + '-checks.json'), delta)
    return rows[-1]


def interrupt(signum, frame):
    raise InterruptedError(signum)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('host', choices=['epyc'])
    args = p.parse_args()
    OUT.mkdir(exist_ok=False)
    source = OUT / 'protocol-source'
    source.mkdir()
    for path in ROOT.glob('*.py'):
        shutil.copy2(path, source / path.name)
    os.chdir(ROOT)
    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGINT, interrupt)
    expected = json.loads((ROOT/'expected-binaries.json').read_text())
    for name, sha in expected.items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == sha, name
    save(OUT/'hardware.json', json.loads(subprocess.check_output(['lscpu','-J'],text=True)))
    assert subprocess.check_output(['systemctl','is-active','seine-expiry.timer'],text=True).strip() == 'active'
    (OUT/'timer.txt').write_text(subprocess.check_output(['systemctl','list-timers','seine-expiry.timer','--all'],text=True))
    pool = Path('/proc/sys/vm/nr_hugepages')
    assert int(pool.read_text()) == 0
    thp = Path('/sys/kernel/mm/transparent_hugepage/enabled')
    thp_before = thp.read_text()
    (OUT/'thp-before.txt').write_text(thp_before)
    status = 'FAILED'
    try:
        # Takeover scope (2026-10-25): PR50 joint tuning only. PR51 reduced-memory
        # parity/throughput phases were dropped after negative C5 and Ice Lake results.
        workers = '24' if args.host == 'epyc' else '12'
        # Cold A/B/B/A, then restart from each matching cold leg's own caches.
        order = [('control','a'),('candidate','a'),('candidate','b'),('control','b')]
        for binary, suffix in order:
            label = f'joint-{binary}-{suffix}'
            run(label,['python3','joint_probe.py','--binary',binary,'--label',label,'--seconds','900','--workers',workers],1020)
            assert (OUT/label/'COMPLETE').exists()
        for binary, suffix in order[::-1]:
            label = f'joint-warm-{binary}-{suffix}'
            cold = OUT/f'joint-{binary}-{suffix}'
            run(label,['python3','joint_probe.py','--binary',binary,'--label',label,'--seconds','180','--workers',workers,'--cache-source',str(cold)],300)
            assert (OUT/label/'COMPLETE').exists()
        for name, digest in expected.items():
            assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest, name
        status='COMPLETE'
    finally:
        # Services also have independent RuntimeMaxSec and the VM has a separate
        # expiry timer. Stop only our uniquely named units before releasing pages.
        for binary in ['control','candidate']:
            for suffix in ['a','b']:
                for warm in ['', 'warm-']:
                    subprocess.run(['sudo','systemctl','stop',f'seine-campaign-joint-{warm}{binary}-{suffix}.service'],capture_output=True,timeout=30)
        subprocess.run(['sudo','sysctl','-w','vm.nr_hugepages=0'],check=True,timeout=30)
        assert int(pool.read_text()) == 0
        save(OUT/'outcome.json',{'status':status,'elapsed_secs':time.monotonic()-started,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat()})
        manifest = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.rglob('*') if p.is_file()}
        save(ROOT/'result-manifest.json',manifest)
        subprocess.run(['tar','-czf','results.tar.gz','results','result-manifest.json','expected-binaries.json'],check=True,timeout=60)
    print(status,flush=True)


if __name__ == '__main__': main()
