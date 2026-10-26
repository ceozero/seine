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
    if time.monotonic() - started + timeout > 112 * 60:
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
    p.add_argument('host', choices=['intel','skylake','epyc'])
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
        run('reduced-parity', [str(ROOT/'test-reduced'),'full_size_reduced_memory_parity','--ignored','--nocapture'], 180)
        parity = (OUT/'reduced-parity.log').read_text()
        assert parity.count('FULL_PARITY') == 6 and '1 passed; 0 failed' in parity
        if args.host == 'epyc':
            # The wide memory comparison uses 256-bit paths, whereas preferred()
            # in the full-size unit test may select full-width AVX-512. Verify
            # each exact wide path against RustCrypto outside every RSS sample.
            for threshold, kernel in [(0,'avx512-256-stream'),(2,'avx512-256'),(3,'avx512-256')]:
                name = 'wide-parity-t' + str(threshold)
                run(name, [str(ROOT/'mine-reduced'),'2097152','1',str(threshold),kernel,'70','1','1'],180)
                rows = [json.loads(line) for line in (OUT/(name+'.log')).read_text().splitlines()]
                assert len(rows) == 2 and rows[0]['verified'] is True
        if args.host == 'intel':
            subprocess.run(['sudo','sysctl','-w','vm.nr_hugepages=12288'],check=True)
            assert int(pool.read_text()) == 12288
            for kernel in ['avx2','avx512']:
                paired(ROOT, OUT/('legacy-'+kernel), {'binary':'baseline21','kernel':kernel}, {'binary':'arm-ungated','kernel':kernel},12,pairs=2,seconds=15,rounds=1,warmup=1)
                paired(ROOT, OUT/('enum-'+kernel), {'binary':'arm-ungated','kernel':kernel}, {'binary':'arm-gated','kernel':kernel},12,pairs=4,seconds=15,rounds=1,warmup=1)
                paired(ROOT, OUT/('joint-fixed-'+kernel), {'binary':'control','kernel':kernel}, {'binary':'candidate','kernel':kernel},12,pairs=2,seconds=15,rounds=1,warmup=1)
            subprocess.run(['sudo','sysctl','-w','vm.nr_hugepages=0'],check=True)
        if args.host == 'skylake':
            subprocess.run(['sudo','sysctl','-w','vm.nr_hugepages=12288'],check=True)
            assert int(pool.read_text()) == 12288
            for workers in [8,12]:
                paired(ROOT, OUT/('crossover-w'+str(workers)), {'binary':'control','kernel':'avx512'}, {'binary':'control','kernel':'avx2'},workers,pairs=3,seconds=15,rounds=1,warmup=1)
            for kernel in ['avx2','avx512']:
                paired(ROOT, OUT/('joint-fixed-'+kernel), {'binary':'control','kernel':kernel}, {'binary':'candidate','kernel':kernel},12,pairs=2,seconds=15,rounds=1,warmup=1)
            subprocess.run(['sudo','sysctl','-w','vm.nr_hugepages=0'],check=True)
        # Reduced buffers use ordinary allocator pages; measure the full-arena
        # prototype under the same backing policy, recording process max RSS.
        subprocess.run(['sudo','sh','-c','echo never > /sys/kernel/mm/transparent_hugepage/enabled'],check=True)
        assert '[never]' in thp.read_text()
        memory = []
        for repeat in range(4):
            # Threshold 1 retains every block: isolate prototype bookkeeping
            # overhead from recomputation on the final EPYC host. The already
            # running Intel protocol remains [0,2,3].
            thresholds = [0,1,2,3] if args.host == 'epyc' else [0,2,3]
            order = thresholds if repeat % 2 == 0 else thresholds[::-1]
            for threshold in order:
                memory.append({'repeat':repeat,'threshold':threshold,'result':memory_run(f'memory-r{repeat}-t{threshold}',threshold,1,3)})
        if args.host == 'epyc':
            for repeat in range(4):
                cases = [(0,24,'avx512-256-stream'),(2,32,'avx512-256'),(3,32,'avx512-256')]
                if repeat % 2: cases.reverse()
                for threshold,workers,kernel in cases:
                    memory.append({'repeat':repeat,'threshold':threshold,'workers':workers,'result':memory_run(f'memory-wide-r{repeat}-t{threshold}',threshold,workers,32,kernel)})
        save(OUT/'memory-results.json',memory)
        mode = thp_before.split('[')[1].split(']')[0]
        subprocess.run(['sudo','sh','-c',f'echo {mode} > /sys/kernel/mm/transparent_hugepage/enabled'],check=True)
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
