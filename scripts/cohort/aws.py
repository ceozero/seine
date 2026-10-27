#!/usr/bin/env python3
"""AWS EC2 leases for cohort benchmarks (same interface as cherry.py).

up:   launch one instance (one-time spot by default) with a task-only key pair and
      security group, guest shutdown at the lease deadline (shutdown behavior =
      terminate) plus a local systemd timer that terminates it independently.
ip:   print the public IPv4 once running.
down: terminate the instance, then delete the key pair and security group.

Uses the AWS CLI with $AWS_PROFILE (default seine-bench) in $AWS_REGION
(default us-east-1). Receipts: ~/.cache/seine-hashrate/leases/<name>.json.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

CACHE = Path.home() / '.cache/seine-hashrate'
LEASES = CACHE / 'leases'
PROFILE = os.environ.get('AWS_PROFILE', 'seine-bench')
REGION = os.environ.get('AWS_REGION', 'us-east-1')
AMI_PARAM = '/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id'
# The benchmark SSO role may only create resources in its owned VPC, tagged with Project.
VPC = os.environ.get('SEINE_AWS_VPC', 'vpc-011004097d89589bb')
SUBNET = os.environ.get('SEINE_AWS_SUBNET', 'subnet-0175eae5171bc2a55')
PROJECT = os.environ.get('SEINE_AWS_PROJECT', 'seine-avx2-validation')


def aws(*args):
    result = subprocess.run(['aws', '--profile', PROFILE, '--region', REGION, '--output', 'json', *args],
                            capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise SystemExit(f"aws {' '.join(args[:2])}: {result.stderr.strip()[:500]}")
    return json.loads(result.stdout) if result.stdout.strip() else None


def receipt_path(name):
    return LEASES / f'{name}.json'


def save(receipt):
    receipt_path(receipt['name']).write_text(json.dumps(receipt, indent=2))


def cmd_up(args):
    LEASES.mkdir(parents=True, exist_ok=True)
    if receipt_path(args.name).exists():
        raise SystemExit(f'lease {args.name} already exists')
    key = CACHE / f'{args.name}-ssh'
    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', args.name, '-f', str(key)], check=True)
    receipt = {'name': args.name, 'provider': 'aws', 'region': REGION, 'key': str(key),
               'instance_type': args.type, 'hours': args.hours, 'market': 'on-demand' if args.on_demand else 'spot'}
    save(receipt)
    unit = f'seine-lease-{args.name}'
    subprocess.run(['systemd-run', '--user', f'--on-active={int(args.hours * 3600)}', f'--unit={unit}',
                    sys.executable, str(Path(__file__).resolve()), 'down', args.name],
                   check=True, capture_output=True)
    my_ip = urllib.request.urlopen('https://checkip.amazonaws.com', timeout=10).read().decode().strip()
    tags = [{'Key': 'Project', 'Value': PROJECT}, {'Key': 'Name', 'Value': args.name}]
    group = aws('ec2', 'create-security-group', '--group-name', args.name, '--vpc-id', VPC,
                '--description', 'seine cohort benchmark (temporary)', '--tag-specifications',
                json.dumps([{'ResourceType': 'security-group', 'Tags': tags}]))['GroupId']
    receipt['security_group'] = group
    save(receipt)
    aws('ec2', 'authorize-security-group-ingress', '--group-id', group,
        '--protocol', 'tcp', '--port', '22', '--cidr', f'{my_ip}/32')
    minutes = max(5, int(args.hours * 60) - 5)
    if args.windows:
        images = aws('ec2', 'describe-images', '--owners', 'amazon', '--filters',
                     'Name=name,Values=Windows_Server-2025-English-Full-Base-*', 'Name=state,Values=available')
        ami = max(images['Images'], key=lambda i: i['CreationDate'])['ImageId']
        receipt.update(os='windows', user='Administrator')
    else:
        ami = aws('ssm', 'get-parameter', '--name', AMI_PARAM)['Parameter']['Value']
    # The SSO role cannot import key pairs; cloud-init installs the task key for
    # ubuntu and (with disable_root false) for root, which the cohort scripts use.
    public_key = key.with_suffix('.pub').read_text().strip()
    if args.windows:
        # OpenSSH for Administrator with the task key; guest shutdown at expiry.
        user_data = f"""<powershell>
