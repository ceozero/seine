#!/usr/bin/env python3
"""Read-only, aggregate telemetry briefing for agents. No third-party packages."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
from zoneinfo import ZoneInfo

REMOTE_SQL = (
    'docker compose -f /opt/seine/telemetry/deploy/compose.yaml '
    '--env-file /opt/seine/telemetry/deploy/.env exec -T db '
    'psql -X -U telemetry -d telemetry -qAt -v ON_ERROR_STOP=1'
)


def remote(host, command, data=None):
    return subprocess.run(
        ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '--', host, command],
        input=data, text=True, capture_output=True, timeout=60,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='root@2.31.36.180', help='Collector SSH destination')
    args = parser.parse_args()
    if args.host.startswith('-'):
        parser.error('host must be an SSH destination, not an option')
    briefing = {
        'checked_at': datetime.now(ZoneInfo('America/New_York')).strftime('%Y-%m-%d %H:%M:%S %Z'),
        'timezone': 'America/New_York',
        'scope': 'Aggregates from release builds in the last seven days; installations are not people.',
        'performance_screen': {
            'minimum_installations': 5,
            'minimum_reports_per_installation': 3,
            'minimum_span_hours_per_installation': 24,
            'interpretation': 'Screening thresholds, not statistical confidence or benchmark proof.',
        },
    }
    failed = False
    for key, command, data in (
        ('health', '/opt/seine/telemetry/deploy/check.sh --infrastructure-only', None),
        ('data_quality', REMOTE_SQL, Path(__file__).with_name('data_quality.sql').read_text()),
        ('telemetry', REMOTE_SQL, Path(__file__).with_suffix('.sql').read_text()),
        ('diagnostics', REMOTE_SQL, Path(__file__).with_name('diagnostics.sql').read_text()),
    ):
        try:
            result = remote(args.host, command, data)
            if result.returncode:
                briefing[key] = {'status': 'error', 'detail': (result.stderr or result.stdout).strip()[:1000]}
                failed = True
            elif key in ('telemetry', 'data_quality', 'diagnostics'):
                briefing[key] = json.loads(result.stdout)
            else:
                briefing[key] = {'status': 'ok', 'detail': result.stdout.strip()}
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
            briefing[key] = {'status': 'error', 'detail': str(error)[:1000]}
            failed = True
    data = briefing.get('telemetry', {})
    if data.get('status') != 'error':
        briefing['assessment'] = (
            'No qualifying performance cohorts yet. Use inventory only; collect more observations before comparing rates.'
            if not data['performance_candidates'] else
            'Candidate cohorts are available. Prioritize common hardware, then verify any proposed change with controlled paired benchmarks.'
        )
    if failed:
        briefing['assessment'] = 'Resolve the reported health/query failure before relying on this briefing.'
    quality = briefing.get('data_quality', {})
    if not failed and quality.get('status') == 'error':
        failed = True
        briefing['assessment'] = (
            'Hardware inventory is arriving without performance samples from at least five '
            'installations of one version, each reporting at least three times over two hours. '
            'Investigate the miner sampling path; waiting for cohorts is not sufficient.'
        )
    diagnostics = briefing.get('diagnostics', {})
    briefing['diagnostic_interpretation'] = (
        'Event detail contains typed causes captured at the failing operation; absent detail means '
        'legacy or uninstrumented code, not an unknown error message. OS error numbers are platform-specific. '
        'Requested bytes describe one failed allocation. Available memory is a report-time snapshot, '
        'not proof of OOM and excludes reserved HugeTLB pages. Unclean clusters show the last observed '
        'phase of the previous run, not a crash cause; checkpoints can lag or be absent. '
        'Hashing in a restart report establishes work after restart, not recovery from every issue. '
        'Several events can describe one failure.'
    )
    if diagnostics.get('status') == 'attention':
        failed = True
        briefing['diagnostic_assessment'] = (
            'At least three installations of one version reported errors, quarantines or '
            'unclean previous runs within 24 hours. Investigate issue clusters by build, '
            'source location and hardware. An unclean run is not proof of a crash.'
        )
    elif diagnostics.get('status') == 'unavailable':
        briefing['diagnostic_assessment'] = 'No diagnostic coverage yet; missing failure reports do not establish healthy miners.'
    elif diagnostics.get('status') == 'ok':
        briefing['diagnostic_assessment'] = 'Review issue clusters, including single-installation failures. No fleet threshold is exceeded.'
    print(json.dumps(briefing, indent=2))
    return int(failed)


if __name__ == '__main__':
    sys.exit(main())
