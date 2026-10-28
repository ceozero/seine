#!/usr/bin/env python3
import datetime,hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path
from statistics import mean
ROOT=Path('/opt/seine-headline');OUT=ROOT/'results'/'cached-start-ab';OUT.mkdir(parents=True,exist_ok=True)
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
import pwd,re,threading
from fixture import Server,Fixture,fixture_address,SERVER_EVENTS

def counters():
 vals={k:int(v) for k,v in (line.split() for line in Path('/proc/vmstat').read_text().splitlines())}
 return {k:vals[k] for k in ('pswpin','pswpout','oom_kill')}
def live(role,label,seconds,data):
 data.mkdir(exist_ok=True); user=pwd.getpwnam('seinebench')
 for p in [data,*data.rglob('*')]:os.chown(p,user.pw_uid,user.pw_gid)
 argv=['setpriv','--reuid=seinebench','--regid=seinebench','--init-groups',str(ROOT/role/'seine'),'--mode','pool','--pool-url','stratum+tcp://127.0.0.1:3333','--address',fixture_address(),'--backend','cpu','--data-dir',str(data),'--telemetry','off','--ui','plain','--stats-secs','5']
 print('LIVE START '+label,flush=True);before=counters();start=time.monotonic();samples=[];cache=data/'seine.cpu-autotune.json'
 save(label+'-start.json',{'argv':argv,'cache_exists':cache.exists(),'before':before})
 with (OUT/(label+'.log')).open('w') as log:
  proc=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,cwd=ROOT,env={**os.environ,'HOME':str(data)})
  try:
   while time.monotonic()-start<seconds:
    assert proc.poll() is None,('early live exit',label,proc.returncode)
    sample={'elapsed':time.monotonic()-start}
    try:
     p=Path(f'/proc/{proc.pid}/smaps_rollup');sample['memory']={s.split(':')[0]:s.split(':',1)[1].strip() for s in p.read_text().splitlines() if ':' in s}
    except (FileNotFoundError,ProcessLookupError):pass
    text=(OUT/(label+'.log')).read_text(errors='replace');counts=re.findall(r'\bhashes=(\d+)',text);sample['logged_hashes']=max(map(int,counts),default=0)
    samples.append(sample);save(label+'-samples.json',samples)
    time.sleep(min(10,max(0,seconds-(time.monotonic()-start))))
  finally:
   if proc.poll() is None:
    os.killpg(proc.pid,signal.SIGINT)
    try:proc.wait(timeout=90)
    except subprocess.TimeoutExpired:
     os.killpg(proc.pid,signal.SIGKILL);proc.wait();raise RuntimeError('live shutdown timeout '+label)
 elapsed=time.monotonic()-start;after=counters();delta={k:after[k]-before[k] for k in before}
 txt=(OUT/(label+'.log')).read_text(errors='replace');counts=re.findall(r'\bhashes=(\d+)',txt);hashes=max(map(int,counts),default=0)
 result={'role':role,'binary_sha256':hashlib.sha256((ROOT/role/'seine').read_bytes()).hexdigest(),'label':label,'seconds_requested':seconds,'exit_code':proc.returncode,'whole_invocation_seconds':elapsed,'logged_completed_hashes':hashes,'whole_invocation_hps_lower_bound':hashes/elapsed,'counter_delta':delta,'cache_exists':cache.exists(),'samples':len(samples)}
 if cache.exists():save(label+'-cache.json',json.loads(cache.read_text()))
 save(label+'-measurement.json',result);print(json.dumps(result),flush=True)
 assert proc.returncode in (0,130,-2),(label,proc.returncode)
 assert hashes>0,('no logged hashes',label)
 assert all(v==0 for v in delta.values()),('swap/OOM invalidates run',delta)
 assert not re.search(r'backend.*quarantin|allocation failed|panicked at',txt,re.I),('backend fault',label)
 return result


import shutil
runs=[];status='FAILED';failure=None;server=None
try:
 assert int(POOL.read_text())==0,'original page reservation must be restored'
 server=Server(('127.0.0.1',3333),Fixture);threading.Thread(target=server.serve_forever,daemon=True).start()
 for role in ('current','candidate'):
  data=ROOT/('ab-cold-'+role);assert not data.exists()
  runs.append(live(role,'cold-'+role,300,data))
  for p in data.iterdir():
   if p.is_file() and p.suffix=='.json':shutil.copy2(p,OUT/(role+'-seed-'+p.name))
 for i,role in enumerate(('current','candidate','candidate','current'),1):
  data=ROOT/f'ab-restart-{i}-{role}';assert not data.exists()
  shutil.copytree(ROOT/('ab-cold-'+role),data)
  runs.append(live(role,f'cached-{i}-{role}',180,data))
 save('fixture-events.json',SERVER_EVENTS)
 save('summary.json',{'metric':'logged completed hashes / whole-invocation seconds; lower bound','cold_seconds':300,'memory_limit_gib':192,'cached_seconds':180,'runs':runs})
 status='COMPLETE'
except BaseException as e:failure=repr(e);raise
finally:
 if server:server.shutdown();server.server_close()
 save('outcome.json',{'status':status,'failure':failure,'completed_runs':len(runs)})
 save('manifest.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file() and p.name!='manifest.json'})
