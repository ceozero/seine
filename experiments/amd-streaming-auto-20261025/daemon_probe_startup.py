"""Ryzen startup-streaming check (aecc267): starts on streaming, then sweeps the rest.

Variant of daemon_probe.py. Expects the validated-identity startup message and a
streaming winner after avx512/avx2 are compared against it; then an exact-context
restart restores streaming. Original protocol below.

Long native default-kernel trial at one bounded count, then exact-context restart.

Uses the unchanged production miner and a local daemon API. Unlike pool mode,
the fee-address transition cannot connect to an external pool. Count is bounded
to eight solely to isolate kernel/cache behavior from the separately owned joint
tuner investigation. No kernel is forced. This is not unconstrained count tuning.
"""
import argparse
import json
from pathlib import Path
import threading
import time

from daemon_fixture import Server
from fixture import address
from native_run import Campaign,save,memory


def caches(path):
    return {p.name:json.loads(p.read_text()) for p in path.glob('tuning.json*') if p.suffix=='.json'}


class Probe(Campaign):
    def episode(self,label,seconds):
        out=self.out/label;out.mkdir()
        cache=self.root/'cache';cache.mkdir(exist_ok=True)
        before=caches(cache); server=Server()
        threading.Thread(target=server.serve_forever,daemon=True).start()
        args=[str(self.exe),'--mode','daemon','--api-url',f'http://127.0.0.1:{server.server_port}','--token','native-fixture','--address',address(),'--backend','cpu','--cpu-page-mode','regular','--cpu-affinity','auto','--cpu-autotune-min-threads','8','--cpu-autotune-max-threads','8','--cpu-autotune-config',str(cache/'tuning.json'),'--data-dir',str(cache/'config'),'--ui','plain','--stats-secs','5']
        start=time.monotonic();p=None;samples=[];confirmed_at=None
        try:
            self.check();p=self.start(args,label,0x55555555)
            while time.monotonic()-start<seconds:
                self.check();assert p.poll() is None,(label,p.returncode)
                assert not server.errors,server.errors
                elapsed=time.monotonic()-start
                current=caches(cache)
                winners=[w for c in current.values() for w in c.get('winners',[]) if w['kernel']=='avx512-256-stream']
                if winners and confirmed_at is None:confirmed_at=elapsed
                samples.append({'elapsed':elapsed,'memory':memory(),'streaming_cached':bool(winners)})
                if label=='cold' and confirmed_at is not None and elapsed>=max(360,confirmed_at+30):break
                time.sleep(5)
        finally:
            code=self.stop(p) if p else None
            server.finish()
            after=caches(cache)
            save(out/'record.json',{'command':args,'seconds':time.monotonic()-start,'exit_code':code,'cache_before':before,'cache_after':after,'http_events':server.events,'errors':server.errors,'samples':samples,'confirmed_at':confirmed_at})
        text=(self.out/(label+'.log')).read_text()+(self.out/(label+'.err')).read_text()
        assert not server.errors and any('/api/mining/blocktemplate' in e['path'] for e in server.events)
        assert 'quarantined' not in text.lower()
        print(label,'complete',confirmed_at,flush=True)
        return after,text

    def run(self):
        save(self.out/'protocol.json',{'source_commit':json.loads((self.root/'source.json').read_text())['commit'],'binary_sha256':self.sha,'job_id':self.jobid,'stop_before_epoch':self.stop_before,'mode':'daemon','worker_bounds':[8,8],'page_mode':'regular','cold_max_seconds':1020,'cold_early_stop':'at least360seconds and30seconds after a confirmed cache winner','warm_seconds':90,'scope':'Startup-streaming variant (aecc267): validated start, sweep vs avx512/avx2, exact-context restart; no unconstrained count claim.'})
        cold,text=self.episode('cold',1020)
        assert any(w['kernel']=='avx512-256-stream' for c in cold.values() for w in c.get('winners',[])), 'No streaming winner after bounded long trial'
        assert 'starting avx512-256-stream path validated for this CPU' in text, 'Validated startup path was not applied'
        warm,text=self.episode('warm',90)
        assert 'restoring confirmed avx512-256-stream' in text
        save(self.out/'summary.json',{'streaming_kept_after_sweep':True,'exact_context_restart_restored':True,'workers':8,'all_requests_loopback':True,'cold_cache':cold,'warm_cache':warm})
        (self.out/'COMPLETE').write_text('Native automatic streaming and exact-context restart passed.\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path);parser.add_argument('--job');args=parser.parse_args()
    probe=Probe(args.root,args.job)
    try:probe.run()
    finally:probe.close()
