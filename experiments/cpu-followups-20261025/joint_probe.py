#!/usr/bin/env python3
"""Observe default joint tuning against a loopback pool on an owned EC2 guest.

This measures bounded productive behavior including startup, rather than an
isolated kernel. Explicit 12/24-worker bounds protect the 32/64-GiB guests;
kernel selection remains automatic. Retain unsuccessful trajectories too.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import signal
import subprocess
import sys
import threading
import time

import resource_lifecycle as life
from screen import counters


def interrupted(signum, frame):
    raise InterruptedError(signum)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--seconds', type=int, default=900)
    parser.add_argument('--label', required=True)
    parser.add_argument("--cache-source", type=Path)
    parser.add_argument("--workers", type=int, choices=[12,24], default=12)
    args = parser.parse_args()
    assert 60 <= args.seconds <= 1200
    assert re.fullmatch(r'joint-[a-z0-9-]{1,30}', args.label)
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    out = life.ROOT / 'results' / args.label
    out.mkdir(parents=True, exist_ok=False)
    life.OUT = out
    if args.cache_source:
        import shutil
        seeds = list(args.cache_source.glob('tuning.json*'))
        assert seeds, 'no completed cold-run caches available'
        for seed in seeds:
            shutil.copy2(seed, out / seed.name)
    pool = Path('/proc/sys/vm/nr_hugepages')
    assert int(pool.read_text()) == 0
    memory = {line.split(':')[0]: int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines()}
    assert memory['Hugepagesize'] == 2048
    assert memory['MemAvailable'] * 1024 >= (29 if args.workers == 12 else 55) * 1024**3
    assert len(Path('/proc/swaps').read_text().splitlines()) == 1
    (out / 'hosts').write_text('127.0.0.1 localhost bntpool.com\n::1 localhost\n')
    unit = 'seine-campaign-' + args.label + '.service'
    log = out / 'miner.log'
    server = life.Server(('127.0.0.1', 3333), life.Fixture)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    samples = []
    observation_start = None
    stop_timing = {}
    before = counters()
    (out / 'identity.json').write_text(json.dumps({
        'binary_sha256': hashlib.sha256(args.binary.read_bytes()).hexdigest(),
        'binary': str(args.binary.resolve()), 'seconds': args.seconds,
        'meminfo_before': memory,
        'topology': life.command(['lscpu', '-J']),
        'scope': 'Natural productive convergence; warm runs copy only this binary previous cold cache.', 'cache_source': str(args.cache_source) if args.cache_source else None}, indent=2) + '\n')
    try:
        life.command(['sudo', 'sysctl', '-w', 'vm.nr_hugepages=' + str(args.workers * 1024)])
        assert int(pool.read_text()) == args.workers * 1024
        command = ['sudo', 'systemd-run', '--quiet', '--unit=' + unit, '--uid=ubuntu',
            '--property=Type=exec', '--property=TasksMax=96', '--property=MemoryHigh=' + ('28G' if args.workers == 12 else '56G'),
            '--property=MemoryMax=' + ('29G' if args.workers == 12 else '58G'), '--property=AllowedCPUs=' + ('0-15' if args.workers == 12 else '0-31'),
            '--property=RuntimeMaxSec=' + str(args.seconds + 60), '--property=TimeoutStopSec=20',
            '--property=KillSignal=SIGINT', '--property=IPAddressDeny=any',
            '--property=IPAddressAllow=localhost',
            '--property=BindReadOnlyPaths=' + str(out / 'hosts') + ':/etc/hosts',
            '--property=StandardOutput=append:' + str(log),
            '--property=StandardError=append:' + str(log),
            'taskset', '-c', ('0-15' if args.workers == 12 else '0-31'), str(args.binary.resolve()),
            '--mode', 'pool', '--pool-url', '127.0.0.1:3333', '--address', life.fixture_address(),
            '--backend', 'cpu', '--cpu-page-mode', 'large', '--cpu-affinity', 'auto',
            '--cpu-autotune-max-threads', str(args.workers),
            '--cpu-autotune-config', str(out / 'tuning.json'), '--data-dir', str(out / 'config'),
            '--ui', 'plain', '--stats-secs', '5']
        (out / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
        observation_start = time.monotonic()
        life.command(command)
        end = time.monotonic() + args.seconds
        while time.monotonic() < end:
            assert life.command(['systemctl', 'show', unit, '--property=ActiveState', '--value']).strip() == 'active'
            sample = life.state(unit)
            assert 'oom_kill 0' in sample['memory.events']
            group = Path('/sys/fs/cgroup') / sample['cgroup'].lstrip('/')
            sample['hugetlb'] = {p.name: p.read_text().strip() for p in group.glob('hugetlb.*') if p.is_file()}
            sample['meminfo'] = {line.split(':')[0]: int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines()}
            text = log.read_text(errors='replace') if log.exists() else ''
            sample['completed_hashes'] = max([0] + [int(n) for n in re.findall(r'\bhashes=(\d+)', text)])
            sample['thread_cpu_masks'] = {}
            for status in (Path('/proc') / str(sample['pid']) / 'task').glob('*/status'):
                try:
                    fields = dict(line.split(':', 1) for line in status.read_text().splitlines() if ':' in line)
                    sample['thread_cpu_masks'][status.parent.name] = fields['Cpus_allowed_list'].strip()
                except FileNotFoundError:
                    pass
            samples.append(sample)
            (out / 'samples.json').write_text(json.dumps(samples, indent=2) + '\n')
            time.sleep(min(10, max(0, end - time.monotonic())))
        text = log.read_text()
        assert 'quarantined' not in text.lower()
        assert any(e['method'] == 'login' for e in life.SERVER_EVENTS), 'no fixture login'
        hashes = max([0] + [int(n) for n in re.findall(r'\bhashes=(\d+)', text)])
        assert hashes > 0 and samples[-1]['completed_hashes'] > samples[0]['completed_hashes'], 'no productive observation'
        capacity = re.search(r'capacity=(\d+), (?:worker slots=(\d+), )?currently available=(\d+)', text)
        assert capacity and int(capacity[1]) == args.workers and int(capacity[3]) == args.workers, 'worker opportunity not provisioned'
        after = counters()
        delta = {key: after[key] - before[key] for key in before}
        assert all(delta[k] == 0 for k in ('pswpin', 'pswpout', 'oom_kill')), delta
        assert 100 * delta['cpu_steal'] / max(1, delta['cpu_total']) < 2, delta
        (out / 'observation.json').write_text(json.dumps({'completed_hashes': hashes,
            'initial_capacity_slots_available': [int(v) if v is not None else None for v in capacity.groups()],
            'vm_delta': delta, 'kernel_and_count_trajectory': 'miner.log and tuning.json*',
            'finding_crossover_required': False}, indent=2) + '\n')
    finally:
        primary_failure = sys.exc_info()[1]
        # A failed stop must not skip pool release or socket cleanup. Each
        # external command is bounded; the service and rental also expire.
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        cleanup_failures = []

        def stop_owned_unit():
            life.stop(unit)
            stop_timing['stopped_at_monotonic'] = time.monotonic()

        operations = [
            ('stop owned unit', stop_owned_unit),
            ('reset failed unit', lambda: subprocess.run(
                ['sudo', 'systemctl', 'reset-failed', unit], capture_output=True, timeout=30)),
            ('stop fixture', server.shutdown),
            ('close fixture', server.server_close),
            ('release hugepages', lambda: life.command(['sudo', 'sysctl', '-w', 'vm.nr_hugepages=0'])),
        ]
        for name, operation in operations:
            try:
                operation()
            except Exception as error:
                cleanup_failures.append(name + ': ' + repr(error))
        try:
            state = life.command(['systemctl', 'show', unit, '--property=ActiveState', '--value']).strip()
            assert state not in ('active', 'activating', 'deactivating'), state
            assert int(pool.read_text()) == 0
        except Exception as error:
            cleanup_failures.append('cleanup verification: ' + repr(error))
        (out / 'cleanup.json').write_text(json.dumps({'failures': cleanup_failures,
            'primary_failure': repr(primary_failure) if primary_failure else None}, indent=2) + '\n')
        (out / 'fixture-events.json').write_text(json.dumps(life.SERVER_EVENTS, indent=2) + '\n')
        if cleanup_failures:
            raise RuntimeError(cleanup_failures) from primary_failure
    final_hashes = max([0] + [int(n) for n in re.findall(r'\bhashes=(\d+)', log.read_text())])
    elapsed = stop_timing['stopped_at_monotonic'] - observation_start
    (out / 'productive-window.json').write_text(json.dumps({
        'completed_hashes_lower_bound': final_hashes,
        'elapsed_start_request_through_stopped_seconds': elapsed,
        'completed_hps_lower_bound': final_hashes / elapsed,
        'scope': ('Cached-restart' if args.cache_source else 'Cold-cache') + ' real pool runtime including startup, productive trials and shutdown; log counters may omit final unreported hashes. Not a fixed-kernel throughput benchmark.'}, indent=2) + '\n')
    (out / 'COMPLETE').write_text(datetime.datetime.now(datetime.timezone.utc).isoformat() + '\n')
    print(args.label, 'complete; owned service stopped and hugepage pool released', flush=True)


if __name__ == '__main__':
    main()
