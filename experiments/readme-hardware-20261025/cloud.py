#!/usr/bin/env python3
"""Campaign-owned EC2 spot leases for the README hardware benchmarks.

Adapted from ../cpu-campaign-20261024/cloud.py (seine-release-v0.2.22 tree).
Only instances whose IDs are recorded in this campaign's ledger AND carry the
tag Experiment=readme-hardware-20261025 are ever terminated. The benchmark IAM
role only permits Project=seine-avx2-validation (shared with other sessions), so
ownership is never inferred from Project alone. EC2 key-pair APIs are denied to
the role: a local temporary ed25519 key is injected through user-data instead.
Private state and keys live in ignored data/readme-hardware-20261025/.
"""
import base64
import datetime as dt
import ipaddress
import json
import math
import pathlib
import shlex
import subprocess
import time
import urllib.request

REPO = pathlib.Path(__file__).resolve().parents[2]
ROOT = REPO / 'data/readme-hardware-20261025'
EXPERIMENT = 'readme-hardware-20261025'
CAMPAIGN = 'seine-readme-benchmarks'
PROJECT = 'seine-avx2-validation'  # IAM-required tag value for this role
BUDGET_STOP_USD = 67.0  # cap raised to $70 by the user at ~03:55 UTC (was $30 / stop $28)
TIMER_MINUTES = 50  # wider 4-count sweeps (was 40)
EBS_GIB = 16
EBS_USD_PER_GIB_MONTH = 0.08
IPV4_USD_PER_HOUR = 0.005
TRANSFER_CONTINGENCY_USD = 0.10  # per lease; downloads are a few MB
AMI = {'amd64': 'ami-0d6dd9e8265d48906', 'arm64': 'ami-09a93d801db0bafae'}  # Ubuntu 24.04, SSM 2026-10-25


def now():
    return dt.datetime.now(dt.timezone.utc)


def save(path, obj):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2, default=str) + '\n')
    tmp.replace(path)


