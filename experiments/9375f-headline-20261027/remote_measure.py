#!/usr/bin/env python3
import datetime,hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path
from statistics import mean
ROOT=Path('/opt/seine-headline');OUT=ROOT/'results';OUT.mkdir(exist_ok=True)
POOL=Path('/sys/kernel/mm/hugepages/hugepages-1048576kB/nr_hugepages')
kind='9575'
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
def reserve(n):
 POOL.write_text(str(n));assert int(POOL.read_text())==n,('hugepage allocation failed',n,POOL.read_text())
def measure(role,threads,seconds,label):
 reserve(threads*2)
 binary=ROOT/role/'seine'
 argv=['unshare','-n',str(binary),'--bench','--bench-kind','end-to-end','--backend','cpu','--threads',str(threads),'--disable-cpu-autotune-threads','--bench-cpu-kernel','avx512-256-stream','--cpu-page-mode','large-1g','--bench-secs',str(seconds),'--bench-rounds','1','--bench-warmup-rounds','0','--bench-output',str(OUT/(label+'.json')),'--data-dir',str(ROOT/'data'),'--telemetry','off','--ui','plain']
 elapsed=command(argv,label,seconds+120);d=json.loads((OUT/(label+'.json')).read_text());assert d['cpu_threads']==threads and d['rounds']==1
 assert d['config_fingerprint']['cpu_kernel']=='avx512-256-stream'
 hashes=0
 for run in d['runs']:
  assert run['hashes']==run['counted_hashes']+run['late_hashes'];assert len(run['backend_runs'])==1
  b=run['backend_runs'][0];assert b['hashes']==run['hashes'];assert b['memory_explicit_large_1g_workers']==threads;assert b['memory_explicit_large_1g_bytes']==threads*2*1024**3
  assert b['memory_allocation_failures']==0;hashes+=run['hashes']
 assert d['total_hashes']==hashes
 r={'role':role,'threads':threads,'seconds':seconds,'completed_hashes':hashes,'whole_invocation_seconds':elapsed,'whole_invocation_hps':hashes/elapsed,'benchmark_avg_hps':d['avg_hps'],'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'report_sha256':hashlib.sha256((OUT/(label+'.json')).read_bytes()).hexdigest(),'label':label,'cpu':d['environment']['cpu_brand']}
 save(label+'-measurement.json',r);print(json.dumps(r),flush=True);return r

status='FAILED';failure=None;original=int(POOL.read_text());allruns=[];headline_complete=False
try:
 hw=json.loads(subprocess.check_output(['lscpu','-J'],text=True));save('lscpu.json',hw)
 facts={e['field'].rstrip(':'):e['data'] for e in hw['lscpu']};assert '9375F' in facts['Model name'];assert facts['Socket(s)']=='1'
 save('context.json',{'started_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'kernel':subprocess.check_output(['uname','-r'],text=True).strip(),'memory':Path('/proc/meminfo').read_text(),'power_caps':{str(p):p.read_text() for p in Path('/sys/class/hwmon').glob('hwmon*/power*_cap')},'original_1g_pages':original,'thp':Path('/sys/kernel/mm/transparent_hugepage/enabled').read_text()})
 (OUT/'memory-dimms.txt').write_text(subprocess.check_output(['dmidecode','-t','memory'],text=True))
 reserve(3);command(['unshare','-n',str(ROOT/'current/verify_streaming_1g')],'current-1g-parity',240)
 assert (OUT/'current-1g-parity.log').read_text().count('PASS nonce=')==21
 screens=[measure('current',t,60,f'screen-t{t}') for t in [16,32,48,64]];allruns.extend(screens)
 winner=max(screens,key=lambda r:r['whole_invocation_hps'])['threads'];save('selection.json',{'threads':winner,'criterion':'highest screen whole-invocation completed-hash rate','fresh_confirmations':3})
 for i in range(1,4):allruns.append(measure('current',winner,120,f'confirm-{i}-t{winner}'))
 save('summary.json',{'scope':'completed hashes / whole process invocation including allocation, work, fences, teardown','warmup_rounds':0,'manual_page_backing':'explicit_1g_hugetlb','runs':allruns,'live_runs':[]})
 headline_complete=True;save('headline-outcome.json',{'status':'COMPLETE','completed_runs':len(allruns)})
 status='COMPLETE'
except BaseException as e:failure=repr(e);raise
finally:
 try:POOL.write_text(str(original))
 except Exception as e:failure=str(failure)+';restore:'+repr(e);status='FAILED'
 save('outcome.json',{'status':status,'failure':failure,'completed_runs':len(allruns),'headline_complete':headline_complete,'pages_restored':int(POOL.read_text())==original})
 save('manifest.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file() and p.name!='manifest.json'})
