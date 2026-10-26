#!/usr/bin/env python3
"""Whole-VM README benchmark for one disposable, campaign-owned Linux guest.

Run from the uploaded bundle directory on a fresh instance whose independent
shutdown timer and shutdown-to-terminate behaviour were verified by the caller.
Standard library only. Writes evidence beside itself and a COMPLETE or FAILED
marker. The explicit HugeTLB pool must start empty and is restored in `finally`.

Protocol (fixed before launch):
  * full-size (2 GiB) reference parity for every timed kernel, per verifier;
  * workers 16, 24 and the largest count leaving >=5 GiB ordinary RAM after a
    HugeTLB reservation of ceil(1.05 * workers * 1024) 2 MiB pages;
  * kernel x worker grid, then the identical grid in exactly reversed order;
  * best cell confirmed by best/runner-up/runner-up/best invocations, runner-up
    being the second kernel at the best worker count (or, with one kernel, the
    same kernel at the second-best worker count);
  * every invocation: --bench-kind backend, 1 warmup + 2 measured 20 s rounds,
    --cpu-page-mode large, --cpu-affinity auto, fixed --threads, no autotune.
Completed H/s = sum(completed hashes) / sum(actual elapsed incl. round-end fence).
The report's avg_hps counts only hashes inside the configured window; ignored.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import statistics
import subprocess
import tempfile
import time
import traceback

ROOT = Path(__file__).resolve().parent
POOL = Path('/proc/sys/vm/nr_hugepages')
GIB = 1024 ** 3
SECONDS, ROUNDS, WARMUP = 20, 2, 1
RUN_ESTIMATE = 75  # seconds per invocation incl. allocation and settle sleep
CONFIG = json.loads((ROOT / 'host-config.json').read_text())
SCRUB = ('SEINE_', 'BNMINER_')


def save(path, obj):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n')
    tmp.replace(path)


def log(*args):
    print(time.strftime('%H:%M:%S', time.gmtime()), *args, flush=True)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sh(command, timeout=120, check=True, **kw):
    return subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=check, **kw)


def meminfo():
    return {line.split(':')[0]: int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines()}


def counters():
    vm = dict(line.split() for line in Path('/proc/vmstat').read_text().splitlines())
    cpu = [int(v) for v in Path('/proc/stat').read_text().splitlines()[0].split()[1:]]
    return {k: int(vm[k]) for k in ('pswpin', 'pswpout', 'oom_kill')} | {'ticks': sum(cpu[:8]), 'steal': cpu[7]}


def set_pool(pages):
    sh(['sudo', 'sysctl', '-w', f'vm.nr_hugepages={pages}'])
    return int(POOL.read_text())


def child_env():
    env = {k: v for k, v in os.environ.items() if not k.startswith(SCRUB)}
    env['NO_COLOR'] = '1'
    return env


def hardware():
    out = ROOT / 'hardware'
    out.mkdir(exist_ok=True)
    for name, command in {'lscpu.json': ['lscpu', '-J'], 'lscpu-extended.txt': ['lscpu', '-e'],
                          'lscpu-caches.json': ['lscpu', '-C', '-J'], 'uname.txt': ['uname', '-a'],
                          'lscpu.txt': ['lscpu'], 'nproc.txt': ['nproc']}.items():
        result = sh(command, check=False)
        (out / name).write_text(result.stdout + result.stderr)
    for src in ['/proc/cpuinfo', '/proc/meminfo', '/proc/swaps', '/proc/loadavg', '/proc/cmdline',
                '/sys/kernel/mm/transparent_hugepage/enabled']:
        (out / src.strip('/').replace('/', '_')).write_text(Path(src).read_text())
    for src in ['product_name', 'sys_vendor', 'board_name']:
        p = Path('/sys/devices/virtual/dmi/id') / src
        if p.exists():
            try:
                (out / ('dmi_' + src)).write_text(p.read_text())
            except OSError:
                pass
    nodes = sorted(p.name for p in Path('/sys/devices/system/node').glob('node[0-9]*'))
    fields = {r['field'].rstrip(':'): r['data'] for r in json.loads((out / 'lscpu.json').read_text())['lscpu']}
    caches = json.loads((out / 'lscpu-caches.json').read_text()).get('caches', [])
    cpuinfo = Path('/proc/cpuinfo').read_text()
    first = {}
    for line in cpuinfo.split('\n\n')[0].splitlines():
        if ':' in line:
            k, v = line.split(':', 1)
            first[k.strip()] = v.strip()
    # Unique L3 instances from sysfs shared_cpu_list.
    l3 = {}
    for cache in Path('/sys/devices/system/cpu').glob('cpu[0-9]*/cache/index*'):
        try:
            if (cache / 'level').read_text().strip() == '3':
                l3[(cache / 'shared_cpu_list').read_text().strip()] = (cache / 'size').read_text().strip()
        except OSError:
            pass
    def num(*keys):
        for k in keys:
            try:
                return int(fields.get(k))
            except (TypeError, ValueError):
                pass
        return None
    sockets = num('Socket(s)', 'Cluster(s)') or 1
    cores_per_socket = num('Core(s) per socket', 'Core(s) per cluster') or 0
    threads_per_core = num('Thread(s) per core') or 1
    info = {
        'arch': os.uname().machine,
        'cpu_brand': fields.get('Model name'),
        'vendor_id': fields.get('Vendor ID'),
        'cpu_family': fields.get('CPU family'),
        'model': fields.get('Model'),
        'stepping': fields.get('Stepping'),
        'microcode': first.get('microcode'),
        'arm_midr': {k: first.get(k) for k in ('CPU implementer', 'CPU architecture', 'CPU variant', 'CPU part', 'CPU revision')}
                    if os.uname().machine == 'aarch64' else None,
        'logical_cpus': os.cpu_count(),
        'sockets': sockets,
        'cores_per_socket': cores_per_socket,
        'threads_per_core': threads_per_core,
        'physical_cores': sockets * cores_per_socket,
        'numa_nodes': len(nodes),
        'numa_node_cpus': {n: Path(f'/sys/devices/system/node/{n}/cpulist').read_text().strip() for n in nodes},
        'l3_instances': [{'shared_cpu_list': k, 'size': v} for k, v in sorted(l3.items())],
        'lscpu_caches': caches,
        'mem_total_kib': meminfo()['MemTotal'],
        'hypervisor': fields.get('Hypervisor vendor'),
        'flags_has': {f: bool(re.search(rf'\b{f}\b', first.get('flags', first.get('Features', ''))))
                      for f in ('avx2', 'avx512f', 'avx512vl', 'avx512_vnni', 'amx_tile', 'sha3', 'asimd', 'sve', 'sve2')},
        'kernel': os.uname().release,
    }
    save(ROOT / 'hardware.json', info)
    return info


def maybe_build_v022_arm_verifier():
    """Build v0.2.22 verify_cpu_kernels natively when no frozen copy was supplied."""
    target = ROOT / 'verify-v022-arm'
    if target.exists() or not CONFIG.get('build_v022_verifier'):
        return None
    start = time.monotonic()
    build = ROOT / 'build-v022'
    build.mkdir()
    logf = (ROOT / 'build-v022.log').open('w')
    def run(cmd, timeout=900, cwd=None, env=None):
        logf.write('$ ' + ' '.join(cmd) + '\n'); logf.flush()
        subprocess.run(cmd, stdout=logf, stderr=subprocess.STDOUT, timeout=timeout, check=True, cwd=cwd, env=env)
    run(['sudo', 'apt-get', 'update', '-qq'])
    run(['sudo', 'env', 'DEBIAN_FRONTEND=noninteractive', 'apt-get', 'install', '-y', '-qq', 'gcc', 'curl'])
    run(['sh', '-c', "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs -o /tmp/rustup-init.sh"])
    run(['sh', '/tmp/rustup-init.sh', '-y', '--profile', 'minimal', '--default-toolchain', '1.93.0'])
    run(['tar', 'xf', str(ROOT / 'v022-source.tar'), '-C', str(build)])
    env = child_env()
    env['PATH'] = str(Path.home() / '.cargo/bin') + ':' + env['PATH']
    env['CARGO_TARGET_DIR'] = str(build / 'target-v022-verify')  # isolated, never shared
    run(['cargo', '+1.93.0', 'build', '--locked', '--release', '-p', 'blocknet-pow-kernel',
         '--example', 'verify_cpu_kernels'], cwd=build, env=env, timeout=1200)
    shutil.copy2(build / 'target-v022-verify/release/examples/verify_cpu_kernels', target)
    rustc = sh([str(Path.home() / '.cargo/bin/rustc'), '+1.93.0', '--version'], env=env).stdout.strip()
    record = {'source_commit': CONFIG['release_commit'], 'source_archive_sha256': sha256(ROOT / 'v022-source.tar'),
              'command': 'cargo +1.93.0 build --locked --release -p blocknet-pow-kernel --example verify_cpu_kernels',
              'cargo_target_dir': 'isolated target-v022-verify', 'rustc': rustc, 'rustflags': None,
              'sha256': sha256(target), 'build_seconds': time.monotonic() - start}
    save(ROOT / 'verify-v022-arm-provenance.json', record)
    shutil.rmtree(build / 'target-v022-verify', ignore_errors=True)
    # Let compiler memory and cache pressure settle before any timing.
    subprocess.run(['sync'])
    time.sleep(10)
    return record


def parity():
    results = {}
    for verifier in CONFIG['verifiers']:
        path = ROOT / verifier['file']
        if not path.exists():
            results[verifier['file']] = {'status': 'missing'}
            continue
        start = time.monotonic()
        result = subprocess.run([str(path)], capture_output=True, text=True, timeout=900, env=child_env())
        (ROOT / (verifier['file'] + '.log')).write_text(result.stdout + result.stderr)
        passed = re.findall(r'^(\S+): PASS', result.stdout, re.MULTILINE)
        # f20e7bb verifier format: "PASS nonce=N kernel=K full_size_bytes=2147483648 dirty_reuse=true"
        passed += [k for k in dict.fromkeys(re.findall(
            r'^PASS nonce=\S+ kernel=(\S+) full_size_bytes=2147483648', result.stdout, re.MULTILINE))
                   if k not in passed]
        unsupported = re.findall(r'^(\S+): unsupported', result.stdout, re.MULTILINE)
        results[verifier['file']] = {'exit_code': result.returncode, 'passed': passed, 'unsupported': unsupported,
                                     'covers_binary': verifier['covers'], 'sha256': sha256(path),
                                     'seconds': time.monotonic() - start}
        log('parity', verifier['file'], result.returncode, passed)
    save(ROOT / 'parity.json', results)
    return results


def run_case(out, name, variant, workers):
    binary = ROOT / variant['binary']
    kernel = variant['kernel']
    path = out / (name + '.json')
    datadir = Path(tempfile.mkdtemp(prefix='seine-data-'))
    command = [str(binary), '--bench', '--bench-kind', 'backend', '--backend', 'cpu',
               '--threads', str(workers), '--cpu-page-mode', 'large', '--cpu-affinity', 'auto',
               '--bench-cpu-kernel', kernel, '--disable-cpu-autotune-threads', '--ui', 'plain',
               '--bench-secs', str(SECONDS), '--bench-rounds', str(ROUNDS),
               '--bench-warmup-rounds', str(WARMUP), '--bench-output', str(path),
               '--data-dir', str(datadir)]
    record = {'name': name, 'variant': variant['name'], 'kernel': kernel, 'workers': workers,
              'binary': variant['binary'], 'command': command, 'started_utc': time.time()}
    before = counters()
    mem_before = meminfo()
    start = time.monotonic()
    try:
        with (out / (name + '.log')).open('w') as logf:
            result = subprocess.run(command, stdout=logf, stderr=subprocess.STDOUT, timeout=240, env=child_env())
        record['exit_code'] = result.returncode
        record['wall_seconds'] = time.monotonic() - start
        delta = {k: v - before[k] for k, v in counters().items()}
        mem_after = meminfo()
        record['vm_delta'] = delta
        record['steal_pct'] = 100 * delta['steal'] / max(1, delta['ticks'])
        record['hugepages_total_before_after'] = [mem_before['HugePages_Total'], mem_after['HugePages_Total']]
        problems = []
        if result.returncode != 0:
            problems.append(f'exit code {result.returncode}')
        for k in ('pswpin', 'pswpout', 'oom_kill'):
            if delta[k]:
                problems.append(f'{k} delta {delta[k]}')
        if record['steal_pct'] >= 2:
            problems.append(f"steal {record['steal_pct']:.3f}%")
        if mem_before['HugePages_Total'] != mem_after['HugePages_Total']:
            problems.append('HugeTLB pool changed during run')
        report = json.loads(path.read_text()) if path.exists() else None
        if report is None:
            problems.append('no report')
        else:
            env, fp = report['environment'], report['config_fingerprint']
            record['report_sha256'] = sha256(path)
            record['environment'] = {k: env.get(k) for k in ('seine_version', 'git_commit', 'source_fingerprint',
                                     'build_fingerprint', 'build_features', 'target_triple', 'runtime_environment',
                                     'cpu_brand', 'cpu_identity', 'cpu_kernels_supported', 'logical_cores',
                                     'physical_cores', 'total_memory_bytes')}
            checks = {
                'workers': report['cpu_threads'] == workers,
                'rounds': len(report['runs']) == ROUNDS and report.get('rounds') == ROUNDS,
                'warmup': report.get('warmup_rounds') == WARMUP,
                'bench_secs': report.get('bench_secs') == SECONDS,
                'kernel': fp['cpu_kernel'] == kernel and fp.get('cpu_kernel_requested') == kernel,
                'page_mode': fp['cpu_page_mode'] == 'large',
                'affinity': fp.get('cpu_affinity') == 'auto',
                'autotune_off': fp['cpu_autotune_threads'] is False,
                'cpu_only': report.get('backends') == ['cpu#1'],
                'native': env.get('runtime_environment') == 'native',
                'pow': report['pow_fingerprint'].get('memory_kb') == 2097152
                       and report['pow_fingerprint'].get('iterations') == 1
                       and report['pow_fingerprint'].get('parallelism') == 1,
            }
            samples = []
            for run in report['runs']:
                b = run['backend_runs']
                samples.append({'hashes': run['hashes'], 'counted_hashes': run['counted_hashes'],
                                'late_hashes': run['late_hashes'], 'elapsed_secs': run['elapsed_secs'],
                                'actual_elapsed_secs': run['actual_elapsed_secs'],
                                'fence_secs': run.get('fence_secs'),
                                'completed_hps': run['hashes'] / run['actual_elapsed_secs']})
                checks.setdefault('hash_accounting', True)
                checks['hash_accounting'] &= run['hashes'] == run['counted_hashes'] + run['late_hashes']
                checks.setdefault('full_hugetlb', True)
                checks['full_hugetlb'] &= (sum(x['memory_explicit_large_workers'] for x in b) == workers
                                           and sum(x['memory_explicit_large_bytes'] for x in b) == workers * 2 * GIB
                                           and sum(x['memory_regular_workers'] + x['memory_heap_workers']
                                                   + x['memory_transparent_huge_workers'] for x in b) == 0)
                checks.setdefault('zero_failures', True)
                checks['zero_failures'] &= all(x[k] == 0 for x in b for k in (
                    'memory_allocation_failures', 'dropped_events', 'assignment_enqueue_timeouts',
                    'assignment_execution_timeouts', 'control_enqueue_timeouts', 'control_execution_timeouts'))
                checks.setdefault('all_lanes_active', True)
                checks['all_lanes_active'] &= sum(x.get('peak_active_lanes', workers) for x in b) == workers
            record['checks'] = checks
            record['samples'] = samples
            problems += [f'check failed: {k}' for k, v in checks.items() if not v]
            record['completed_hps'] = sum(s['hashes'] for s in samples) / sum(s['actual_elapsed_secs'] for s in samples)
            record['report_avg_hps_window_only'] = report.get('avg_hps')
        record['problems'] = problems
        record['accepted'] = not problems
    except Exception as error:  # retained as a rejected invocation
        record.update(accepted=False, problems=[f'exception: {error!r}'], wall_seconds=time.monotonic() - start)
    finally:
        shutil.rmtree(datadir, ignore_errors=True)
    save(out / (name + '-record.json'), record)
    log(name, 'ACCEPTED' if record['accepted'] else 'REJECTED', f"{record.get('completed_hps', 0):.4f} H/s",
        record.get('problems'))
    time.sleep(2)
    return record


def main():
    started = time.monotonic()
    status = {'label': CONFIG['label'], 'started_unix': time.time()}
    for name, digest in CONFIG['sha256'].items():
        if (ROOT / name).exists():
            assert sha256(ROOT / name) == digest, f'bundle digest mismatch {name}'
    timer = sh(['sudo', 'cat', '/run/systemd/shutdown/scheduled']).stdout
    shutdown_at = next(int(l.split('=', 1)[1]) / 1e6 for l in timer.splitlines() if l.startswith('USEC='))
    deadline = shutdown_at - 6 * 60  # leave time for collection before the guest powers off
    status['shutdown_at_unix'] = shutdown_at
    status['measurement_deadline_unix'] = deadline
    save(ROOT / 'status.json', status)
    assert len(Path('/proc/swaps').read_text().splitlines()) == 1, 'guest must have no swap'
    assert int(POOL.read_text()) == 0, 'refuse to alter a pre-existing HugeTLB pool'
    assert meminfo()['Hugepagesize'] == 2048
    hw = hardware()
    log('hardware', hw['cpu_brand'], hw['vendor_id'], hw['cpu_family'], hw['model'], hw['stepping'])
    build = maybe_build_v022_arm_verifier()
    if build:
        CONFIG['sha256']['verify-v022-arm'] = build['sha256']
        log('built verify-v022-arm', build['sha256'], f"{build['build_seconds']:.0f}s")
    par = parity()
    # Variant selection: a kernel is timed only if its covering verifier passed it.
    variants = []
    for v in CONFIG['variants']:
        ok = [r for r in par.values() if r.get('exit_code') == 0 and v['binary'] in r['covers_binary']
              and v['kernel'] in r['passed']]
        if ok:
            variants.append(v)
        else:
            log('variant not timed (no passing full-size parity):', v['name'])
    for v in CONFIG.get('conditional_variants', []):
        # e.g. Graviton2 portable NEON when neon-sha3 is unsupported
        if not any(x['name'] == v['when_missing'] for x in variants):
            ok = [r for r in par.values() if r.get('exit_code') == 0 and v['binary'] in r['covers_binary']
                  and v['kernel'] in r['passed']]
            if ok:
                variants.append(v)
    assert variants, 'no verified kernel'
    status['variants'] = variants
    # Idle check: loadavg should be small before allocation.
    for _ in range(30):
        if float(Path('/proc/loadavg').read_text().split()[0]) < 1.0:
            break
        time.sleep(4)
    status['loadavg_before'] = Path('/proc/loadavg').read_text().strip()
    mem = meminfo()
    available = mem['MemAvailable'] * 1024
    cpus = len(os.sched_getaffinity(0))
    def pages_for(w):
        return math.ceil(1.05 * w * 1024)
    wmax = max(w for w in range(1, cpus + 1) if pages_for(w) * 2 * 1024 ** 2 + 5 * GIB <= available)
    # Sweep (coordinator update 03:55 UTC): SMT hosts also try 20; 32-core hosts 30 and 32.
    smt = hw['threads_per_core'] > 1
    candidates = (16, 20, 24, wmax) if smt else (16, 24, 30, 32, wmax)
    counts = sorted({c for c in candidates if c <= wmax})
    flagship = CONFIG.get('mode') == 'flagship'
    if flagship:
        # Full-size host (coordinator plan): coarse 25/50/75/100% of physical cores,
        # capped by RAM, then refine +/-12.5% around the best; reserve for the
        # largest count that refinement could reach (logical CPUs on SMT hosts).
        cores = hw['physical_cores']
        counts = sorted({min(wmax, max(1, round(cores * p))) for p in (0.25, 0.5, 0.75, 1.0)})
        ceiling = min(wmax, cpus if smt else cores)
        pages = pages_for(ceiling)
        status['flagship_ceiling'] = ceiling
    else:
        pages = pages_for(max(counts))
    status.update(mem_available_before_bytes=available, logical_cpus=cpus, max_fitting_workers=wmax,
                  worker_counts=counts, hugetlb_pages_requested=pages)
    save(ROOT / 'status.json', status)
    log('workers', counts, 'pages', pages, 'available GiB', available / GIB)
    save(ROOT / 'memory-before.json', mem)
    records = []
    try:
        got = set_pool(pages)
        if got != pages:
            # Fresh guests normally reserve at once; compact and retry once, recording it.
            subprocess.run(['sudo', 'sh', '-c', 'sync; echo 3 > /proc/sys/vm/drop_caches; echo 1 > /proc/sys/vm/compact_memory'])
            status['hugetlb_retry_after_compaction'] = True
            got = set_pool(pages)
        mem_reserved = meminfo()
        save(ROOT / 'memory-reserved.json', mem_reserved)
        assert got == pages and mem_reserved['HugePages_Free'] == pages, ('HugeTLB reservation incomplete', got)
        status['ordinary_mem_available_after_reservation_bytes'] = mem_reserved['MemAvailable'] * 1024
        assert mem_reserved['MemAvailable'] * 1024 >= 5 * GIB, 'ordinary RAM headroom below 5 GiB'
        out = ROOT / 'runs'
        out.mkdir(exist_ok=False)
        sequence = [(w, v) for w in counts for v in variants]
        plan = [(1, w, v) for w, v in sequence] + [(2, w, v) for w, v in reversed(sequence)]
        if flagship:
            # One coarse pass, kernel order alternating per thread count.
            plan = [(1, w, v) for i, w in enumerate(counts) for v in (variants if i % 2 == 0 else variants[::-1])]
        status['grid_plan'] = [f'p{p}-w{w}-{v["name"]}' for p, w, v in plan]
        save(ROOT / 'status.json', status)
        for p, w, v in plan:
            if time.time() + RUN_ESTIMATE > deadline:
                status.setdefault('skipped_for_deadline', []).append(f'p{p}-w{w}-{v["name"]}')
                continue
            rec = run_case(out, f'grid-p{p}-w{w}-{v["name"]}', v, w)
            rec.update(phase='grid', pass_index=p)
            records.append(rec)
            save(ROOT / 'records.json', records)
        if flagship:
            coarse = {(r['variant'], r['workers']): r['completed_hps'] for r in records if r['accepted']}
            assert coarse, 'no accepted coarse cell'
            bv, bw = max(coarse, key=coarse.get)
            step = max(1, round(hw['physical_cores'] * 0.125))
            refine = sorted({w for w in (bw - step, bw + step) if 1 <= w <= status['flagship_ceiling']
                             and (bv, w) not in coarse})
            status['refine_counts'] = refine
            for w in refine:
                if time.time() + RUN_ESTIMATE > deadline:
                    status.setdefault('skipped_for_deadline', []).append(f'refine-w{w}-{bv}')
                    continue
                v = next(x for x in variants if x['name'] == bv)
                rec = run_case(out, f'grid-refine-w{w}-{bv}', v, w)
                rec.update(phase='grid', pass_index='refine')
                records.append(rec)
                save(ROOT / 'records.json', records)
        cells = {}
        for r in records:
            if r['accepted']:
                cells.setdefault((r['variant'], r['workers']), []).append(r['completed_hps'])
        complete = {k: statistics.mean(x) for k, x in cells.items() if len(x) == (1 if flagship else 2)}
        assert complete, 'no grid cell has two accepted samples'
        best = max(complete, key=complete.get)
        same_w = sorted((k for k in complete if k[1] == best[1] and k != best), key=complete.get, reverse=True)
        if flagship:
            others = sorted((k for k in complete if k != best), key=complete.get, reverse=True)
            runner = others[0] if others else None
            runner_basis = 'flagship: second-best measured cell'
        elif same_w:
            runner = same_w[0]
            runner_basis = 'second kernel at best worker count'
        else:
            other = sorted((k for k in complete if k[0] == best[0] and k != best), key=complete.get, reverse=True)
            runner = other[0] if other else None
            runner_basis = 'single kernel: same kernel at second-best worker count'
        status.update(best_grid_cell=list(best), runner_up_cell=list(runner) if runner else None,
                      runner_up_basis=runner_basis)
        save(ROOT / 'status.json', status)
        vmap = {v['name']: v for v in variants}
        order = [best, runner, runner, best] if runner else [best, best]
        for i, cell in enumerate(order, 1):
            if time.time() + RUN_ESTIMATE > deadline:
                status.setdefault('skipped_for_deadline', []).append(f'confirm-{i}-{cell}')
                continue
            rec = run_case(out, f'confirm-{i}-w{cell[1]}-{cell[0]}', vmap[cell[0]], cell[1])
            rec.update(phase='confirm', confirm_index=i)
            records.append(rec)
            save(ROOT / 'records.json', records)
    finally:
        restored = set_pool(0)
        save(ROOT / 'memory-restored.json', meminfo())
        status['hugetlb_restored'] = restored == 0
        status['wall_seconds'] = time.monotonic() - started
        save(ROOT / 'status.json', status)
        save(ROOT / 'records.json', records)
    for name, digest in CONFIG['sha256'].items():
        if (ROOT / name).exists():
            assert sha256(ROOT / name) == digest, f'bundle digest changed {name}'
    assert status['hugetlb_restored']
    (ROOT / 'COMPLETE').write_text('Parity, grid, confirmation and restore finished; see records.json.\n')
    log('COMPLETE', f'{status["wall_seconds"]:.0f}s')


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        (ROOT / 'FAILED').write_text(traceback.format_exc())
        raise
