#!/usr/bin/env python3
"""Cherry Servers bare-metal leases for cohort benchmarks.

up:    deploy a server, register a task-only SSH key and arm a local systemd
       timer that deletes the server at the lease deadline (billing only ends
       on provider deletion, not guest shutdown).
ip:    print the primary IPv4 once provisioned.
down:  delete the server and the task SSH key; idempotent.
extend: re-arm the delete timer N hours from now.
stock: list in-stock AMD plans.

The API token lives at $CHERRY_TOKEN_FILE (default
~/.cache/seine-hashrate/cherry-api-token, mode 0600). Lease receipts are
written to ~/.cache/seine-hashrate/leases/<name>.json.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request

API = 'https://api.cherryservers.com/v1'
CACHE = Path.home() / '.cache/seine-hashrate'
TOKEN = Path(os.environ.get('CHERRY_TOKEN_FILE', CACHE / 'cherry-api-token'))
LEASES = CACHE / 'leases'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None  # never forward the bearer token


def call(method, path, body=None):
    assert TOKEN.stat().st_mode & 0o077 == 0, f'{TOKEN} must be mode 0600'
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(API + path, data=data, method=method, headers={
        'Authorization': 'Bearer ' + TOKEN.read_text().strip(),
        'Accept': 'application/json', 'Content-Type': 'application/json'})
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=30) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors='replace')[:500]
        if error.code == 404:
            return 404, None
        raise SystemExit(f'Cherry {method} {path}: HTTP {error.code} {detail}')


def receipt_path(name):
    return LEASES / f'{name}.json'


def load(name):
    return json.loads(receipt_path(name).read_text())


def team_project():
    _, teams = call('GET', '/teams')
    team = teams[0]
    _, projects = call('GET', f"/teams/{team['id']}/projects")
    return team, projects[0]['id']


def cmd_stock(args):
    team, _ = team_project()
    _, plans = call('GET', f"/teams/{team['id']}/plans")
    print(f"credit remaining: {team['credit']['account']['remaining']} USD")
    for plan in plans:
        stock = [(r['slug'], r['stock_qty']) for r in plan.get('available_regions', []) if r.get('stock_qty')]
        hourly = [p['price'] for p in plan.get('pricing', []) if p.get('unit') == 'Hourly']
        if stock and 'AMD' in plan['name']:
            print(plan['id'], plan['name'], plan.get('specs', {}).get('memory', {}).get('total'), 'GB', stock, hourly)


def cmd_up(args):
    LEASES.mkdir(parents=True, exist_ok=True)
    path = receipt_path(args.name)
    if path.exists():
        raise SystemExit(f'lease {args.name} already exists: {path}')
    team, project = team_project()
    key = CACHE / f'{args.name}-ssh'
    if not key.exists():
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', args.name, '-f', str(key)], check=True)
    _, ssh_key = call('POST', '/ssh-keys', {'label': args.name, 'key': key.with_suffix('.pub').read_text().strip()})
    receipt = {'name': args.name, 'project': project, 'ssh_key_id': ssh_key['id'], 'key': str(key),
               'plan': int(args.plan) if args.plan.isdigit() else args.plan, 'region': args.region, 'hours': args.hours,
               'created_at': time.strftime('%Y-%m-%dT%H:%M:%S%z')}
    path.write_text(json.dumps(receipt, indent=2))
    # Arm deletion before ordering, so a crash between order and receipt still cleans up by hostname.
    unit = f'seine-lease-{args.name}'
    subprocess.run(['systemd-run', '--user', f'--on-active={int(args.hours * 3600)}', f'--unit={unit}',
                    sys.executable, str(Path(__file__).resolve()), 'down', args.name], check=True,
                   capture_output=True)
    try:
        _, server = call('POST', f'/projects/{project}/servers', {
            'plan': int(args.plan) if args.plan.isdigit() else args.plan, 'region': args.region, 'image': args.image, 'hostname': args.name,
            'ssh_keys': [ssh_key['id']]})
    except SystemExit:
        cmd_down(args)  # out of stock or rejected: remove the key and timer
        raise
    receipt.update(server_id=server['id'], watchdog_unit=unit)
    path.write_text(json.dumps(receipt, indent=2))
    print(json.dumps({'name': args.name, 'server_id': server['id'], 'delete_after_hours': args.hours}))


def cmd_ip(args):
    receipt = load(args.name)
    deadline = time.time() + args.wait
    while True:
        code, server = call('GET', f"/servers/{receipt['server_id']}")
        assert code == 200 and server['hostname'] == args.name
        ips = [x['address'] for x in server.get('ip_addresses', [])
               if x.get('type') == 'primary-ip' and x.get('address_family') == 4]
        if ips and (server.get('state') == 'active' or server.get('status') == 'deployed'):
            print(ips[0])
            return
        if time.time() > deadline:
            raise SystemExit(f"not ready: state={server.get('state')} status={server.get('status')}")
        time.sleep(20)


def cmd_down(args):
    path = receipt_path(args.name)
    if not path.exists():
        print(f'no lease {args.name}')
        return
    receipt = load(args.name)
    server_id = receipt.get('server_id')
    if server_id is None:  # order may have succeeded without a recorded id
        _, servers = call('GET', f"/projects/{receipt['project']}/servers")
        server_id = next((s['id'] for s in servers if s['hostname'] == args.name), None)
    if server_id is not None:
        code, server = call('GET', f'/servers/{server_id}')
        if code == 200:
            assert server['hostname'] == args.name, 'refusing to delete a server this lease does not own'
            call('DELETE', f'/servers/{server_id}')
        for _ in range(30):
            if call('GET', f'/servers/{server_id}')[0] == 404:
                break
            time.sleep(10)
        else:
            raise SystemExit(f'server {server_id} still present after delete')
    call('DELETE', f"/ssh-keys/{receipt['ssh_key_id']}")
    for suffix in ('', '.pub'):
        Path(receipt['key'] + suffix).unlink(missing_ok=True)
    subprocess.run(['systemctl', '--user', 'stop', f"seine-lease-{args.name}.timer"], capture_output=True)
    path.rename(path.with_suffix('.deleted.json'))
    print(f'deleted {args.name} (server {server_id})')


def cmd_extend(args):
    receipt = load(args.name)
    unit = f'seine-lease-{args.name}'
    # Re-arm the delete timer from now; stopping the transient timer frees its name.
    subprocess.run(['systemctl', '--user', 'stop', f'{unit}.timer'], capture_output=True)
    subprocess.run(['systemd-run', '--user', f'--on-active={int(args.hours * 3600)}', f'--unit={unit}',
                    sys.executable, str(Path(__file__).resolve()), 'down', args.name], check=True,
                   capture_output=True)
    receipt['extended_at'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
    receipt['extended_hours'] = args.hours
    receipt_path(args.name).write_text(json.dumps(receipt, indent=2))
    print(json.dumps({'name': args.name, 'delete_after_hours_from_now': args.hours}))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('stock')
    up = sub.add_parser('up')
    up.add_argument('name')
    up.add_argument('--plan', required=True, help='plan id or slug (some plans only order by slug)')
    up.add_argument('--region', required=True)
    up.add_argument('--image', default='ubuntu_24_04_64bit')
    up.add_argument('--hours', type=float, default=2.0, help='hard lease; local timer deletes the server')
    ip = sub.add_parser('ip')
    ip.add_argument('name')
    ip.add_argument('--wait', type=int, default=1800)
    down = sub.add_parser('down')
    down.add_argument('name')
    extend = sub.add_parser('extend')
    extend.add_argument('name')
    extend.add_argument('--hours', type=float, required=True, help='new deadline, counted from now')
    args = parser.parse_args()
    {'stock': cmd_stock, 'up': cmd_up, 'ip': cmd_ip, 'down': cmd_down, 'extend': cmd_extend}[args.command](args)


if __name__ == '__main__':
    main()
