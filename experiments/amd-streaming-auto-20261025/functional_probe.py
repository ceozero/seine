"""Functional cache restart/park/recovery test, not a throughput measurement.

Normal background work is allowed. Owned children use a 25% Windows Job CPU cap,
a 20 GiB commitment ceiling, and eight 2 GiB arenas. Gaming Mode aborts the test.
The cache is copied unchanged from the independently confirmed native load run.
"""
import argparse
import ctypes as C
from ctypes import wintypes as W
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import time

from native_run import Campaign,Extended,K,GI,memory,save


class CpuRate(C.Structure):
    _fields_=[('flags',W.DWORD),('rate',W.DWORD)]


class Functional(Campaign):
    def __init__(self,root):
        self.root=root;self.out=root/'results';self.out.mkdir(exist_ok=False)
        self.jobid=None;self.children=[];self.started=time.monotonic();self.worker_max=8
        self.stop_before=datetime.datetime.fromisoformat(json.loads((root/'deadline.json').read_text())['stop_before_utc']).timestamp()
        assert self.stop_before-time.time()>=360
        self.exe=root/'target/release/seine.exe';self.sha=hashlib.sha256(self.exe.read_bytes()).hexdigest()
        assert self.sha==json.loads((root/'provenance.json').read_text())['binary_sha256']
        self.job=K.CreateJobObjectW(None,None);assert self.job
        limits=Extended();limits.basic.flags=0x2000|0x200;limits.job_memory=20*GI
        assert K.SetInformationJobObject(self.job,9,C.byref(limits),C.sizeof(limits))
        rate=CpuRate(1|4,2500)
        assert K.SetInformationJobObject(self.job,15,C.byref(rate),C.sizeof(rate)),C.get_last_error()
        self.check();assert memory()['available']>=26*GI
        save(self.out/'protocol.json',{'purpose':'Functional cache restore/parking/recovery only; no throughput claim','source_commit':json.loads((root/'source.json').read_text())['commit'],'binary_sha256':self.sha,'cpu_rate_cap_percent':25,'job_memory_limit':20*GI,'worker_bounds':[8,8],'page_mode':'regular','cache_source':'Unmodified confirmed load-run cache','background_work_allowed':True,'gaming_abort':True,'deadline_seconds':360,'stop_before_epoch':self.stop_before})

    def check(self):
        assert time.monotonic()-self.started<360 and time.time()<self.stop_before
        state=json.loads((Path(os.environ['LOCALAPPDATA'])/'GpuQ/operator-state.json').read_text(encoding='utf-8-sig'))
        age=time.time()*1000-state['updatedAtUnixMs']
        assert state['schemaVersion']==3 and -5000<=age<60000 and not state['gamingActive'],'Gaming reservation/state stale'
        assert memory()['available']>=8*GI,'Stop functional test to preserve memory headroom'

    def run(self):
        warm,text=self.productive('warm',60,self.root/'cache')
        times=re.findall(r'([\d.]+)s\s+INFO\s+MINER\s+cpu-autotune \| restoring confirmed avx512-256-stream',text)
        assert times and float(times[0])<30,'Exact-context restart did not promptly restore streaming'
        first_restore=float(times[0])
        parked,text=self.productive('parked',30,self.root/'cache',reserve=95)
        assert 'waiting for RAM' in text and parked==warm,'Parked start changed cache or did not park'
        assert max([0]+[int(n) for n in re.findall(r'\bhashes=(\d+)',text)])==0
        recovered,text=self.productive('recovery',60,self.root/'cache')
        times=re.findall(r'([\d.]+)s\s+INFO\s+MINER\s+cpu-autotune \| restoring confirmed avx512-256-stream',text)
        assert times and float(times[0])<30
        assert max([0]+[int(n) for n in re.findall(r'\bhashes=(\d+)',text)])>0
        save(self.out/'summary.json',{'warm_restore_seconds':first_restore,'recovery_restore_seconds':float(times[0]),'parked_cache_unchanged':True,'scope':'Functional only, fixed research count bound, controlled high reserve; no OS memory-pressure or unconstrained convergence claim.'})
        assert self.sha==hashlib.sha256(self.exe.read_bytes()).hexdigest()
        (self.out/'COMPLETE').write_text('Native cache restore, parked startup and recovery passed.\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path);args=parser.parse_args()
    probe=Functional(args.root)
    try:probe.run()
    finally:probe.close()