def aws(service, action, *args, timeout=90):
    result = subprocess.run(['aws', '--profile', 'seine-bench', '--region', 'us-east-1',
                             service, action, *args, '--output', 'json'],
                            capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return json.loads(result.stdout or '{}')


def ledger():
    path = ROOT / 'ledger.json'
    return json.loads(path.read_text()) if path.exists() else {'leases': [], 'security_group': None, 'events': []}


def persist(s):
    save(ROOT / 'ledger.json', s)


def event(s, **kw):
    s.setdefault('events', []).append({'at': now().isoformat(), **kw})


def ondemand_price(instance_type):
    filters = [{'Type': 'TERM_MATCH', 'Field': k, 'Value': v} for k, v in {
        'instanceType': instance_type, 'location': 'US East (N. Virginia)', 'operatingSystem': 'Linux',
        'tenancy': 'Shared', 'preInstalledSw': 'NA', 'capacitystatus': 'Used'}.items()]
    raw = subprocess.run(['aws', '--profile', 'seine-bench', '--region', 'us-east-1', 'pricing', 'get-products',
                          '--service-code', 'AmazonEC2', '--filters', json.dumps(filters), '--output', 'json'],
                         capture_output=True, text=True, timeout=90, check=True).stdout
    retrieved = now()
    (ROOT / 'prices').mkdir(exist_ok=True)
    (ROOT / 'prices' / f'ondemand-{instance_type}-{retrieved:%H%M%S}.json').write_text(raw)
    values = []
    for entry in json.loads(raw)['PriceList']:
        product = json.loads(entry) if isinstance(entry, str) else entry
        for term in product.get('terms', {}).get('OnDemand', {}).values():
            for d in term['priceDimensions'].values():
                if d['unit'] == 'Hrs':
                    values.append(float(d['pricePerUnit']['USD']))
    assert len(values) == 1 and values[0] > 0, values
    return {'usd_per_hour': values[0], 'source': 'AWS Pricing API get-products', 'retrieved_utc': retrieved.isoformat()}


def spot_prices(instance_type, start=None, end=None):
    args = ['--instance-types', instance_type, '--product-descriptions', 'Linux/UNIX']
    if start:
        args += ['--start-time', start, '--end-time', end or now().isoformat()]
    else:
        args += ['--start-time', now().isoformat()]
    return aws('ec2', 'describe-spot-price-history', *args)['SpotPriceHistory']


def lease_cost(record):
    """Conservative upper bound and spot estimate for a lease, minutes rounded up."""
    start = dt.datetime.fromisoformat(record['launched_at'])
    end = dt.datetime.fromisoformat(record['verified_terminated_at']) if record.get('verified_terminated_at') else now()
    hours = math.ceil((end - start).total_seconds() / 60) / 60
    extras = hours * (IPV4_USD_PER_HOUR + EBS_GIB * EBS_USD_PER_GIB_MONTH / 730) + TRANSFER_CONTINGENCY_USD
    rate_cap = record['ondemand_usd_per_hour']  # spot can never bill above on-demand by default
    spot_rate = record.get('spot_max_seen_usd_per_hour') or rate_cap
    if record['lifecycle'] == 'on-demand':
        spot_rate = rate_cap
    return {'billable_hours_rounded_up_to_minute': hours,
            'conservative_usd': rate_cap * hours + extras,
            'expected_usd': spot_rate * hours + extras,
            'extras_usd': extras}


def committed_usd(s, include_open_reserve=True):
    total = 0.0
    for r in s['leases']:
        if r.get('verified_terminated_at'):
            total += lease_cost(r)['conservative_usd']
        elif include_open_reserve:
            total += r['reserved_usd']
    return total


def owned_info(ident):
    s = ledger()
    assert any(x['instance_id'] == ident for x in s['leases']), 'not a ledger-recorded lease'
    info = aws('ec2', 'describe-instances', '--instance-ids', ident)['Reservations'][0]['Instances'][0]
    tags = {t['Key']: t['Value'] for t in info.get('Tags', [])}
    assert tags.get('Experiment') == EXPERIMENT and tags.get('Campaign') == CAMPAIGN, tags
    return info


def ssh_args(ip):
    return ['-i', str(ROOT / 'ssh-key'), '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=accept-new',
            '-o', f'UserKnownHostsFile={ROOT}/known-hosts', '-o', 'ConnectTimeout=10',
            '-o', 'ServerAliveInterval=15']


def ssh(ip, command, timeout=120):
    result = subprocess.run(['ssh', *ssh_args(ip), 'ubuntu@' + ip, command],
                            capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f'SSH exit {result.returncode}: {result.stderr[-1500:]} {result.stdout[-1500:]}')
    return result.stdout


def scp(ip, source, destination, download=False, timeout=600):
    host = 'ubuntu@' + ip + ':'
    subprocess.run(['scp', '-q', '-r', *ssh_args(ip), host + source if download else source,
                    destination if download else host + destination], check=True, timeout=timeout)


def ensure_security_group(s):
    if s.get('security_group'):
        return s['security_group']
    address = urllib.request.urlopen('https://checkip.amazonaws.com', timeout=15).read().decode().strip()
    ipaddress.IPv4Address(address)
    vpc = aws('ec2', 'describe-vpcs', '--filters', 'Name=is-default,Values=true')['Vpcs'][0]['VpcId']
    tags = [{'ResourceType': 'security-group', 'Tags': [
        {'Key': 'Project', 'Value': PROJECT}, {'Key': 'Experiment', 'Value': EXPERIMENT},
        {'Key': 'Campaign', 'Value': CAMPAIGN}, {'Key': 'Name', 'Value': 'seine-readme-ssh'}]}]
    group = aws('ec2', 'create-security-group', '--group-name', 'seine-' + EXPERIMENT,
                '--description', 'Temporary Seine README benchmark SSH', '--vpc-id', vpc,
                '--tag-specifications', json.dumps(tags))['GroupId']
    s['security_group'] = group
    s['security_group_ingress_cidr'] = address + '/32'
    event(s, action='security group created', group=group, cidr=address + '/32')
    persist(s)  # record before ingress so cleanup ownership cannot be lost
    aws('ec2', 'authorize-security-group-ingress', '--group-id', group, '--protocol', 'tcp',
        '--port', '22', '--cidr', address + '/32')
    return group


def quota_room(lifecycle, vcpus):
    code = 'L-34B43A08' if lifecycle == 'spot' else 'L-1216C47A'
    limit = aws('service-quotas', 'get-service-quota', '--service-code', 'ec2', '--quota-code', code)['Quota']['Value']
    live = aws('ec2', 'describe-instances', '--filters',
               'Name=instance-state-name,Values=pending,running,stopping,shutting-down')['Reservations']
    used = 0
    for r in live:
        for i in r['Instances']:
            if i['InstanceType'][0] not in 'acdhimrtz':
                continue
            is_spot = i.get('InstanceLifecycle') == 'spot'
            if is_spot == (lifecycle == 'spot'):
                used += i['CpuOptions']['CoreCount'] * i['CpuOptions']['ThreadsPerCore']
    return {'limit': limit, 'used': used, 'free': limit - used, 'fits': used + vcpus <= limit}


def launch(label, instance_type, arch, allow_ondemand=True):
    s = ledger()
    assert not [r for r in s['leases'] if not r.get('verified_terminated_at')], 'an open lease already exists'
    od = ondemand_price(instance_type)
    reserve = od['usd_per_hour'] * (TIMER_MINUTES + 10) / 60 + 0.2
    committed = committed_usd(s)
    if committed + reserve > BUDGET_STOP_USD:
        raise RuntimeError(f'budget stop: committed {committed:.2f} + reserve {reserve:.2f} > {BUDGET_STOP_USD}')
    if not (ROOT / 'ssh-key').exists():
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(ROOT / 'ssh-key'),
                        '-C', EXPERIMENT], check=True)
    pubkey = (ROOT / 'ssh-key.pub').read_text().strip()
    group = ensure_security_group(s)
    s = ledger()
    expires = now() + dt.timedelta(minutes=TIMER_MINUTES + 2)
    # Shutdown timer is the very first action; EC2 converts it into termination.
    userdata = f"""#!/bin/bash
shutdown -h +{TIMER_MINUTES}
install -d -m 700 -o ubuntu -g ubuntu /home/ubuntu/.ssh
printf '%s\\n' {shlex.quote(pubkey)} >> /home/ubuntu/.ssh/authorized_keys
chown ubuntu:ubuntu /home/ubuntu/.ssh/authorized_keys
chmod 600 /home/ubuntu/.ssh/authorized_keys
"""
    tags = [{'Key': 'Project', 'Value': PROJECT}, {'Key': 'Experiment', 'Value': EXPERIMENT},
            {'Key': 'Campaign', 'Value': CAMPAIGN}, {'Key': 'Name', 'Value': 'seine-readme-' + label},
            {'Key': 'ExpiresAt', 'Value': expires.isoformat()}]
    offers = {x['Location'] for x in aws('ec2', 'describe-instance-type-offerings', '--location-type',
              'availability-zone', '--filters', 'Name=instance-type,Values=' + instance_type)['InstanceTypeOfferings']}
    subnets = {x['AvailabilityZone']: x['SubnetId'] for x in aws('ec2', 'describe-subnets', '--filters',
               'Name=default-for-az,Values=true')['Subnets'] if x['AvailabilityZone'] in offers}
    spot = {p['AvailabilityZone']: float(p['SpotPrice']) for p in spot_prices(instance_type)}
    zones = sorted(subnets, key=lambda z: spot.get(z, 1e9))
    attempts = []
    vcpus = 32
    plans = []
    q = quota_room('spot', vcpus)
    attempts.append({'quota_spot': q})
    if q['fits']:  # retried every launch: a refusal is free and the role may be added later
        plans += [('spot', z) for z in zones if z in spot]
    answer = None
    lifecycle = None
    def make_spec(kind, zone):
        spec = {'ImageId': AMI[arch], 'InstanceType': instance_type, 'MinCount': 1, 'MaxCount': 1,
                'SubnetId': subnets[zone], 'SecurityGroupIds': [group],
                'InstanceInitiatedShutdownBehavior': 'terminate', 'MetadataOptions': {'HttpTokens': 'required'},
                'UserData': base64.b64encode(userdata.encode()).decode(),
                'BlockDeviceMappings': [{'DeviceName': '/dev/sda1', 'Ebs': {
                    'VolumeSize': EBS_GIB, 'VolumeType': 'gp3', 'DeleteOnTermination': True}}],
                'TagSpecifications': [{'ResourceType': t, 'Tags': tags} for t in ('instance', 'volume')]}
        if kind == 'spot':
            spec['InstanceMarketOptions'] = {'MarketType': 'spot', 'SpotOptions': {
                'SpotInstanceType': 'one-time', 'InstanceInterruptionBehavior': 'terminate'}}
        return spec

    for kind, zone in plans:
        spec = make_spec(kind, zone)
        try:
            answer = aws('ec2', 'run-instances', '--cli-input-json', json.dumps(spec))
            lifecycle = kind
            attempts.append({'zone': zone, 'kind': kind, 'result': 'launched'})
            break
        except RuntimeError as error:
            attempts.append({'zone': zone, 'kind': kind, 'error': str(error)[:300]})
            if 'ServiceLinkedRoleCreationNotPermitted' in str(error):
                # Account lacks AWSServiceRoleForEC2Spot and this role may not create it:
                # spot is unavailable for every zone/type, so stop trying it.
                s['spot_blocked'] = {'at': now().isoformat(), 'reason': str(error)[:400]}
                event(s, action='spot unavailable (service-linked role missing)', error=str(error)[:400])
                persist(s)
                break
            if not any(x in str(error) for x in ('InsufficientInstanceCapacity', 'Unsupported',
                                                  'SpotMaxPriceTooLow', 'capacity-not-available')):
                raise
    if answer is None and allow_ondemand:
        q = quota_room('on-demand', vcpus)
        attempts.append({'quota_ondemand': q})
        if q['fits']:
            for zone in sorted(subnets):
                spec = make_spec('on-demand', zone)
                try:
                    answer = aws('ec2', 'run-instances', '--cli-input-json', json.dumps(spec))
                    lifecycle = 'on-demand'
                    attempts.append({'zone': zone, 'kind': 'on-demand', 'result': 'launched'})
                    break
                except RuntimeError as error:
                    attempts.append({'zone': zone, 'kind': 'on-demand', 'error': str(error)[:300]})
                    if 'InsufficientInstanceCapacity' not in str(error):
                        raise
    if answer is None:
        event(s, action='launch failed', label=label, type=instance_type, attempts=attempts)
        persist(s)
        raise RuntimeError('no capacity: ' + json.dumps(attempts)[:2000])
    inst = answer['Instances'][0]
    zone = inst['Placement']['AvailabilityZone']
    record = {'label': label, 'instance_id': inst['InstanceId'], 'type': instance_type, 'arch': arch,
              'lifecycle': lifecycle, 'zone': zone, 'launched_at': inst['LaunchTime'],
              'spot_request_id': inst.get('SpotInstanceRequestId'),
              'ondemand_usd_per_hour': od['usd_per_hour'], 'ondemand_price': od,
              'spot_price_at_launch_usd_per_hour': spot.get(zone) if lifecycle == 'spot' else None,
              'reserved_usd': reserve, 'expires_at': expires.isoformat(), 'launch_attempts': attempts,
              'volume_ids': []}
    s['leases'].append(record)
    event(s, action='launch', label=label, instance=inst['InstanceId'], lifecycle=lifecycle,
          committed_usd=committed_usd(s))
    persist(s)
    (ROOT / label).mkdir(parents=True, exist_ok=True)
    save(ROOT / label / f"launch-response-{inst['InstanceId']}.json", answer)
    return record


