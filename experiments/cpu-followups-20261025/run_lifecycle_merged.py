#!/usr/bin/env python3
"""Fresh-host rerun of the native RAM/load/restart checks on the merged PR50 build.

Takeover variant (2026-10-25): no main timing controller precedes it, so the
main-outcome precondition is dropped. Binary is master+PR50 merge 211657d,
which includes PR43's capacity recovery.
"""
import hashlib
import json
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'results'


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def interrupt(signum, frame):
    raise InterruptedError(signum)


def main():
    OUT.mkdir(exist_ok=False)
    (OUT/'protocol-source').mkdir()
    for name in ['run_lifecycle_merged.py', 'lifecycle_source.py']:
        shutil.copy2(ROOT/name, OUT/'protocol-source'/name)
    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGINT, interrupt)
    expected = json.loads((ROOT.parent/'expected-binaries.json').read_text())['candidate']
    binary = ROOT.parent/'candidate'
    assert hashlib.sha256(binary.read_bytes()).hexdigest() == expected
    assert int(Path('/proc/sys/vm/nr_hugepages').read_text()) == 0
    sys.path.insert(0, str(ROOT.parent))
    from bench import counters
    before = counters()
    started = time.monotonic()
    status = 'FAILED'
    save(OUT/'protocol.json', {'binary_sha256': expected, 'source': '211657d (master + PR50 merge, includes PR43)',
        'harness': 'Established resource_lifecycle.py copied as lifecycle_source.py',
        'initial_seconds': 360, 'page_mode': 'regular', 'cpus': '0-3',
        'scope': 'Real RAM budget reduction to one/zero arenas, recovery, CPU contention, constrained cached restart and opt-out; not a speed benchmark.'})
    try:
        with (OUT/'controller.log').open('w') as log:
            subprocess.run(['python3',str(ROOT/'lifecycle_source.py'),'--binary',str(binary),
                '--initial-seconds','360','--page','regular','--cpus','0-3'],
                cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=990)
        assert (OUT/'lifecycle/COMPLETE').exists()
        after = counters()
        diff = {k: after[k]-before[k] for k in before}
        assert all(diff[k] == 0 for k in ['pswpin','pswpout','oom_kill']), diff
        save(OUT/'vm-checks.json',diff)
        assert hashlib.sha256(binary.read_bytes()).hexdigest() == expected
        status = 'COMPLETE'
    finally:
        failures = []
        for name in ['cpu-load','lifecycle-optout','lifecycle-restart','lifecycle-first']:
            unit = 'seine-campaign-' + name + '.service'
            subprocess.run(['sudo','systemctl','stop',unit],capture_output=True,timeout=30)
            state = subprocess.check_output(['systemctl','show',unit,'--property=ActiveState','--value'],text=True).strip()
            if state in ['active','activating','deactivating']: failures.append(unit)
        assert int(Path('/proc/sys/vm/nr_hugepages').read_text()) == 0
        save(OUT/'outcome.json',{'status':status,'elapsed_secs':time.monotonic()-started,'cleanup_failures':failures})
        save(ROOT/'result-manifest.json',{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.rglob('*') if p.is_file()})
        subprocess.run(['tar','-czf','results.tar.gz','results','result-manifest.json','run_lifecycle_merged.py','lifecycle_source.py'],cwd=ROOT,check=True,timeout=60)
        assert not failures, failures
    print(status,flush=True)


if __name__ == '__main__':
    main()
