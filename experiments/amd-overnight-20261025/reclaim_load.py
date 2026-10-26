#!/usr/bin/python3
"""Bounded test allocation inside an already-owned miner cgroup."""
import argparse
import json
import os
from pathlib import Path
import time


def inject(group, size, seconds):
    assert 0 < size <= 2 * 1024**3 and 0 < seconds <= 25
    (group / 'cgroup.procs').write_text(str(os.getpid()) + '\n')
    start = time.monotonic()
    chunks, committed = [], 0
    while time.monotonic() - start < seconds:
        if committed < size:
            chunk = bytearray(min(16 * 1024**2, size - committed))
            # calloc alone can leave demand-zero pages uncharged. Write every page.
            for offset in range(0, len(chunk), 4096):
                chunk[offset] = 1
            chunks.append(chunk)
            committed += len(chunk)
        else:
            time.sleep(.05)
    print(json.dumps({'pid': os.getpid(), 'bytes_touched': committed,
                      'elapsed_seconds': time.monotonic() - start}), flush=True)
    return committed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cgroup', type=Path, required=True)
    parser.add_argument('--bytes', type=int, default=2 * 1024**3)
    parser.add_argument('--seconds', type=float, default=20)
    args = parser.parse_args()
    inject(args.cgroup, args.bytes, args.seconds)