def update_record(ident, **kw):
    s = ledger()
    rec = next(x for x in s['leases'] if x['instance_id'] == ident)
    rec.update(kw)
    persist(s)
    return rec


def ready(ident):
    deadline = time.monotonic() + 420
    last = None
    while time.monotonic() < deadline:
        try:
            info = owned_info(ident)
            if info['State']['Name'] != 'running' or 'PublicIpAddress' not in info:
                time.sleep(5)
                continue
            ip = info['PublicIpAddress']
            text = ssh(ip, 'cloud-init status --wait >/dev/null; sudo cat /run/systemd/shutdown/scheduled; date +%s',
                       timeout=60)
            assert 'USEC=' in text and 'MODE=poweroff' in text, 'shutdown timer missing'
            behavior = aws('ec2', 'describe-instance-attribute', '--instance-id', ident, '--attribute',
                           'instanceInitiatedShutdownBehavior')['InstanceInitiatedShutdownBehavior']['Value']
            assert behavior == 'terminate'
            scheduled = next(int(l.split('=', 1)[1]) / 1e6 for l in text.splitlines() if l.startswith('USEC='))
            launched = info['LaunchTime']
            launch_ts = dt.datetime.fromisoformat(launched).timestamp()
            assert now().timestamp() < scheduled <= launch_ts + (TIMER_MINUTES + 6) * 60, 'timer out of bounds'
            return update_record(ident, ip=ip, timer_verified=True, timer_evidence=text,
                                 shutdown_at_unix=scheduled, shutdown_behavior=behavior,
                                 volume_ids=[x['Ebs']['VolumeId'] for x in info['BlockDeviceMappings']])
        except (RuntimeError, subprocess.TimeoutExpired, AssertionError) as error:
            last = error
            time.sleep(5)
    raise RuntimeError(f'startup failed: {last!r}')


