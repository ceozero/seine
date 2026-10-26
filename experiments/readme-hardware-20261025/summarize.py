#!/usr/bin/env python3
"""Build summary.json from verified evidence in data/readme-hardware-20261025/.

Uses only collected, SHA256-verified guest evidence plus the local cost ledger.
Only accepted invocations contribute numbers; rejected ones are listed.
"""
import hashlib
import json
from pathlib import Path
import statistics

import cloud

HERE = Path(__file__).resolve().parent
ROOT = cloud.ROOT
DISPLAY = {
    'zen1-naples': 'Zen 1 Naples', 'zen2-rome': 'Zen 2 Rome', 'zen3-milan': 'Zen 3 Milan',
    'zen4-genoa': 'Zen 4 Genoa', 'zen5-turin': 'Zen 5 Turin', 'broadwell': 'Broadwell',
    'skylake': 'Skylake', 'skylake-r5': 'Skylake (r5)', 'cascadelake': 'Cascade Lake', 'icelake': 'Ice Lake',
    'sapphirerapids': 'Sapphire Rapids', 'graniterapids': 'Granite Rapids',
    'sapphirerapids-m7i': 'Sapphire Rapids (m7i)', 'icelake-m6i': 'Ice Lake (m6i)', 'graniterapids-m8i': 'Granite Rapids (m8i)',
    'graviton2': 'Graviton2', 'graviton3': 'Graviton3', 'graviton4': 'Graviton4',
}
ORDER = ['zen1-naples', 'zen2-rome', 'zen3-milan', 'zen4-genoa', 'zen5-turin', 'broadwell', 'skylake',
         'skylake-r5', 'cascadelake', 'icelake', 'icelake-m6i', 'sapphirerapids', 'sapphirerapids-m7i', 'graniterapids', 'graniterapids-m8i',
         'graviton2', 'graviton3', 'graviton4']


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def host(label, leases):
    attempts = sorted((ROOT / label).glob('attempt*/outcome.json'))
    history = []
    chosen = None
    for path in attempts:
        outcome = json.loads(path.read_text())
        history.append({'attempt': outcome['attempt'], 'status': outcome['status'], 'error': outcome.get('error')})
        if outcome['status'] == 'complete':
            chosen = path.parent
    lease_rows = [l for l in leases if l['label'] == label]
    base = {'label': label, 'host': DISPLAY.get(label, label), 'attempts': history,
            'leases': [{k: l.get(k) for k in ('type', 'lifecycle', 'zone', 'launched_at', 'verified_terminated_at',
                        'ondemand_usd_per_hour', 'spot_price_at_launch_usd_per_hour', 'cost', 'state_reason')}
                       for l in lease_rows]}
    if chosen is None:
        base['status'] = 'no complete run'
        return base
    ev = chosen / 'evidence'
    verification = json.loads((chosen / 'collection-verification.json').read_text())
    hw = json.loads((ev / 'hardware.json').read_text())
    status = json.loads((ev / 'status.json').read_text())
    records = json.loads((ev / 'records.json').read_text())
    parity = json.loads((ev / 'parity.json').read_text())
    config = json.loads((ev / 'host-config.json').read_text())
    lease = next(l for l in lease_rows if l['instance_id'] == json.loads((chosen / 'outcome.json').read_text())['instance_id'])
    accepted = [r for r in records if r['accepted']]
    rejected = [{'name': r['name'], 'problems': r['problems']} for r in records if not r['accepted']]
    variants = {v['name']: v for v in status['variants']}
    grid = {}
    for r in records:
        if r['phase'] != 'grid':
            continue
        cell = grid.setdefault(f"{r['variant']}@{r['workers']}", {
            'variant': r['variant'], 'kernel': r['kernel'], 'binary': r['binary'], 'threads': r['workers'],
            'samples_completed_hps': [], 'rejected': 0})
        if r['accepted']:
            cell['samples_completed_hps'].append(r['completed_hps'])
        else:
            cell['rejected'] += 1
    for cell in grid.values():
        s = cell['samples_completed_hps']
        cell['mean_completed_hps'] = statistics.mean(s) if s else None
    cells = {}
    for r in accepted:
        cells.setdefault((r['variant'], r['workers']), []).append(r)
    best_grid = tuple(status['best_grid_cell'])
    runner = tuple(status['runner_up_cell']) if status.get('runner_up_cell') else None
    def cell_stats(key):
        rows = cells.get(key, [])
        values = [r['completed_hps'] for r in rows]
        return {'variant': key[0], 'kernel': variants[key[0]]['kernel'], 'binary': variants[key[0]]['binary'],
                'threads': key[1], 'n_runs': len(values), 'values_completed_hps': values,
                'mean_completed_hps': statistics.mean(values) if values else None,
                'stdev_completed_hps': statistics.stdev(values) if len(values) > 1 else None,
                'confirm_values': [r['completed_hps'] for r in rows if r['phase'] == 'confirm']}
    b = cell_stats(best_grid)
    r_ = cell_stats(runner) if runner else None
    best = b
    reversed_ = False
    if r_ and r_['mean_completed_hps'] and r_['n_runs'] >= 2 and r_['mean_completed_hps'] > b['mean_completed_hps']:
        best, reversed_ = r_, True
    # Best cell using only the published v0.2.22 binary (Graviton bests may be the
    # unreleased PR #44 build); grid cells only, mean of their accepted samples.
    release_cells = {k: statistics.mean(r['completed_hps'] for r in v) for k, v in cells.items()
                     if variants[k[0]]['binary'] in ('seine-v022', 'seine-v022-arm')}
    release_best = None
    if release_cells:
        k = max(release_cells, key=release_cells.get)
        release_best = cell_stats(k)
    env = accepted[0]['environment'] if accepted else {}
    binaries = {}
    for r in accepted:
        binaries.setdefault(r['binary'], {'sha256': config['sha256'][r['binary']],
                                          'seine_version': r['environment'].get('seine_version'),
                                          'git_commit_label': r['environment'].get('git_commit'),
                                          'source_fingerprint': r['environment'].get('source_fingerprint'),
                                          'build_features': r['environment'].get('build_features')})
    od = lease['ondemand_usd_per_hour']
    out = base | {
        'status': 'complete',
        'instance_type': lease['type'], 'lifecycle': lease['lifecycle'], 'zone': lease['zone'],
        'cpu': {'brand': hw['cpu_brand'], 'vendor': hw['vendor_id'], 'family': hw['cpu_family'],
                'model': hw['model'], 'stepping': hw['stepping'], 'microcode': hw.get('microcode'),
                'arm_midr': hw.get('arm_midr'), 'seine_cpu_identity': env.get('cpu_identity'),
                'flags': hw['flags_has']},
        'topology': {'logical_cpus': hw['logical_cpus'], 'physical_cores': hw['physical_cores'],
                     'threads_per_core': hw['threads_per_core'], 'sockets': hw['sockets'],
                     'numa_nodes': hw['numa_nodes'], 'numa_node_cpus': hw['numa_node_cpus'],
                     'l3_instances': hw['l3_instances']},
        'memory': {'mem_total_gib': hw['mem_total_kib'] / 1024 ** 2,
                   'mem_available_before_gib': status['mem_available_before_bytes'] / 1024 ** 3,
                   'hugetlb_2mib_pages_reserved': status['hugetlb_pages_requested'],
                   'ordinary_available_after_reservation_gib':
                       status.get('ordinary_mem_available_after_reservation_bytes', 0) / 1024 ** 3,
                   'hugetlb_restored_to_zero': status['hugetlb_restored'],
                   'hugetlb_retry_after_compaction': status.get('hugetlb_retry_after_compaction', False)},
        'kernel_os': hw['kernel'],
        'thread_counts': status['worker_counts'], 'max_fitting_threads': status['max_fitting_workers'],
        'variants_timed': list(variants.values()),
        'parity': {k: {kk: v.get(kk) for kk in ('exit_code', 'passed', 'unsupported', 'sha256', 'covers_binary', 'status')}
                   for k, v in parity.items()},
        'grid': sorted(grid.values(), key=lambda c: (c['threads'], c['variant'])),
        'grid_order': status['grid_plan'],
        'best_grid_cell': b, 'runner_up_cell': r_, 'runner_up_basis': status.get('runner_up_basis'),
        'confirmation_reversed_grid_choice': reversed_,
        'best': {'variant': best['variant'], 'kernel': best['kernel'], 'binary': best['binary'],
                 'threads': best['threads'], 'mean_completed_hps': best['mean_completed_hps'],
                 'n_runs': best['n_runs']},
        'best_release_binary': {'variant': release_best['variant'], 'kernel': release_best['kernel'],
                                'threads': release_best['threads'], 'mean_completed_hps': release_best['mean_completed_hps'],
                                'n_runs': release_best['n_runs']} if release_best else None,
        'rejected_invocations': rejected,
        'skipped_for_deadline': status.get('skipped_for_deadline', []),
        'accepted_invocations': len(accepted),
        'max_steal_pct': max((r['steal_pct'] for r in accepted), default=None),
        'binaries': binaries,
        'pricing': {'ondemand_usd_per_hour': od, 'ondemand_source': lease['ondemand_price'],
                    'spot_price_paid_usd_per_hour': lease.get('spot_max_seen_usd_per_hour') if lease['lifecycle'] == 'spot' else None,
                    'hps_per_ondemand_usd_per_hour': best['mean_completed_hps'] / od},
        'guest_wall_seconds': status['wall_seconds'],
        'evidence_archive_sha256': verification['sha256'],
        'evidence_files_verified': verification['files'],
    }
    return out


