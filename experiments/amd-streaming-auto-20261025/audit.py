#!/usr/bin/env python3
"""Independent audit of complete native results; does not execute the miner."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics

COMMIT = 'a13502a1a2a76e2825c4ae1e05ee81dc0a086859'
SOURCE = '505c35d2289a3788'
POW = {'memory_kb':2097152,'iterations':1,'parallelism':1,'output_len':32,'header_base_len':92}


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def gain(samples):
    before,candidate,after=samples
    if any(s['secs']<=0 or s['hashes']<=0 for s in samples):return False
    rate=lambda s:s['hashes']/s['secs']
    if abs(rate(after)/rate(before)-1)>.05:return False
    base=(before['hashes']+after['hashes'])/(before['secs']+after['secs'])
    return rate(candidate)>base*1.02+sum(1/s['secs'] for s in samples)


def audit(root):
    assert (root/'COMPLETE').exists()
    protocol=read(root/'protocol.json')
    assert protocol['source_commit']==COMMIT
    assert (root/'verify_cpu_kernels.log').read_text().count(': PASS (full 2 GiB reference parity)')==5
    assert len([s for s in (root/'verify_streaming_dispatch.log').read_text().splitlines() if s.startswith('PASS ')])==21
    names=[f'count-p{n}-{label}' for n in range(1,5) for label in ['eight','sixteen']]
    names += [f'ccd-p{n}-{label}' for n in [1,2] for label in ['spread','cache','frequency']]
    rates={};fingerprints=set();files=[]
    for name in names:
        p=root/(name+'.json');r=read(p);meta=read(root/(name+'.meta.json'))
        env=r['environment'];fp=r['config_fingerprint'];workers=len(meta['cpus'])
        assert env['git_commit']==COMMIT and env['source_fingerprint']==SOURCE
        assert env['target_triple']=='x86_64-pc-windows-msvc' and env['runtime_environment']=='native'
        assert (env['cpu_identity']['family'],env['cpu_identity']['model'])==(26,68)
        assert r['pow_fingerprint']==POW and r['backends']==['cpu#1']
        assert r['cpu_threads']==workers and workers in [8,16]
        assert fp['cpu_kernel']==fp['cpu_kernel_requested']=='avx512-256-stream'
        assert fp['cpu_page_mode']=='regular' and fp['cpu_affinity']=='os'
        assert not fp['cpu_autotune_threads'] and fp['bench_warmup_rounds']==1
        assert meta['mask']==sum(1<<c for c in meta['cpus']) and meta['exit_code']==0
        assert len(r['runs'])==2
        for s in r['runs']:
            assert s['hashes']==s['counted_hashes']+s['late_hashes']
            assert s['elapsed_secs']==s['actual_elapsed_secs']
            assert sum(b['memory_regular_bytes'] for b in s['backend_runs'])==workers*2*1024**3
            assert sum(b['memory_regular_workers'] for b in s['backend_runs'])==workers
            for b in s['backend_runs']:
                for field in ['memory_allocation_failures','dropped_events','assignment_enqueue_timeouts','assignment_execution_timeouts','control_enqueue_timeouts','control_execution_timeouts']:assert b[field]==0
        rates[name]=statistics.mean(s['hashes']/s['elapsed_secs'] for s in r['runs'])
        assert rates[name]==meta['hps'];fingerprints.add(env['build_fingerprint'])
        files.append({'path':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    assert len(fingerprints)==1
    pairs=[{'eight':rates[f'count-p{n}-eight'],'sixteen':rates[f'count-p{n}-sixteen']} for n in range(1,5)]
    assert pairs==read(root/'count-pairs.json')
    summary=read(root/'summary.json')
    for key in ['eight','sixteen']:assert summary['count_means'][key]==statistics.mean(p[key] for p in pairs)
    geometric=100*(math.exp(statistics.mean(math.log(p['eight']/p['sixteen']) for p in pairs))-1)
    assert geometric==summary['geometric_eight_vs_sixteen_pct']
    episodes={name:read(root/name/'record.json') for name in ['cold','warm','load','reserve']}
    for name,e in episodes.items():
        assert e['seconds']<600 and not e['errors']
        assert any(ev['method']=='login' for ev in e['fixture_events'])
        assert '--bench-cpu-kernel' not in e['command'] and '--threads' not in e['command']
        for cache in e['cache_after'].values():
            for winner in cache.get('winners',[]):
                if winner['kernel']==winner['candidate']:
                    assert len(winner['samples'])==6 and gain(winner['samples'][:3]) and gain(winner['samples'][3:])
    assert episodes['warm']['cache_before']==episodes['cold']['cache_after']
    assert episodes['reserve']['cache_before']==episodes['reserve']['cache_after']
    assert read(root/'cleanup.json')['all_children_stopped']
    return {'source_commit':COMMIT,'source_fingerprint':SOURCE,'build_fingerprint':fingerprints.pop(),'reports_checked':14,
            'count_means':summary['count_means'],'paired_eight_vs_sixteen_pct':summary['paired_eight_vs_sixteen_pct'],
            'geometric_eight_vs_sixteen_pct':geometric,'placement_means':summary['placement_means'],
            'episode_seconds':{n:e['seconds'] for n,e in episodes.items()},'files':files}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path);args=parser.parse_args()
    print(json.dumps(audit(args.directory),indent=2))