def terminate(ident):
    """Terminate one ledger-recorded, tag-verified lease and prove disk deletion."""
    info = owned_info(ident)
    s = ledger()
    rec = next(x for x in s['leases'] if x['instance_id'] == ident)
    vols = rec.get('volume_ids') or [x['Ebs']['VolumeId'] for x in info.get('BlockDeviceMappings', [])]
    if info['State']['Name'] != 'terminated':
        aws('ec2', 'terminate-instances', '--instance-ids', ident)
    for _ in range(90):
        info = owned_info(ident)
        if info['State']['Name'] == 'terminated':
            break
        time.sleep(5)
    assert info['State']['Name'] == 'terminated', info['State']
    assert vols, 'disk identities unknown'
    for _ in range(36):
        remaining = aws('ec2', 'describe-volumes', '--filters', 'Name=volume-id,Values=' + ','.join(vols))['Volumes']
        if not remaining:
            break
        time.sleep(5)
    assert not remaining, 'root volume still exists'
    verified = now().isoformat()
    spot_hist = []
    if rec['lifecycle'] == 'spot':
        try:
            spot_hist = [p for p in spot_prices(rec['type'], rec['launched_at'], verified)
                         if p['AvailabilityZone'] == rec['zone']]
        except RuntimeError:
            pass
    sir = None
    if rec.get('spot_request_id'):
        try:
            sir = aws('ec2', 'describe-spot-instance-requests', '--spot-instance-request-ids',
                      rec['spot_request_id'])['SpotInstanceRequests'][0]
            sir = {'state': sir['State'], 'status': sir['Status']['Code']}
        except RuntimeError as error:
            sir = {'error': str(error)[:200]}
    rec = update_record(ident, volume_ids=vols, terminated=True, volumes_deleted=True,
                        verified_terminated_at=verified, state_reason=info.get('StateReason'),
                        spot_price_history_during_lease=[{'t': p['Timestamp'], 'usd': p['SpotPrice']} for p in spot_hist],
                        spot_max_seen_usd_per_hour=max([float(p['SpotPrice']) for p in spot_hist] +
                                                       [rec.get('spot_price_at_launch_usd_per_hour') or 0]) or None,
                        spot_request_final=sir)
    cost = lease_cost(rec)
    rec = update_record(ident, cost=cost)
    s = ledger()
    event(s, action='terminated+verified', label=rec['label'], instance=ident, cost=cost,
          committed_usd=committed_usd(s))
    persist(s)
    return rec


