#!/usr/bin/env python3
"""Owned native Windows validation. No global settings, network pools or GPU work.

Pool episodes end before the 600-second dev-fee grace period. Memory-pressure
coverage here uses an explicit high reserve on restart, not an OS stress test.
"""
import argparse
import ctypes as C
from ctypes import wintypes as W
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import shutil
import statistics
import subprocess
import sys
import threading
import time

from fixture import Server, address

GI = 1024**3
K = C.WinDLL('kernel32', use_last_error=True)
K.GetCurrentProcess.restype = W.HANDLE
K.SetProcessAffinityMask.argtypes = [W.HANDLE, C.c_size_t]
K.SetPriorityClass.argtypes = [W.HANDLE, W.DWORD]
K.CreateJobObjectW.argtypes = [C.c_void_p, W.LPCWSTR]
K.CreateJobObjectW.restype = W.HANDLE
K.SetInformationJobObject.argtypes = [W.HANDLE, C.c_int, C.c_void_p, W.DWORD]
K.AssignProcessToJobObject.argtypes = [W.HANDLE, W.HANDLE]
K.CloseHandle.argtypes = [W.HANDLE]

class Basic(C.Structure):
    _fields_ = [('process_time', C.c_int64), ('job_time', C.c_int64),
                ('flags', W.DWORD), ('min_ws', C.c_size_t), ('max_ws', C.c_size_t),
                ('active', W.DWORD), ('affinity', C.c_size_t),
                ('priority', W.DWORD), ('scheduling', W.DWORD)]
class IO(C.Structure):
    _fields_ = [(n, C.c_uint64) for n in ['ro','wo','oo','rb','wb','ob']]
class Extended(C.Structure):
    _fields_ = [('basic', Basic), ('io', IO), ('process_memory', C.c_size_t),
                ('job_memory', C.c_size_t), ('peak_process', C.c_size_t), ('peak_job', C.c_size_t)]
class Memory(C.Structure):
    _fields_ = [('length', W.DWORD), ('load', W.DWORD)] + [(n, C.c_uint64) for n in
                ['total','available','total_page','available_page','total_virtual','available_virtual','reserved']]


def memory():
    m = Memory(); m.length = C.sizeof(m)
    assert K.GlobalMemoryStatusEx(C.byref(m))
    return {n: getattr(m,n) for n in ['total','available','load']}


def save(path, obj):
    path.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')


