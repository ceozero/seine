#!/usr/bin/env python3
"""Exercise a disposable local collector + PostgreSQL. Writes fixture rows."""
import json
import os
from pathlib import Path
import subprocess
import urllib.error
import urllib.request
import uuid

URL = os.environ.get('TELEMETRY_TEST_URL', 'http://127.0.0.1:9080')
DATABASE = os.environ['TELEMETRY_TEST_DATABASE']
FIXTURE = json.loads(Path(__file__).with_name('fixture.json').read_text())


def report():
    value = json.loads(json.dumps(FIXTURE))
    value['installation_id'] = uuid.uuid4().hex
    value['report_id'] = uuid.uuid4().hex
    return value


def send(value):
    body = json.dumps(value).encode()
    request = urllib.request.Request(URL + '/v1/reports', body, {'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


def query(sql):
    return subprocess.check_output(['psql', DATABASE, '-At', '-v', 'ON_ERROR_STOP=1', '-c', sql], text=True).strip()


valid = report()
assert send(valid) == 204
assert send(valid) == 429
invalid = report()
invalid['hardware']['hostname'] = 'private-field-fixture'
assert send(invalid) == 422
assert send({}) == 422
oversized = report()
oversized['hardware']['cpu_model'] = 'x' * 40000
assert send(oversized) == 413
bad_window = report()
bad_window['window_secs'] = 0
assert send(bad_window) == 422
row = query(f"SELECT payload->>'report_id' FROM telemetry_reports WHERE report_id='{valid['report_id']}'")
assert row == valid['report_id']
assert query("SELECT median_hps FROM telemetry_backend_performance WHERE cpu_model='Example CPU (fixture)'") == '10'
assert query("SELECT count(*) FROM telemetry_reports WHERE payload::text LIKE '%private-field-fixture%'") == '0'
print('PASS: valid upload, rate limit, strict fields, empty/oversized/invalid-window rejection, database persistence and population-weighted performance view')

# The collector accepts both generations while rejecting v2 fields disguised as v1.
legacy = report()
legacy['schema_version'] = 1
legacy['hardware'].pop('resources')
legacy['hardware']['cpu_model'] = 'Legacy CPU (fixture)'
for backend in legacy['backends']:
    backend['settings'].pop('cpu_backing_mib')
    backend['settings'].pop('cpu_affinity')
assert send(legacy) == 204
bad_version = report()
bad_version['schema_version'] = 1
assert send(bad_version) == 422


def insert(value, hours):
    payload = json.dumps(value).replace("'", "''")
    query("INSERT INTO telemetry_reports (report_id,installation_id,received_at,payload) "
          f"VALUES ('{value['report_id']}','{value['installation_id']}',"
          f"now()-interval '{hours} hours','{payload}'::jsonb)")


def analysis(filename):
    return json.loads(subprocess.check_output(
        ['psql', DATABASE, '-qAt', '-v', 'ON_ERROR_STOP=1', '-f',
         str(Path(__file__).with_name(filename))], text=True))


# Exact settings are not enough: environments, builds, RAM and resource limits
# must separate otherwise identical CPUs. Free RAM remains a diagnostic snapshot.
for cohort in range(5):
    for installation in range(5):
        identity = uuid.uuid4().hex
        for index, hours in enumerate((26, 13, 1)):
            sample = report()
            sample['installation_id'] = identity
            sample['hardware']['cpu_model'] = 'Analysis CPU (fixture)'
            if cohort == 1:
                sample['hardware']['runtime_environment'] = 'wsl'
            elif cohort == 2:
                sample['build_features'] = 'cpu-only'
            elif cohort == 3:
                sample['hardware']['memory_gib'] = 128
            elif cohort == 4:
                sample['hardware']['resources']['effective_memory_gib'] = 32
            sample['hardware']['resources']['available_memory_gib'] = 20 + index
            sample['backends'][0]['hashes'] = 3600 * (10 + index * 10 + cohort * 100)
            # One report has two identical devices; it still counts as one report.
            if index == 0:
                duplicate = json.loads(json.dumps(sample['backends'][0]))
                duplicate['instance'] = 2
                sample['backends'].append(duplicate)
            insert(sample, hours)

candidates = analysis('agent_report.sql')['performance_candidates']
candidates = [c for c in candidates if c['cpu'] == 'Analysis CPU (fixture)']
assert len(candidates) == 5, candidates
assert sorted(c['median_hps'] for c in candidates) == [20, 120, 220, 320, 420]
assert all(c['installations'] == 5 for c in candidates)
view = json.loads(query("SELECT json_agg(v) FROM telemetry_backend_performance v "
                        "WHERE cpu_model='Analysis CPU (fixture)'"))
assert sorted(v['median_hps'] for v in view) == [20, 120, 220, 320, 420]
assert all(v['installations'] == 5 for v in view)

# Recent inventory-only reporters cannot be confused with healthy sparse cohorts.
identities = [uuid.uuid4().hex for _ in range(5)]
for index, identity in enumerate(identities):
    for hours in (4, 2, 1):
        empty = report()
        empty['installation_id'] = identity
        empty['miner_version'] = 'quality-fixture'
        empty['backends'] = []
        insert(empty, hours)
    quality = analysis('data_quality.sql')
    assert quality['status'] == ('error' if index == 4 else 'ok'), quality
for identity in identities:
    recovered = report()
    recovered['installation_id'] = identity
    recovered['miner_version'] = 'quality-fixture'
    insert(recovered, 0)
assert analysis('data_quality.sql')['status'] == 'ok'
print('PASS: schema 1/2 compatibility, environment/build/RAM/limit cohort separation, '
      'per-report deduplication, stable cohort thresholds, sustained empty-sample detection and recovery')

assert analysis('diagnostics.sql')['status'] == 'unavailable'
diagnostic_fixture = json.loads(Path(__file__).with_name('diagnostics-fixture.json').read_text())

def diagnostic_report():
    value = json.loads(json.dumps(diagnostic_fixture))
    value['installation_id'] = uuid.uuid4().hex
    value['report_id'] = uuid.uuid4().hex
    value['miner_version'] = 'diagnostics-fixture'
    value['diagnostics']['previous_run_unclean'] = False
    value['diagnostics'].pop('previous_run', None)
    return value

valid_diagnostic = diagnostic_report()
assert send(valid_diagnostic) == 204
stored = json.loads(query(f"SELECT payload->'diagnostics' FROM telemetry_reports WHERE report_id='{valid_diagnostic['report_id']}'"))
assert stored['events'][0]['detail']['os_error'] == 12
assert stored['events'][0]['detail']['requested_bytes'] == 2147483648
legacy_diagnostic = diagnostic_report()
legacy_diagnostic['schema_version'] = 3
legacy_diagnostic['diagnostics'].pop('phase')
for event in legacy_diagnostic['diagnostics']['events']:
    event.pop('detail', None)
    event.pop('phase', None)
assert send(legacy_diagnostic) == 204
wrong_generation = diagnostic_report()
wrong_generation['schema_version'] = 3
assert send(wrong_generation) == 422
private_detail = diagnostic_report()
private_detail['diagnostics']['events'][0]['detail']['message'] = 'PRIVATE WALLET'
assert send(private_detail) == 422
private = diagnostic_report()
private['diagnostics']['events'][0]['message'] = 'PRIVATE WALLET'
assert send(private) == 422
wrong_schema = diagnostic_report()
wrong_schema['schema_version'] = 2
assert send(wrong_schema) == 422
forbidden_source = diagnostic_report()
forbidden_source['diagnostics']['events'][0]['source'] = '/home/private/src/main.rs'
assert send(forbidden_source) == 422
short_failure = diagnostic_report()
short_failure['window_secs'] = 1
short_failure['backends'] = []
short_failure['diagnostics']['reason'] = 'failure'
assert send(short_failure) == 204

# One noisy installation does not count as a fleet incident; three do.
for index in range(3):
    failure = diagnostic_report()
    failure['diagnostics']['events'][0]['code'] = 'backend_error'
    failure['diagnostics']['events'][0]['count'] = 1000
    insert(failure, 0)
    if index == 0:
        repeated = json.loads(json.dumps(failure))
        repeated['report_id'] = uuid.uuid4().hex
        insert(repeated, 1)
    diagnostics = analysis('diagnostics.sql')
    assert diagnostics['status'] == ('attention' if index == 2 else 'ok'), diagnostics
clusters = [c for c in diagnostics['issue_clusters'] if c['code'] == 'backend_error']
assert len(clusters) == 1 and clusters[0]['affected_installations'] == 3
assert clusters[0]['occurrences'] == 4000
assert 'installation_id' not in json.dumps(diagnostics)

# Final reports cannot trigger the missing-periodic-samples alarm.
for _ in range(5):
    failure = diagnostic_report()
    failure['backends'] = []
    failure['diagnostics']['reason'] = 'failure'
    for hours in (4, 2, 1):
        failure['report_id'] = uuid.uuid4().hex
        insert(failure, hours)
assert analysis('data_quality.sql')['status'] == 'ok'
assert query("SELECT count(*) FROM telemetry_reports WHERE payload::text LIKE '%PRIVATE WALLET%'") == '0'
print('PASS: schema 4 diagnostics, early failures, private-data rejection, installation-weighted incident thresholds and periodic/final separation')

recovered = json.loads(Path(__file__).with_name('reliability-fixture.json').read_text())
recovered['installation_id'] = uuid.uuid4().hex
recovered['report_id'] = uuid.uuid4().hex
assert send(recovered) == 204
stored = json.loads(query(f"SELECT payload #> '{{diagnostics,previous_run}}' FROM telemetry_reports WHERE report_id='{recovered['report_id']}'"))
assert stored['miner_version'] == 'v0.2.35-fixture'
assert stored['recent_events'][0]['source'] == 'deps/cudarc-0.19.2/src/lib.rs'
for mutate in (
    lambda p: p.update(schema_version=4),
    lambda p: p['diagnostics']['previous_run']['recent_events'][0].update(message='PRIVATE WALLET'),
    lambda p: p['diagnostics']['previous_run']['recent_events'][0].update(source='/home/private/src/lib.rs'),
):
    bad = json.loads(json.dumps(recovered))
    bad['installation_id'] = uuid.uuid4().hex
    bad['report_id'] = uuid.uuid4().hex
    mutate(bad)
    assert send(bad) == 422
assert query("SELECT count(*) FROM telemetry_reports WHERE payload::text LIKE '%PRIVATE WALLET%'") == '0'
print('PASS: schema 5 recovered evidence, previous version, downgrade and private-field rejection')

tuning = json.loads(Path(__file__).with_name('tuning-fixture.json').read_text())
tuning['installation_id'] = uuid.uuid4().hex
tuning['report_id'] = uuid.uuid4().hex
assert send(tuning) == 204
stored = json.loads(query(f"SELECT payload->'tuning' FROM telemetry_reports WHERE report_id='{tuning['report_id']}'"))
assert stored['run_id'] == tuning['tuning']['run_id']
assert stored['trials'][0]['outcome']['samples'][1]['hashes'] == 3090
assert stored['trials'][0]['outcome']['policy']['quantization'] == 'three_window_hash'
for mutate in (
    lambda p: p.update(schema_version=5),
    lambda p: p['tuning']['trials'][0]['outcome'].update(message='PRIVATE WALLET'),
    lambda p: p['tuning']['trials'][0]['outcome']['samples'][0]['context']['resources'].update(placement_fingerprint='/home/private'),
):
    bad = json.loads(json.dumps(tuning))
    bad['installation_id'] = uuid.uuid4().hex
    bad['report_id'] = uuid.uuid4().hex
    mutate(bad)
    assert send(bad) == 422
assert analysis('tuning_report.sql')['unique_trials'] == 1
assert query("SELECT count(*) FROM telemetry_reports WHERE payload::text LIKE '%PRIVATE WALLET%'") == '0'
print('PASS: schema 6 paired trials, raw samples and policy persistence, strict rejection and analysis')

alternative = json.loads(json.dumps(tuning))
alternative['installation_id'] = uuid.uuid4().hex
alternative['report_id'] = uuid.uuid4().hex
trial = alternative['tuning']['trials'][0]['outcome']
trial['policy'].update(minimum_sample_ms=30000, minimum_hashes=32,
                       short_sample_ms=10000, short_minimum_hashes=256)
trial.update(decision='no_confirmed_gain', applied='baseline')
trial['context_after'] = json.loads(json.dumps(trial['context_before']))
trial['samples'] = trial['samples'][:3]
for sample in trial['samples']:
    sample.update(elapsed_ms=30000 if sample['arm'] == 'candidate' else 10000,
                  hashes=64 if sample['arm'] == 'candidate' else 300)
assert send(alternative) == 204
assert analysis('tuning_report.sql')['qualified_trials'] == 2
alternative['installation_id'] = uuid.uuid4().hex
alternative['report_id'] = uuid.uuid4().hex
del trial['policy']['short_minimum_hashes']
assert send(alternative) == 422
print('PASS: schema 6 mixed short/full window rules and incomplete alternative rejection')

# Optional artifact emitted by the real runtime Monitor test. Keep this boundary
# check separate from the handwritten collector fixture and production data.
if runtime_fixture := os.environ.get('TELEMETRY_TEST_TRIAL_FIXTURE'):
    runtime = json.loads(Path(runtime_fixture).read_text())
    before = analysis('tuning_report.sql')['qualified_trials']
    for _ in range(5):
        runtime['installation_id'] = uuid.uuid4().hex
        runtime['report_id'] = uuid.uuid4().hex
        assert send(runtime) == 204
    result = analysis('tuning_report.sql')
    assert result['qualified_trials'] == before + 5, result
    hint, = result['ranked_hints']
    assert hint['installations'] == 5
    assert hint['confidence'] == 'observational_support'
    assert hint['installations_with_resolved_gain'] == 5
    assert abs(hint['median_ratio'] - 1.1) < 1e-9
    assert hint['median_idle_ms'] is None
    assert not hint['automatic_default_eligible']
    for mutation in ('changed', 'unknown'):
        invalid_context = json.loads(json.dumps(runtime))
        invalid_context['installation_id'] = uuid.uuid4().hex
        invalid_context['report_id'] = uuid.uuid4().hex
        sample = invalid_context['tuning']['trials'][0]['outcome']['samples'][1]
        if mutation == 'changed':
            sample['changed'] = True
        else:
            sample['context']['resources']['placement_fingerprint'] = None
        assert send(invalid_context) == 204
        assert analysis('tuning_report.sql')['qualified_trials'] == before + 5
    print('PASS: runtime Monitor output accepted, five-installation research hint, changed/unknown context excluded and unknown costs preserved')