def main():
    s = cloud.ledger()
    leases = s['leases']
    labels = [l for l in ORDER if (ROOT / l).exists() or any(x['label'] == l for x in leases)]
    hosts = [host(l, leases) for l in labels]
    closed = [l for l in leases if l.get('verified_terminated_at')]
    # Marketing number per generation = highest confirmed best cell across that
    # generation's instance variants (e.g. c7i vs 128 GiB m7i rerun).
    generations = {}
    for h in hosts:
        if h['status'] != 'complete':
            continue
        gen = h['label'].split('-m')[0] if h['label'].endswith(('-m6i', '-m7i', '-m8i')) else h['label']
        gen = 'skylake' if gen == 'skylake-r5' else gen
        cur = generations.get(gen)
        if cur is None or h['best']['mean_completed_hps'] > cur['mean_completed_hps']:
            generations[gen] = {'generation': DISPLAY.get(gen, gen), 'from_label': h['label'],
                                'instance_type': h['instance_type'], 'cpu': h['cpu']['brand'],
                                'physical_cores': h['topology']['physical_cores'],
                                'smt': h['topology']['threads_per_core'] > 1,
                                'kernel': h['best']['kernel'], 'binary': h['best']['binary'],
                                'threads': h['best']['threads'],
                                'mean_completed_hps': h['best']['mean_completed_hps'], 'n_runs': h['best']['n_runs'],
                                'release_v0_2_22_best': h['best_release_binary'],
                                'best_is_unreleased_build': h['best']['binary'] == 'seine-f20-arm',
                                'ondemand_usd_per_hour': h['pricing']['ondemand_usd_per_hour'],
                                'hps_per_ondemand_usd_per_hour': h['pricing']['hps_per_ondemand_usd_per_hour']}
    summary = {
        'campaign': 'readme-hardware-20261025',
        'release': {'version': 'v0.2.22', 'commit': '6e5411768d5d67365ecaff3abc30d280fb30cb0d',
                    'url': 'https://github.com/zpalmtree/seine/releases/tag/v0.2.22'},
        'arm_candidate': {'pr': 44, 'commit': 'f20e7bb1772be024a12ac5cdcc92685ba89d3ddd',
                          'kernel_selection': 'explicit --bench-cpu-kernel neon-sha3 (runtime-guarded by '
                                              'is_aarch64_feature_detected!("sha3"); generic build, no RUSTFLAGS)'},
        'terminology': 'threads = seine --threads = concurrent 2 GiB hashing workers',
        'metric': 'completed hashes / actual elapsed seconds including the round-end fence; mean over invocations '
                  '(each invocation = 1x20 s warmup + 2x20 s measured rounds)',
        'marketing_best_per_generation': [generations[g] for g in ORDER if g in generations],
        'hosts': hosts,
        'cost': {'leases': len(leases), 'closed_verified': len(closed),
                 'conservative_total_usd': sum(l['cost']['conservative_usd'] for l in closed),
                 'expected_total_usd': sum(l['cost']['expected_usd'] for l in closed),
                 'basis': 'per-lease launch -> verified termination, rounded up to the minute; on-demand rate '
                          '(spot unavailable), + 16 GiB gp3 + public IPv4 + $0.10 transfer contingency per lease',
                 'budget_cap_usd': 70, 'budget_cap_history': 'initially $30 (stop $28); raised to $70 by the user ~03:55 UTC', 'launch_stop_usd': cloud.BUDGET_STOP_USD},
        'spot_blocked': s.get('spot_blocked'),
        'cleanup': {k: s.get(k) for k in ('final_audit', 'cleanup_verified_at', 'security_group_deleted')},
    }
    cloud.save(HERE / 'summary.json', summary)
    for h in hosts:
        if h['status'] == 'complete':
            b = h['best']
            print(f"{h['host']:16} {h['instance_type']:12} {h['cpu']['brand'][:40]:40} "
                  f"{h['topology']['physical_cores']}/{h['topology']['logical_cpus']} "
                  f"{b['variant']:20} t{b['threads']:<3} {b['mean_completed_hps']:8.3f} H/s n={b['n_runs']} "
                  f"{h['pricing']['hps_per_ondemand_usd_per_hour']:.3f} H/s per $/h")
        else:
            print(h['host'], h['status'])
    print('conservative cost', round(summary['cost']['conservative_total_usd'], 4))
    md = ['| Host | Instance | CPU (guest-reported) | Physical cores | SMT | Best kernel | Threads | H/s (mean, n) | On-demand $/h | H/s per $/h |',
          '| --- | --- | --- | ---: | --- | --- | ---: | ---: | ---: | ---: |']
    for h in hosts:
        if h['status'] != 'complete':
            continue
        b = h['best']
        kernel = b['kernel'] + (' (f20e7bb)' if b['binary'] == 'seine-f20-arm' else '')
        md.append(f"| {h['host']} | {h['instance_type']} | {h['cpu']['brand']} | "
                  f"{h['topology']['physical_cores']} | {'2-way (' + str(h['topology']['logical_cpus']) + ' vCPU)' if h['topology']['threads_per_core'] > 1 else 'none'} | {kernel} | {b['threads']} | "
                  f"{b['mean_completed_hps']:.2f} (n={b['n_runs']}) | {h['pricing']['ondemand_usd_per_hour']:.4f} | "
                  f"{h['pricing']['hps_per_ondemand_usd_per_hour']:.2f} |")
    grid = ['| Host | Variant | ' + ' | '.join(['Threads: H/s per grid pass (mean)']) + ' |', '| --- | --- | --- |']
    for h in hosts:
        if h['status'] != 'complete':
            continue
        by = {}
        for c in h['grid']:
            by.setdefault(c['variant'], []).append(
                f"t{c['threads']}: " + ', '.join(f'{v:.2f}' for v in c['samples_completed_hps'])
                + (f" ({c['mean_completed_hps']:.2f})" if c['mean_completed_hps'] else ' (rejected)'))
        for v, cells in by.items():
            grid.append(f"| {h['host']} | {v} | {'; '.join(cells)} |")
    (cloud.ROOT / 'results-table.md').write_text('\n'.join(md) + '\n\n' + '\n'.join(grid) + '\n')