class Campaign:
    def __init__(self, root, jobid):
        self.root=root; self.out=root/'results'; self.out.mkdir(exist_ok=False)
        self.jobid=jobid; self.started=time.monotonic(); self.children=[]
        self.resume=json.loads((root/'resume.json').read_text()) if (root/'resume.json').exists() else None
        self.stop_before=datetime.datetime.fromisoformat(json.loads((root/'deadline.json').read_text())['stop_before_utc']).timestamp()
        assert self.stop_before-time.time()>=(1200 if self.resume else 2100), 'Insufficient clean time before research collection deadline'
        self.exe=root/'target/release/seine.exe'
        self.sha=hashlib.sha256(self.exe.read_bytes()).hexdigest()
        if self.resume:
            assert self.sha==self.resume['binary_sha256']
            source=root/self.resume['source_directory']
            for name,digest in self.resume['accepted_files'].items():
                assert Path(name).name==name and hashlib.sha256((source/name).read_bytes()).hexdigest()==digest
                shutil.copy2(source/name,self.out/name)
            shutil.copy2(source/'protocol.json',self.out/'benchmark-protocol.json')
            save(self.out/'resume.json',self.resume)
        self.job=K.CreateJobObjectW(None,None); assert self.job
        limits=Extended(); limits.basic.flags=0x2000|0x200  # kill on close + aggregate memory ceiling
        limits.job_memory=40*GI
        assert K.SetInformationJobObject(self.job,9,C.byref(limits),C.sizeof(limits)), C.get_last_error()
        self.check()
        assert memory()['available']>=42*GI, memory()
        save(self.out/'protocol.json',{'binary_sha256':self.sha,'job_id':jobid,'memory_before':memory(),
             'benchmark_job_id':self.resume['job_id'] if self.resume else jobid,'lifecycle_only_resume':bool(self.resume),'job_memory_ceiling_bytes':40*GI,'deadline_seconds':2700,'stop_before_epoch':self.stop_before,'source_commit':json.loads((root/'source.json').read_text())['commit'],
             'confirmation':'Four AB/BA pairs,8 spread vs16 physical,streaming,20s warmup+2x20s measured',
             'ccd_screen':'Two reversed passes,8 spread vs8 cached CCD vs8 frequency CCD,streaming,10s warmup+20s measured',
             'productive':'Cold default-auto with min8/max16 bound, cached restart, cold CPU-load episode, high-reserve restart; each below600s donation grace',
             'scope':'Native Windows only. High reserve simulates a reduced memory budget; no claim of actual OS memory-pressure validation.'})

    def check(self):
        assert time.monotonic()-self.started < 2700, '45-minute total deadline'
        assert time.time()<self.stop_before, 'Desktop must be released before cloud collection'
        state=json.loads((Path(os.environ['LOCALAPPDATA'])/'GpuQ/operator-state.json').read_text(encoding='utf-8-sig'))
        age=time.time()*1000-state['updatedAtUnixMs']
        assert state['schemaVersion']==3 and -5000<=age<60000 and not state['gamingActive'], 'Gaming reservation/state stale'
        j=json.loads(subprocess.check_output([r'D:\AI\gpuq\gpuq.exe','show',self.jobid],text=True,timeout=10))
        assert j['state']=='running', 'Owned exclusive reservation lost'

    def start(self,args,label,mask):
        assert K.SetProcessAffinityMask(K.GetCurrentProcess(),mask)
        try:
            log=(self.out/(label+'.log')).open('w',encoding='utf-8')
            err=(self.out/(label+'.err')).open('w',encoding='utf-8')
            p=subprocess.Popen(args,cwd=self.root,stdout=log,stderr=err,creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        finally:
            assert K.SetProcessAffinityMask(K.GetCurrentProcess(),0xffffffff)
        self.children.append(p)
        if not K.AssignProcessToJobObject(self.job,W.HANDLE(int(p._handle))):
            p.kill(); p.wait(); raise OSError(C.get_last_error(),'AssignProcessToJobObject failed')
        assert K.SetPriorityClass(W.HANDLE(int(p._handle)),0x4000)  # below normal
        actual=C.c_size_t(); system=C.c_size_t()
        K.GetProcessAffinityMask.argtypes=[W.HANDLE,C.POINTER(C.c_size_t),C.POINTER(C.c_size_t)]
        assert K.GetProcessAffinityMask(W.HANDLE(int(p._handle)),C.byref(actual),C.byref(system)) and actual.value==mask
        log.close();err.close()
        return p

    def stop(self,p):
        if p.poll() is None:
            try:
                p.send_signal(signal.CTRL_BREAK_EVENT);p.wait(timeout=15)
            except (OSError,subprocess.TimeoutExpired):
                p.kill();p.wait(timeout=10)
        return p.returncode

    def bench(self,label,cpus,seconds=20,rounds=2):
        self.check(); mask=sum(1<<c for c in cpus); path=self.out/(label+'.json')
        args=[str(self.exe),'--bench','--backend','cpu','--threads',str(len(cpus)),'--disable-cpu-autotune-threads','--bench-kind','backend','--cpu-page-mode','regular','--cpu-affinity','os','--bench-cpu-kernel','avx512-256-stream','--bench-secs',str(seconds),'--bench-rounds',str(rounds),'--bench-warmup-rounds','1','--bench-output',str(path),'--ui','plain','--data-dir',str(self.root/'bench-config')]
        start=time.monotonic(); p=self.start(args,label,mask)
        try:
            while p.poll() is None:
                self.check();assert time.monotonic()-start<180;time.sleep(3)
            assert p.returncode==0,(label,p.returncode)
        finally:self.stop(p)
        r=json.loads(path.read_text()); assert r['environment']['runtime_environment']=='native'
        assert r['environment']['target_triple']=='x86_64-pc-windows-msvc'
        assert r['environment']['git_commit']==json.loads((self.root/'source.json').read_text())['commit']
        identity=r['environment']['cpu_identity']
        assert identity['vendor']=='AuthenticAMD' and (identity['family'],identity['model'])==(26,68)
        assert r['pow_fingerprint']=={'memory_kb':2097152,'iterations':1,'parallelism':1,'output_len':32,'header_base_len':92}
        assert r['cpu_threads']==len(cpus) and r['config_fingerprint']['cpu_kernel']=='avx512-256-stream'
        for s in r['runs']:
            assert sum(b['memory_regular_bytes'] for b in s['backend_runs'])==len(cpus)*2*GI
            for b in s['backend_runs']:
                for f in ['memory_allocation_failures','dropped_events','assignment_enqueue_timeouts','assignment_execution_timeouts','control_enqueue_timeouts','control_execution_timeouts']: assert b[f]==0
        hps=statistics.mean(s['hashes']/s['elapsed_secs'] for s in r['runs'])
        save(self.out/(label+'.meta.json'),{'command':args,'cpus':cpus,'mask':mask,'exit_code':p.returncode,'hps':hps,'elapsed':time.monotonic()-start})
        print(label,hps,flush=True);return hps

    def productive(self,label,seconds,cache,load=False,reserve=None):
        assert seconds<=540
        self.check();episode=self.out/label;episode.mkdir(); cache.mkdir(exist_ok=True)
        server=Server(('127.0.0.1',0))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        args=[str(self.exe),'--mode','pool','--pool-url',f'127.0.0.1:{server.server_address[1]}','--address',address(),'--pool-worker','native-validation','--backend','cpu','--cpu-page-mode','regular','--cpu-affinity','auto','--cpu-autotune-min-threads','8','--cpu-autotune-max-threads',str(getattr(self,'worker_max',16)),'--cpu-autotune-config',str(cache/'tuning.json'),'--data-dir',str(cache/'config'),'--ui','plain','--stats-secs','5']
        if reserve is not None:args+=['--cpu-memory-reserve-percent',str(reserve)]
        before={p.name:json.loads(p.read_text()) for p in cache.glob('tuning.json*') if p.suffix=='.json'}
        start=time.monotonic(); p=None; burners=[]; snapshots=[]
        try:
            p=self.start(args,label,0x55555555)
            while time.monotonic()-start<seconds:
                self.check();assert p.poll() is None,(label,p.returncode)
                assert not server.errors,server.errors
                assert sum(e['method']=='login' for e in server.events)<=1,'Unexpected fixture reconnect'
                age=time.monotonic()-start
                if load and 45<=age<125 and not burners:
                    for n in [0,2]: burners.append(self.start([sys.executable,__file__,'--burn','100'],label+'-load'+str(n),1<<n))
                if load and age>=125:
                    for b in burners:self.stop(b)
                snapshots.append({'elapsed':age,'memory':memory()})
                time.sleep(5)
        finally:
            for b in burners:self.stop(b)
            code=self.stop(p) if p else None
            server.shutdown();server.server_close()
            after={p.name:json.loads(p.read_text()) for p in cache.glob('tuning.json*') if p.suffix=='.json'}
            save(episode/'record.json',{'command':args,'seconds':time.monotonic()-start,'exit_code':code,'cache_before':before,'cache_after':after,'fixture_events':server.events,'errors':server.errors,'snapshots':snapshots})
        text=(self.out/(label+'.log')).read_text()+(self.out/(label+'.err')).read_text()
        assert not server.errors and any(e['method']=='login' for e in server.events)
        assert 'quarantined' not in text.lower()
        assert 'switching to dev' not in text.lower()
        print(label,'complete',flush=True)
        return after,text

    def run(self):
        if self.resume:
            pairs=json.loads((self.out/'count-pairs.json').read_text())
            placement=json.loads((self.out/'placement.json').read_text())
        else:
            for name in ['verify_cpu_kernels','verify_streaming_dispatch']:
                self.check()
                exe=self.root/'target/release/examples'/(name+'.exe')
                started=time.monotonic();p=self.start([str(exe)],name,1)
                try:
                    while p.poll() is None:
                        self.check();assert time.monotonic()-started<240;time.sleep(3)
                    assert p.returncode==0,(name,p.returncode)
                    save(self.out/(name+'.identity.json'),{'sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'exit_code':p.returncode,'elapsed':time.monotonic()-started})
                finally:self.stop(p)
                print(name,'PASS',flush=True)
            spread=[0,2,4,6,16,18,20,22];physical=list(range(0,32,2))
            pairs=[]
            for n in range(1,5):
                pair={}
                order=[('eight',spread),('sixteen',physical)]
                if n%2==0:order.reverse()
                for label,cpus in order:pair[label]=self.bench(f'count-p{n}-{label}',cpus)
                pairs.append(pair);save(self.out/'count-pairs.json',pairs)
            cases=[('spread',spread),('cache',list(range(0,16,2))),('frequency',list(range(16,32,2)))]
            placement={k:[] for k,_ in cases}
            for n,order in enumerate([cases,list(reversed(cases))],1):
                for label,cpus in order:placement[label].append(self.bench(f'ccd-p{n}-{label}',cpus,10,2))
            save(self.out/'placement.json',placement)
        cold,text=self.productive('cold',540,self.root/'cold-cache')
        warm,warmtext=self.productive('warm',150,self.root/'cold-cache')
        loaded,loadtext=self.productive('load',300,self.root/'load-cache',load=True)
        reduced,reducedtext=self.productive('reserve',75,self.root/'cold-cache',reserve=95)
        assert any(w['kernel']=='avx512-256-stream' for c in cold.values() for w in c.get('winners',[])), 'Cold auto path did not confirm streaming'
        assert 'restoring confirmed avx512-256-stream' in warmtext,'Warm restart did not restore streaming'
        assert 'confirmed faster avx512-256-stream' in text, 'Cold runtime did not report its streaming choice'
        assert 'waiting for RAM' in reducedtext, 'High reserve did not exercise parked startup'
        assert reduced == warm, 'Parked startup changed the saved tuning evidence'
        assert self.sha==hashlib.sha256(self.exe.read_bytes()).hexdigest()
        save(self.out/'summary.json',{'count_means':{k:statistics.mean(p[k] for p in pairs) for k in ['eight','sixteen']},'paired_eight_vs_sixteen_pct':[100*(p['eight']/p['sixteen']-1) for p in pairs],
             'geometric_eight_vs_sixteen_pct':100*(math.exp(statistics.mean(math.log(p['eight']/p['sixteen']) for p in pairs))-1),
             'placement_means':{k:statistics.mean(v) for k,v in placement.items()},'cold_streaming_confirmed':True,'warm_streaming_restored':True,'high_reserve_parked':True,'memory_pressure_scope':'Controlled high reserve on restart; not actual OS memory-pressure injection.'})
        (self.out/'COMPLETE').write_text('Native count/placement and automatic lifecycle validation passed.\n')

    def close(self):
        for p in self.children:self.stop(p)
        assert all(p.poll() is not None for p in self.children)
        K.CloseHandle(self.job)
        save(self.out/'cleanup.json',{'owned_children':[{'pid':p.pid,'exit_code':p.returncode} for p in self.children],'all_children_stopped':True,'memory_after':memory(),'elapsed':time.monotonic()-self.started})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path);parser.add_argument('--job');parser.add_argument('--burn',type=int)
    args=parser.parse_args()
    if args.burn:
        end=time.monotonic()+args.burn;x=1
        while time.monotonic()<end:x=(x*1664525+1013904223)&0xffffffff
    else:
        campaign=Campaign(args.root,args.job)
        try:campaign.run()
        finally:campaign.close()
