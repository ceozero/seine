#!/usr/bin/env python3
"""Own bounded leases, frozen uploads and verified downloads for this campaign.

Infrastructure and SSH material stay in ignored data/. Run start only after
coordinating the shared vCPU quota. $10 is the separately authorized total cap.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
DATA = REPO/'data/followups-20261025'


def call(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('action',choices=['start','upload','run','status','collect','cleanup'])
    p.add_argument('host',choices=['intel','skylake','epyc'])
    a=p.parse_args();root=DATA/(a.host+'-lease')
    cloud=[sys.executable,str(HERE/'cloud.py')]
    ssh=['ssh','-F',str(root/'ssh-config'),'ep']
    if a.action=='start':
        # Three maximum 2-hour rentals reserve $6.16864 compute, plus $2 for disk,
        # IPv4 and transfer. Retries need a new explicit ledger reservation.
        ledger=DATA/'budget.json'
        if not ledger.exists():
            ledger.write_text(json.dumps({'cap_usd':10,'reserved_usd':8.16864,'leases':{'skylake':{'type':'c5.4xlarge','max_minutes':120,'max_compute_usd':1.36},'intel':{'type':'c6i.4xlarge','max_minutes':120,'max_compute_usd':1.36},'epyc':{'type':'c8a.8xlarge','max_minutes':120,'max_compute_usd':3.44864}},'other_reserved_usd':2},indent=2)+'\n')
        b=json.loads(ledger.read_text());assert b['reserved_usd']<=b['cap_usd']
        config=json.loads((DATA/'infrastructure.json').read_text())
        spec=b['leases'][a.host]
        try:
            call(cloud+['launch','--root',str(root),'--type',spec['type'],'--minutes',str(spec['max_minutes']),'--image',config['ImageId'],'--vpc',config['VpcId'],'--subnet',config['SubnetId']],stdout=subprocess.DEVNULL)
            for attempt in range(12):
                result=subprocess.run(cloud+['connect','--root',str(root)],capture_output=True,text=True,timeout=65)
                if result.returncode == 0: break
                if attempt == 11: raise RuntimeError('instance networking did not become ready: '+result.stderr)
                time.sleep(3)
        except BaseException:
            if (root/'session.json').exists(): call(cloud+['cleanup','--root',str(root)])
            else:
                (root/'ssh-key').unlink(missing_ok=True)
                (root/'ssh-key.pub').unlink(missing_ok=True)
            raise
        print('Created bounded '+a.host+' lease; SSH may still be booting.',flush=True)
    elif a.action=='upload':
        call(ssh+['mkdir -p /home/ubuntu/followups'],timeout=20)
        frozen=DATA/'frozen'
        files=[str(p) for p in frozen.iterdir() if p.is_file()]+[str(p) for p in HERE.glob('*.py') if p.name not in ['cloud.py','lease.py']]
        call(['scp','-q','-F',str(root/'ssh-config'),*files,'ep:/home/ubuntu/followups/'],timeout=120)
        call(ssh+['chmod +x /home/ubuntu/followups/control /home/ubuntu/followups/candidate /home/ubuntu/followups/mine-reduced /home/ubuntu/followups/test-reduced'],timeout=20)
        print('Frozen inputs uploaded.',flush=True)
    elif a.action=='run':
        call(ssh+['sudo systemd-run --quiet --unit=seine-followups-controller --uid=ubuntu --property=WorkingDirectory=/home/ubuntu/followups --property=RuntimeMaxSec=6900 --property=TimeoutStopSec=120 --property=KillSignal=SIGINT --property=StandardOutput=append:/home/ubuntu/followups/controller.log --property=StandardError=append:/home/ubuntu/followups/controller.log /usr/bin/python3 /home/ubuntu/followups/run_native.py '+a.host],timeout=20)
        print('Native controller started; separate controller and VM expiry limits active.',flush=True)
    elif a.action=='status':
        call(ssh+['systemctl show seine-followups-controller --property=ActiveState --property=ExecMainStatus; tail -n 12 /home/ubuntu/followups/controller.log; ls /home/ubuntu/followups/results | tail -n 10'],timeout=20)
    elif a.action=='collect':
        call(['scp','-q','-F',str(root/'ssh-config'),'ep:/home/ubuntu/followups/results.tar.gz',str(root/'results.tar.gz')],timeout=120)
        dest=root/'collected';dest.mkdir(exist_ok=False)
        with tarfile.open(root/'results.tar.gz') as archive:
            archive.extractall(dest,filter='data')
        manifest=json.loads((dest/'result-manifest.json').read_text())
        for name,digest in manifest.items():
            assert hashlib.sha256((dest/name).read_bytes()).hexdigest()==digest,name
        record={'files_verified':len(manifest),'archive_sha256':hashlib.sha256((root/'results.tar.gz').read_bytes()).hexdigest(),'outcome':json.loads((dest/'results/outcome.json').read_text())}
        (root/'archive-verification.json').write_text(json.dumps(record,indent=2)+'\n')
        print(json.dumps(record),flush=True)
    else:
        call(cloud+['cleanup','--root',str(root)])


if __name__=='__main__': main()
