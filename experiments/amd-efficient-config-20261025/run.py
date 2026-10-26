#!/usr/bin/python3
"""Bounded comparison of two page/power configurations after all prior work is collected."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

from compare_energy import compare, expected_pool_state, PAGE_MODES, POWER_CAPS_UW

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'results'
CAP = Path('/sys/devices/platform/AMDI0097:00/hwmon/hwmon4/power1_cap')
POOLS = {mode: Path('/sys/kernel/mm/hugepages') / directory for mode, directory in (
    ('large', 'hugepages-2048kB'), ('large-1g', 'hugepages-1048576kB'))}
GOAL_DEADLINE = dt.datetime.fromisoformat('2026-10-25T18:42:52+00:00').timestamp()
PROVIDER_DEADLINE = dt.datetime.fromisoformat('2026-10-25T18:25:00+00:00').timestamp()


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def pools():
    return {mode: {key: int((folder / filename).read_text()) for key, filename in (
        ('total', 'nr_hugepages'), ('free', 'free_hugepages'),
        ('reserved', 'resv_hugepages'), ('surplus', 'surplus_hugepages'))}
        for mode, folder in POOLS.items()}


def vm_counters():
    values = dict(line.split() for line in Path('/proc/vmstat').read_text().splitlines())
    return {key: int(values[key]) for key in ('pswpin', 'pswpout', 'oom_kill')}


def validate_admission(authorization, handoff, active_units, now, deadline):
    assert authorization['server_id'] == 1043469 and authorization['ledger_extension_recorded'] is True
    assert authorization['controller_deadline_epoch'] == deadline and now + 1800 + 180 < deadline
    assert deadline + 600 <= authorization['provider_delete_before_epoch'] <= min(
        GOAL_DEADLINE, PROVIDER_DEADLINE, authorization['funded_until_epoch'])
    assert 0 < authorization['total_reserved_usd'] <= 25
    assert handoff['experiments_finished'] is True
    for campaign in ('amd-overnight-20261025', 'amd-ring-locality-20261025',
                     'amd-page-size-20261025', 'amd-trial-windows-20261025'):
        record = handoff['verified_collections'][campaign]
        assert re.fullmatch(r'[0-9a-f]{64}', record['archive_sha256'])
        assert record['verified_manifest_entries'] > 0 and record['settings_restored'] is True
    assert all(line.split()[0] == 'seine-amd-efficient-config.service'
               for line in active_units.splitlines() if line.strip()), active_units


def run(label, command, timeout, deadline=None, required=True):
    if deadline is not None:
        assert time.time() + timeout + 180 < deadline, 'insufficient time for ' + label
    save(OUT / 'progress.json', {'phase': label, 'at_epoch': time.time()})
    with (OUT / (label + '.log')).open('w') as log:
        child = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                 start_new_session=True)
        try:
            code = child.wait(timeout=timeout)
            assert not required or code == 0, label + ' failed'
        finally:
            if child.poll() is None:
                try:
                    os.killpg(child.pid, signal.SIGINT)
                except ProcessLookupError:
                    pass
                try:
                    child.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    child.wait(timeout=10)
    return code


def set_pool(label, mode, count, deadline=None, required=True):
    return run(label, [sys.executable, '-c',
        'from pathlib import Path; import sys; Path(sys.argv[1]).write_text(sys.argv[2]+"\\n")',
        str(POOLS[mode] / 'nr_hugepages'), str(count)], 60, deadline, required)


def empty_pools(label, deadline=None):
    for mode in POOLS:
        set_pool(label + '-' + mode, mode, 0, deadline)
    assert all(all(value == 0 for value in state.values()) for state in pools().values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deadline-epoch', type=float, required=True)
    args = parser.parse_args()
    assert os.geteuid() == 0
    authorization = json.loads((ROOT / 'run-authorization.json').read_text())
    handoff = json.loads((ROOT / 'prior-evidence-collected.json').read_text())
    active = subprocess.check_output(['systemctl', 'list-units', '--type=service',
        '--state=active,activating,deactivating,reloading', '--no-legend', '--plain',
        'seine-amd-*', 'seine-overnight-*', 'seine-short-windows-*', 'seine-cherry-*'],
        text=True, timeout=30)
    validate_admission(authorization, handoff, active, time.time(), args.deadline_epoch)
    hardware = {entry['field'].rstrip(':'): entry['data'] for entry in json.loads(
        subprocess.check_output(['lscpu', '-J'], text=True))['lscpu']}
    assert (hardware['Vendor ID'], int(hardware['CPU family']), int(hardware['Model'])) == ('AuthenticAMD', 26, 2)
    assert int(hardware['CPU(s)']) == 64 and int(hardware['Socket(s)']) == 1 and int(hardware['NUMA node(s)']) == 1
    assert int(CAP.read_text()) == 280_000_000
    original = pools()
    assert all(all(value == 0 for value in state.values()) for state in original.values())
    swaps = Path('/proc/swaps').read_text().splitlines()
    assert len(swaps) == 2 and swaps[1].split()[0] == '/swap.img' and int(swaps[1].split()[3]) == 0
    expected = json.loads((ROOT / 'expected-files.json').read_text())
    for name, digest in expected.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    OUT.mkdir(exist_ok=False)
    def interrupt(signum, frame):
        raise InterruptedError(signum)
    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGINT, interrupt)
    save(OUT / 'protocol.json', {'hardware': hardware, 'binary_sha256': expected['miner'],
        'verifier_sha256': expected['verify_streaming_1g'], 'page_modes': PAGE_MODES,
        'workers': 64, 'pairs': 4, 'seconds': 120, 'warmup_rounds': 0,
        'pool_settle_seconds': 10, 'original_pools': original, 'original_swaps': swaps,
        'power_caps_uw': POWER_CAPS_UW, 'original_cap_uw': 280_000_000, 'deadline_epoch': args.deadline_epoch})
    status, failure = 'FAILED', None
    before_vm = vm_counters()
    try:
        run('swapoff', ['swapoff', '/swap.img'], 30, args.deadline_epoch)
        code = set_pool('one-gib-feasibility', 'large-1g', 128, args.deadline_epoch, required=False)
        observed = pools()
        save(OUT / 'allocation-feasibility.json', {'returncode': code, 'requested_one_gib_pages': 128,
                                                  'observed': observed})
        if code != 0 or observed != expected_pool_state('large-1g'):
            status = 'UNAVAILABLE'
            return
        run('one-gib-reference-parity', [str(ROOT / 'verify_streaming_1g')], 180, args.deadline_epoch)
        parity = (OUT / 'one-gib-reference-parity.log').read_text().splitlines()
        assert any('kernel_page_size_kib=1048576' in line for line in parity)
        passes = [line for line in parity if line.startswith('PASS nonce=')]
        assert len(passes) == 21 and all('backing=large-1g full_size_bytes=2147483648 dirty_reuse=true guards=true' in line for line in passes)
        assert pools() == expected_pool_state('large-1g')
        for pair in range(1, 5):
            for role in (('baseline', 'candidate') if pair % 2 else ('candidate', 'baseline')):
                label, mode = f'pair-{pair:02d}-{role}', PAGE_MODES[role]
                empty_pools(label + '-empty', args.deadline_epoch)
                set_pool(label + '-reserve', mode, 65536 if mode == 'large' else 128, args.deadline_epoch)
                assert pools() == expected_pool_state(mode)
                CAP.write_text(str(POWER_CAPS_UW[role]) + '\n')
                assert int(CAP.read_text()) == POWER_CAPS_UW[role]
                time.sleep(10)
                before, cap_before = pools(), int(CAP.read_text())
                assert cap_before == POWER_CAPS_UW[role]
                run(label, [sys.executable, '-B', str(ROOT / 'bench_cpu_energy.py'), 'run',
                    '--binary', str(ROOT / 'miner'), '--threads', '64', '--page-mode', mode,
                    '--kernel', 'avx512-256-stream', '--seconds', '120', '--rounds', '1',
                    '--interval', '0.25', '--timeout', '180', '--max-domain-watts', '1000',
                    '--zone', '/sys/devices/virtual/powercap/intel-rapl/intel-rapl:0',
                    '--label', label, '--output-dir', str(OUT / label)], 200, args.deadline_epoch)
                save(OUT / (label + '-pools.json'), {'mode': mode, 'before': before, 'after': pools()})
                save(OUT / (label + '-cap.json'), {'before_uw': cap_before,
                    'after_uw': int(CAP.read_text()), 'requested_uw': POWER_CAPS_UW[role]})
                assert pools() == expected_pool_state(mode) and int(CAP.read_text()) == POWER_CAPS_UW[role]
        save(OUT / 'comparison.json', compare(OUT, expected['miner']))
        for name, digest in expected.items():
            assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
        status = 'COMPLETE'
    except BaseException as error:
        failure = repr(error)
        raise
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        cleanup = []
        try:
            CAP.write_text('280000000\n')
            assert int(CAP.read_text()) == 280_000_000
        except Exception as error:
            cleanup.append('power cap: ' + repr(error))
        for mode in POOLS:
            try:
                set_pool('cleanup-' + mode, mode, 0)
            except Exception as error:
                cleanup.append(mode + ': ' + repr(error))
        try:
            if len(Path('/proc/swaps').read_text().splitlines()) == 1:
                run('cleanup-swap', ['swapon', '/swap.img'], 30)
        except Exception as error:
            cleanup.append('swap: ' + repr(error))
        restored = False
        try:
            restored = pools() == original and int(CAP.read_text()) == 280_000_000 and any(
                line.split()[0] == '/swap.img' and int(line.split()[3]) == 0
                for line in Path('/proc/swaps').read_text().splitlines()[1:])
            delta = {key: value - before_vm[key] for key, value in vm_counters().items()}
            save(OUT / 'vm-checks.json', delta)
            if any(delta.values()):
                cleanup.append('swap or OOM counters increased during the experiment')
        except Exception as error:
            cleanup.append('restoration verification: ' + repr(error))
        save(OUT / 'outcome.json', {'status': status if restored and not cleanup else 'FAILED',
            'failure': failure, 'settings_restored': restored, 'cleanup_failures': cleanup,
            'finished_at_epoch': time.time()})
        save(OUT / 'manifest.json', {str(path.relative_to(OUT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in OUT.rglob('*') if path.is_file() and path.name != 'manifest.json'})
        assert restored and not cleanup, cleanup


if __name__ == '__main__':
    main()