def audit():
    """Tag-scoped audit of everything this campaign could own."""
    inst = aws('ec2', 'describe-instances', '--filters', 'Name=tag:Experiment,Values=' + EXPERIMENT)['Reservations']
    states = [{'id': i['InstanceId'], 'state': i['State']['Name']} for r in inst for i in r['Instances']]
    live = [x for x in states if x['state'] != 'terminated']
    vols = aws('ec2', 'describe-volumes', '--filters', 'Name=tag:Experiment,Values=' + EXPERIMENT)['Volumes']
    sgs = aws('ec2', 'describe-security-groups', '--filters', 'Name=tag:Experiment,Values=' + EXPERIMENT)['SecurityGroups']
    named = aws('ec2', 'describe-security-groups', '--filters', 'Name=group-name,Values=seine-' + EXPERIMENT)['SecurityGroups']
    keys = aws('ec2', 'describe-key-pairs')['KeyPairs']
    mine_keys = [k['KeyName'] for k in keys if EXPERIMENT in k['KeyName'] or 'readme' in k['KeyName']]
    s = ledger()
    ledger_ids = [r['instance_id'] for r in s['leases']]
    ledger_states = {}
    if ledger_ids:
        for r in aws('ec2', 'describe-instances', '--instance-ids', *ledger_ids)['Reservations']:
            for i in r['Instances']:
                ledger_states[i['InstanceId']] = i['State']['Name']
    local = {f: (ROOT / f).exists() for f in ('ssh-key', 'ssh-key.pub', 'known-hosts', 'known-hosts.old')}
    return {'at': now().isoformat(), 'instances_tagged': states, 'live_instances_tagged': live,
            'ledger_instance_states': ledger_states, 'volumes_tagged': [v['VolumeId'] for v in vols],
            'security_groups_tagged': [g['GroupId'] for g in sgs], 'security_groups_named': [g['GroupId'] for g in named],
            'key_pairs_matching': mine_keys, 'local_ssh_material_present': local}


def cleanup():
    s = ledger()
    a = audit()
    assert not a['live_instances_tagged'] and not a['volumes_tagged'], a
    assert all(v == 'terminated' for v in a['ledger_instance_states'].values()), a
    if s.get('security_group'):
        for _ in range(12):
            try:
                aws('ec2', 'delete-security-group', '--group-id', s['security_group'])
                break
            except RuntimeError as error:
                if 'DependencyViolation' not in str(error):
                    raise
                time.sleep(10)
        s['security_group_deleted'] = s['security_group']
        s['security_group'] = None
        persist(s)
    for f in ('ssh-key', 'ssh-key.pub', 'known-hosts', 'known-hosts.old'):
        (ROOT / f).unlink(missing_ok=True)
    final = audit()
    assert not final['security_groups_tagged'] and not final['security_groups_named'], final
    assert not any(final['local_ssh_material_present'].values()), final
    assert not final['key_pairs_matching'], final
    s = ledger()
    s['final_audit'] = final
    s['cleanup_verified_at'] = now().isoformat()
    persist(s)
    return final
