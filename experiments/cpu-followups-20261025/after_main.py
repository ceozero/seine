#!/usr/bin/env python3
"""Wait without CPU load, then run alignment only within the existing lease."""
import argparse
import json
from pathlib import Path
import subprocess
import time


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--deadline', type=float, required=True)
    p.add_argument('--program', choices=['run_alignment.py', 'run_lifecycle.py'], default='run_alignment.py')
    p.add_argument('--minimum-remaining', type=int, default=1020)
    p.add_argument('--timeout', type=int, default=960)
    args = p.parse_args()
    root = Path(__file__).resolve().parent
    while True:
        remaining = args.deadline - time.time()
        if remaining < args.minimum_remaining:
            raise RuntimeError('Insufficient lease time for bounded follow-up test')
        state = subprocess.check_output(['systemctl', 'show', 'seine-followups-controller', '--property=ActiveState', '--value'], text=True).strip()
        if state not in ['active', 'activating', 'deactivating']:
            break
        time.sleep(15)
    assert json.loads((root.parent / 'results/outcome.json').read_text())['status'] == 'COMPLETE'
    print('Main controller complete; starting bounded ' + args.program, flush=True)
    subprocess.run(['python3', str(root / args.program)], cwd=root, check=True, timeout=args.timeout)


if __name__ == '__main__':
    main()