New-Item -ItemType Directory -Force C:\\cohort | Out-Null
Start-Transcript -Path C:\\cohort\\bootstrap.log
$expiry = New-ScheduledTaskAction -Execute 'shutdown.exe' -Argument '/s /f /t 0'
$when = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes({minutes})
Register-ScheduledTask -TaskName SeineExpiry -Action $expiry -Trigger $when -User SYSTEM -RunLevel Highest -Force | Out-Null
if (!(Get-Service sshd -ErrorAction SilentlyContinue)) {{ Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0 | Out-Null }}
Set-Service sshd -StartupType Automatic
Start-Service sshd
Set-Content -Path C:\\ProgramData\\ssh\\administrators_authorized_keys -Value '{public_key}' -Encoding ASCII
& icacls.exe C:\\ProgramData\\ssh\\administrators_authorized_keys /inheritance:r /grant:r 'Administrators:F' 'SYSTEM:F' | Out-Null
New-Item -Path HKLM:\\SOFTWARE\\OpenSSH -Force | Out-Null
New-ItemProperty -Path HKLM:\\SOFTWARE\\OpenSSH -Name DefaultShell -Value 'C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe' -PropertyType String -Force | Out-Null
Restart-Service sshd
New-NetFirewallRule -Name seine-ssh -DisplayName seine-ssh -Enabled True -Direction Inbound -Protocol TCP -LocalPort 22 -Action Allow | Out-Null
Stop-Transcript
</powershell>"""
    else:
        user_data = ('#cloud-config\ndisable_root: false\nssh_authorized_keys:\n  - ' + public_key
                     + f'\nruncmd:\n  - [shutdown, -P, "+{minutes}"]\n')
    launch = ['ec2', 'run-instances', '--image-id', ami, '--instance-type', args.type,
              '--security-group-ids', group, '--subnet-id', SUBNET,
              '--metadata-options', 'HttpTokens=required',
              '--instance-initiated-shutdown-behavior', 'terminate',
              '--user-data', user_data,
              '--block-device-mappings', json.dumps([{'DeviceName': '/dev/sda1', 'Ebs': {
            'VolumeSize': 40 if args.windows else 16, 'VolumeType': 'gp3', 'DeleteOnTermination': True}}]),
              '--tag-specifications', json.dumps([{'ResourceType': r, 'Tags': tags} for r in ('instance', 'volume')])]
    if not args.on_demand:
        launch += ['--instance-market-options',
                   json.dumps({'MarketType': 'spot', 'SpotOptions': {
                       'SpotInstanceType': 'one-time', 'InstanceInterruptionBehavior': 'terminate',
                       **({'MaxPrice': str(args.max_price)} if args.max_price else {})}})]
    try:
        instance = aws(*launch)['Instances'][0]['InstanceId']
    except SystemExit:
        cmd_down(args)
        raise
    receipt['instance_id'] = instance
    save(receipt)
    print(json.dumps({'name': args.name, 'instance_id': instance, 'delete_after_hours': args.hours}))


def cmd_ip(args):
    receipt = json.loads(receipt_path(args.name).read_text())
    deadline = time.time() + args.wait
    while True:
        instance = aws('ec2', 'describe-instances', '--instance-ids', receipt['instance_id'])['Reservations'][0]['Instances'][0]
        state = instance['State']['Name']
        if state == 'running' and instance.get('PublicIpAddress'):
            print(instance['PublicIpAddress'])
            return
        if state in ('shutting-down', 'terminated', 'stopped') or time.time() > deadline:
            raise SystemExit(f'not ready: {state}')
        time.sleep(10)


def cmd_down(args):
    path = receipt_path(args.name)
    if not path.exists():
        print(f'no lease {args.name}')
        return
    receipt = json.loads(path.read_text())
    if receipt.get('instance_id'):
        aws('ec2', 'terminate-instances', '--instance-ids', receipt['instance_id'])
        for _ in range(60):
            state = aws('ec2', 'describe-instances', '--instance-ids', receipt['instance_id'])[
                'Reservations'][0]['Instances'][0]['State']['Name']
            if state == 'terminated':
                break
            time.sleep(10)
        else:
            raise SystemExit(f"instance {receipt['instance_id']} not terminated")
    if receipt.get('security_group'):
        for _ in range(12):  # the group stays attached briefly after termination
            if subprocess.run(['aws', '--profile', PROFILE, '--region', REGION, 'ec2', 'delete-security-group',
                               '--group-id', receipt['security_group']], capture_output=True).returncode == 0:
                break
            time.sleep(10)
    if receipt.get('key_pair'):
        aws('ec2', 'delete-key-pair', '--key-name', receipt['key_pair'])
    for suffix in ('', '.pub'):
        Path(receipt['key'] + suffix).unlink(missing_ok=True)
    subprocess.run(['systemctl', '--user', 'stop', f"seine-lease-{args.name}.timer"], capture_output=True)
    path.rename(path.with_suffix('.deleted.json'))
    print(f"terminated {args.name} ({receipt.get('instance_id')})")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    up = sub.add_parser('up')
    up.add_argument('name')
    up.add_argument('--type', required=True)
    up.add_argument('--hours', type=float, default=1.5)
    up.add_argument('--on-demand', action='store_true')
    up.add_argument('--max-price', type=float)
    up.add_argument('--windows', action='store_true', help='Windows Server 2025 with OpenSSH (user Administrator)')
    ip = sub.add_parser('ip')
    ip.add_argument('name')
    ip.add_argument('--wait', type=int, default=900)
    down = sub.add_parser('down')
    down.add_argument('name')
    args = parser.parse_args()
    {'up': cmd_up, 'ip': cmd_ip, 'down': cmd_down}[args.command](args)


if __name__ == '__main__':
    main()
