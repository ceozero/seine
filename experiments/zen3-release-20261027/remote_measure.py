#!/usr/bin/env python3
import datetime,hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path
from statistics import mean
ROOT=Path('/opt/seine-headline');OUT=ROOT/'results';OUT.mkdir(exist_ok=True)
POOL=Path('/sys/kernel/mm/hugepages/hugepages-1048576kB/nr_hugepages')
kind='zen3'
def save(name,data):
 p=OUT/name;t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(data,indent=2)+'\n');t.replace(p)
def command(argv,label,timeout=240):
 print(label,flush=True);start=time.monotonic()
 with (OUT/(label+'.log')).open('w') as log:
  proc=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,cwd=ROOT)
  try:code=proc.wait(timeout=timeout)
  finally:
   if proc.poll() is None:
    os.killpg(proc.pid,signal.SIGTERM)
    try:proc.wait(timeout=10)
    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
 elapsed=time.monotonic()-start
 assert code==0,(label,code)
 return elapsed
def counters():
 vm={k:int(v) for k,v in (s.split() for s in Path('/proc/vmstat').read_text().splitlines())}
 cpu=list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:]))
 return {**{k:vm[k] for k in ('pswpin','pswpout','oom_kill')},'cpu_total':sum(cpu[:8]),'cpu_steal':cpu[7]}
def measure(role,label):
 kernel='avx2' if role=='baseline' else 'avx2-stream';binary=ROOT/role/'seine';before=counters()
 argv=['unshare','-n',str(binary),'--bench','--bench-kind','backend','--backend','cpu','--threads','16','--disable-cpu-autotune-threads','--bench-cpu-kernel',kernel,'--cpu-page-mode','auto','--bench-secs','120','--bench-rounds','1','--bench-warmup-rounds','1','--bench-output',str(OUT/(label+'.json')),'--data-dir',str(ROOT/'data'),'--telemetry','off','--ui','plain']
 elapsed=command(argv,label,400);after=counters();delta={k:after[k]-before[k] for k in before};d=json.loads((OUT/(label+'.json')).read_text())
 assert d['cpu_threads']==16 and d['config_fingerprint']['cpu_kernel']==kernel
 for run in d['runs']:
  assert run['hashes']==run['counted_hashes']+run['late_hashes']
  b=run['backend_runs'][0];assert b['memory_transparent_huge_workers']==16;assert b['memory_transparent_huge_bytes']==16*2*1024**3;assert b['memory_allocation_failures']==0
 assert all(delta[k]==0 for k in ('pswpin','pswpout','oom_kill')),delta
 steal=delta['cpu_steal']/max(1,delta['cpu_total']);assert steal<0.01,('steal exceeds 1%',steal)
 r={'label':label,'role':role,'kernel':kernel,'hps':d['avg_hps'],'total_hashes':d['total_hashes'],'whole_invocation_seconds':elapsed,'counter_delta':delta,'steal_fraction':steal,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'report_sha256':hashlib.sha256((OUT/(label+'.json')).read_bytes()).hexdigest()}
 save(label+'-measurement.json',r);print(json.dumps(r),flush=True);return r
runs=[];status='FAILED';failure=None
try:
 hw=json.loads(subprocess.check_output(['lscpu','-J'],text=True));save('lscpu.json',hw);facts={e['field'].rstrip(':'):e['data'] for e in hw['lscpu']};assert '7R13' in facts['Model name'],facts['Model name']
 save('context.json',{'started_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'kernel':subprocess.check_output(['uname','-r'],text=True).strip(),'memory':Path('/proc/meminfo').read_text(),'thp':Path('/sys/kernel/mm/transparent_hugepage/enabled').read_text()})
 for role in ('baseline','current'):
  command(['unshare','-n',str(ROOT/role/'verify_cpu_kernels')],role+'-parity',240)
  txt=(OUT/(role+'-parity.log')).read_text();assert 'avx2: PASS' in txt
  if role=='current':assert 'avx2-stream: PASS' in txt
 for i,role in enumerate(['baseline','current','current','baseline'],1):runs.append(measure(role,f'comparison-{i}-{role}'))
 save('summary.json',{'metric':'backend avg_hps: counted hashes / timed round elapsed including fence, excludes allocation, warmup, teardown','runs':runs});status='COMPLETE'
except BaseException as e:failure=repr(e);raise
finally:
 save('outcome.json',{'status':status,'failure':failure,'completed_runs':len(runs)})
 save('manifest.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file() and p.name!='manifest.json'})
