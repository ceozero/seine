#!/usr/bin/python3
"""Gate the unchanged productive protocol on prior collection and rental deadlines."""
import argparse
import datetime as dt
import json
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parent
GOAL_DEADLINE = dt.datetime.fromisoformat('2026-10-25T18:42:52+00:00').timestamp()
OWN_UNIT = 'seine-amd-short-windows.service'


def validate_handoff(handoff):
    assert handoff['experiments_finished'] is True
    for campaign in ('amd-overnight-20261025', 'amd-ring-locality-20261025',
                     'amd-page-size-20261025'):
        evidence = handoff['verified_collections'][campaign]
        assert re.fullmatch(r'[0-9a-f]{64}', evidence['archive_sha256'])
        assert evidence['verified_manifest_entries'] > 0
        assert evidence['settings_restored'] is True


def validate_authorization(record, deadline, now):
    assert record['server_id'] == 1043469
    assert record['ledger_extension_recorded'] is True
    assert record['controller_deadline_epoch'] == deadline
    assert now + 14400 + 120 < deadline
    assert deadline + 10 * 60 <= record['provider_delete_before_epoch'] <= min(
        GOAL_DEADLINE, record['funded_until_epoch'])
    assert 0 < record['cherry_total_reserved_usd'] <= 13.20
    assert record['aws_reserved_usd'] == 3.25
    assert record['total_reserved_usd'] == record['cherry_total_reserved_usd'] + record['aws_reserved_usd']
    assert record['total_reserved_usd'] <= 25


def validate_active_units(output):
    units = [line.split()[0] for line in output.splitlines() if line.strip()]
    assert all(unit == OWN_UNIT for unit in units), units


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deadline-epoch', type=float, required=True)
    args = parser.parse_args()
    validate_handoff(json.loads((ROOT / 'prior-evidence-collected.json').read_text()))
    validate_authorization(json.loads((ROOT / 'run-authorization.json').read_text()),
                           args.deadline_epoch, time.time())
    units = subprocess.check_output(['systemctl', 'list-units', '--type=service',
        '--state=active,activating,deactivating,reloading', '--no-legend', '--plain',
        'seine-amd-*', 'seine-overnight-*', 'seine-short-windows-*', 'seine-cherry-*'],
        text=True, timeout=30)
    validate_active_units(units)
    # Frozen copies travel in this bundle; no import from another active run.
    # Its own preflight checks identity, settings, all file checksums and the
    # same full four-hour time allowance before any measurement begins.
    from run_productive import main as run_productive
    run_productive()


if __name__ == '__main__':
    main()
