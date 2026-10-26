#!/usr/bin/env python3
"""Run remaining hosts sequentially in the predeclared priority order.

Each host is a separate `campaign.py run` process (termination in its finally).
Stops launching once the conservative committed total would pass $28 (enforced
again inside cloud.launch). If m5.8xlarge lands on Cascade Lake (family 6,
model 85, stepping >= 5), r5.8xlarge is tried once for a true Skylake-SP.
"""
import json
from pathlib import Path
import subprocess
import sys
import time

import cloud

HERE = Path(__file__).resolve().parent
LOGS = cloud.ROOT / 'logs'


def done(label):
    return any(json.loads(p.read_text())['status'] == 'complete'
               for p in (cloud.ROOT / label).glob('attempt*/outcome.json'))


def next_attempt(label):
    return 1 + len(list((cloud.ROOT / label).glob('attempt*')))


def run(label):
    attempt = next_attempt(label)
    log = LOGS / f'{label}-attempt{attempt}.log'
    print('START', label, 'attempt', attempt, cloud.now().isoformat(), flush=True)
    with log.open('w') as f:
        code = subprocess.run([sys.executable, '-u', str(HERE / 'campaign.py'), 'run', label,
                               '--attempt', str(attempt)], stdout=f, stderr=subprocess.STDOUT).returncode
    tail = log.read_text().strip().splitlines()[-3:]
    print('END', label, 'exit', code, '|', ' / '.join(tail)[-400:], flush=True)
    # Keep summary.json current after every host (coordinator request).
    summary = subprocess.run([sys.executable, str(HERE / 'summarize.py')], capture_output=True, text=True)
    print('SUMMARY', summary.returncode, summary.stdout.strip().splitlines()[-2:] if summary.stdout else summary.stderr[-300:], flush=True)
    return code


def skylake_is_cascade(label):
    for p in sorted((cloud.ROOT / label).glob('attempt*/evidence/hardware.json')):
        hw = json.loads(p.read_text())
        return hw['cpu_family'] == '6' and hw['model'] == '85' and int(hw['stepping']) >= 5
    return None


def main():
    labels = sys.argv[1:]
    for label in labels:
        # Coordinator quota hand-offs: hold before any launch while HOLD exists.
        announced = False
        while (cloud.ROOT / 'HOLD').exists():
            if not announced:
                print('HOLD present; not launching', label, cloud.now().isoformat(), flush=True)
                announced = True
            time.sleep(20)
        force = label.endswith('!')  # explicit rerun of a completed host
        label = label.rstrip('!')
        if done(label) and not force:
            print('SKIP done', label, flush=True)
            continue
        s = cloud.ledger()
        if cloud.committed_usd(s) > cloud.BUDGET_STOP_USD - 1.5:
            print('BUDGET STOP before', label, cloud.committed_usd(s), flush=True)
            break
        code = run(label)
        if code and not done(label) and 'no capacity' in (LOGS / f'{label}-attempt{next_attempt(label) - 1}.log').read_text():
            print('NO CAPACITY', label, flush=True)
        if label == 'skylake' and done(label) and skylake_is_cascade(label):
            print('m5.8xlarge landed on Cascade Lake; trying r5.8xlarge once', flush=True)
            run('skylake-r5')
    print('QUEUE FINISHED', cloud.now().isoformat(), flush=True)


if __name__ == '__main__':
    main()
