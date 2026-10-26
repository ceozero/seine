#!/usr/bin/env python3
"""Short diagnostic profile with bounded, read-only HSMP observations."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parent
HSMP = Path('/sys/devices/platform/AMDI0097:00')
EVENTS = ('cycles', 'instructions', 'l2_cache_req_stat.dc_access_in_l2',
          'l2_cache_req_stat.ls_rd_blk_c')
UNITS = {'ddr_max_bw': 'GB/s', 'ddr_utilised_bw_input': 'GB/s',
         'ddr_utilised_bw_perc_input': 'percent', 'mclk_input': 'MHz',
         'fclk_input': 'MHz', 'prochot_status': 'boolean',
         'cclk_freq_limit_input': 'MHz', 'pwr_current_active_freq_limit_source': 'text'}


def write(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def sample():
    result = {'monotonic_before': time.monotonic(), 'epoch': time.time(), 'values': {}, 'errors': {}}
    for field in UNITS:
        try:
            result['values'][field] = (HSMP / field).read_text().strip()
        except OSError as error:
            result['errors'][field] = repr(error)
    result['monotonic_after'] = time.monotonic()
    return result


def interrupted(signum, frame):
    raise InterruptedError(signum)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers', type=int, choices=(32, 64), required=True)
    args = parser.parse_args()
    prefix = ROOT / 'results' / ('profile-control-' + str(args.workers))
    command = ['perf', 'stat', '--json-output', '-o', str(prefix) + '-perf.json',
        '-e', '{' + ','.join(event + ':u' for event in EVENTS) + '}', '--',
        str(ROOT / 'ring-64'), '--bench', '--bench-kind', 'end-to-end', '--backend', 'cpu',
        '--threads', str(args.workers), '--cpu-page-mode', 'large', '--cpu-affinity', 'auto',
        '--bench-cpu-kernel', 'avx512-256-stream', '--disable-cpu-autotune-threads',
        '--ui', 'plain', '--bench-secs', '30', '--bench-rounds', '1', '--bench-warmup-rounds', '0',
        '--bench-output', str(prefix) + '-bench.json', '--data-dir', str(ROOT / 'config')]
    output = Path(str(prefix) + '-hsmp.json')
    assert not output.exists(), 'never overwrite diagnostic evidence'
    record = {'command': command, 'units': UNITS, 'samples': [],
        'sampling_interval_seconds': 2, 'scope': 'Whole benchmark invocation; no uncounted warmup.',
        'limitations': 'Firmware current-bandwidth estimates in integer GB/s. Separate sysfs reads are not atomic, and averages are not integrated byte counts. No claims about precise bytes per hash.',
        'documentation': 'https://docs.kernel.org/arch/x86/amd_hsmp.html'}
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    child = None
    try:
        record['samples'].append(sample())
        child = subprocess.Popen(command, start_new_session=True)
        deadline = time.monotonic() + 110
        while True:
            assert time.monotonic() < deadline, 'profile exceeded timeout'
            try:
                code = child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                code = None
            record['samples'].append(sample())
            write(output, record)
            if code is not None:
                record['exit_code'] = code
                return code
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGINT)
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=5)
        write(output, record)


if __name__ == '__main__':
    raise SystemExit(main())