def render_readme(summary):
    """Regenerate the README block between the RESULTS markers from summary.json."""
    hosts = [h for h in summary['hosts'] if h['status'] == 'complete']
    L = ['## Results', '',
         'Completed H/s (completed hashes / elapsed incl. round-end fence), mean of the best cell\'s '
         'accepted invocations (2 grid + 2 confirmation). "Threads" = `--threads`. Whole 32-vCPU VM per row.', '',
         '### Best measured configuration per CPU generation (marketing numbers)', '',
         '| Generation | Instance | CPU (guest-reported) | Physical cores | SMT | Best kernel | Threads | H/s (n) | Best with published v0.2.22 binary | On-demand $/h | H/s per $/h |',
         '| --- | --- | --- | ---: | --- | --- | ---: | ---: | --- | ---: | ---: |']
    for g in summary['marketing_best_per_generation']:
        rel = g['release_v0_2_22_best']
        kernel = f"`{g['kernel']}`" + (' (PR #44 `f20e7bb`, unreleased)' if g['best_is_unreleased_build'] else '')
        relcell = 'same' if not g['best_is_unreleased_build'] else f"`{rel['kernel']}` t{rel['threads']}: {rel['mean_completed_hps']:.2f} (n={rel['n_runs']})"
        L.append(f"| {g['generation']} | {g['instance_type']} | {g['cpu']} | {g['physical_cores']} | "
                 f"{'2-way' if g['smt'] else 'no'} | {kernel} | {g['threads']} | {g['mean_completed_hps']:.2f} ({g['n_runs']}) | "
                 f"{relcell} | {g['ondemand_usd_per_hour']:.4f} | {g['hps_per_ondemand_usd_per_hour']:.2f} |")
    L += ['', '### Every host run', '',
          '| Host | Instance | CPU identity | RAM GiB | NUMA nodes / L3 | Threads swept | Best (variant, threads) | H/s (n, stdev) | Runner-up confirmed | Rejected runs |',
          '| --- | --- | --- | ---: | --- | --- | --- | ---: | --- | ---: |']
    for h in hosts:
        c = h['cpu']
        ident = (f"{c['vendor']} fam {c['family']} model {c['model']} step {c['stepping']}" if c['vendor'] != 'ARM'
                 else 'MIDR part ' + str((c.get('arm_midr') or {}).get('CPU part')) + ' r' + str((c.get('arm_midr') or {}).get('CPU variant')) + 'p' + str((c.get('arm_midr') or {}).get('CPU revision')))
        l3 = ', '.join(sorted({x['size'] for x in h['topology']['l3_instances']}))
        b = h['best_grid_cell'] if not h['confirmation_reversed_grid_choice'] else h['runner_up_cell']
        r = h['runner_up_cell']
        L.append(f"| {h['host']} | {h['instance_type']} | {c['brand']}<br>{ident} | {h['memory']['mem_total_gib']:.1f} | "
                 f"{h['topology']['numa_nodes']} / {len(h['topology']['l3_instances'])}x{l3} | {', '.join(map(str, h['thread_counts']))} | "
                 f"`{h['best']['variant']}` t{h['best']['threads']} | {h['best']['mean_completed_hps']:.2f} (n={h['best']['n_runs']}, "
                 f"{(b['stdev_completed_hps'] or 0):.3f}) | "
                 + (f"`{r['variant']}` t{r['threads']}: {r['mean_completed_hps']:.2f}" if r else '-')
                 + f" | {len(h['rejected_invocations'])} |")
    L += ['', '### Full grids (H/s per grid pass, opposite order; mean)', '', '| Host | Kernel (binary) | Results by threads |', '| --- | --- | --- |']
    for h in hosts:
        by = {}
        for c in h['grid']:
            by.setdefault((c['kernel'], c['binary']), []).append(
                f"t{c['threads']}: " + '/'.join(f'{v:.2f}' for v in c['samples_completed_hps'])
                + (f" ({c['mean_completed_hps']:.2f})" if c['mean_completed_hps'] else ' (rejected)'))
        for (k, b), cells in by.items():
            L.append(f"| {h['host']} | `{k}` ({'f20e7bb' if b == 'seine-f20-arm' else 'v0.2.22'}) | {'; '.join(cells)} |")
    L += ['', '### Cost ledger', '',
          '| Host | Instance | Lifecycle | Launched (UTC) | Termination verified (UTC) | Billable min (rounded up) | On-demand $/h | Conservative $ |',
          '| --- | --- | --- | --- | --- | ---: | ---: | ---: |']
    for h in summary['hosts']:
        for l in h['leases']:
            if not l.get('cost'):
                continue
            L.append(f"| {h['host']} | {l['type']} | {l['lifecycle']} | {l['launched_at'][11:19]} | {l['verified_terminated_at'][11:19]} | "
                     f"{round(l['cost']['billable_hours_rounded_up_to_minute'] * 60)} | {l['ondemand_usd_per_hour']:.4f} | {l['cost']['conservative_usd']:.3f} |")
    cost = summary['cost']
    L += ['', f"**Total: {cost['closed_verified']} leases, ${cost['conservative_total_usd']:.2f} conservative** "
          f"({cost['basis']}). Cap ${cost['budget_cap_usd']} ({cost['budget_cap_history']}); launch stop ${cost['launch_stop_usd']:.0f}.", '']
    text = (HERE / 'README.md').read_text()
    start, end = '<!-- RESULTS -->', '<!-- /RESULTS -->'
    head = text.split(start)[0]
    tail = text.split(end)[1] if end in text else text.split(start)[1]
    (HERE / 'README.md').write_text(head + start + '\n' + '\n'.join(L) + '\n' + end + tail)


if __name__ == '__main__':
    main()
    render_readme(json.loads((HERE / 'summary.json').read_text()))
