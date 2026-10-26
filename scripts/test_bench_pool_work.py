"""Exercise receiver job transitions using a harmless socket client, no mining."""
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import textwrap
import unittest
from types import SimpleNamespace

from bench_pool_work import miner_command


class ReceiverTests(unittest.TestCase):
    def run_case(self, grace, rotate=True, reset=False, malformed=False, fee_switch=False,
                 tls=False, wrong_tls_name=False):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        fake = root / 'fixture-miner'
        fake.write_text('#!' + sys.executable + '\n' + textwrap.dedent('''
            import json,os,socket,ssl,struct,sys,time
            from urllib.parse import urlsplit
            endpoint=urlsplit(sys.argv[sys.argv.index('--pool-url')+1])
            address=sys.argv[sys.argv.index('--address')+1]
            connection=socket.create_connection((endpoint.hostname,endpoint.port))
            if '--tls-name' in sys.argv:
                context=ssl.create_default_context(cafile=os.environ['FIXTURE_TEST_CA'])
                connection=context.wrap_socket(connection, server_hostname=sys.argv[sys.argv.index('--tls-name')+1])
            stream=connection.makefile('r')
            def send(value):
                connection.sendall((json.dumps(value)+'\\n').encode())
            def submit(job, nonce, request):
                send({'id':request,'method':'submit','params':{'job_id':job['job_id'],'nonce':nonce,'claimed_hash':'00'*32}})
            send({'id':1,'method':'login','params':{'address':'fixture-fee' if '--fee-switch' in sys.argv else address}})
            original=None
            for line in stream:
                message=json.loads(line)
                if message.get('id')==2 and '--malformed' in sys.argv:
                    connection.sendall(b'{not-json}\\n')
                    time.sleep(30)
                if message.get('id')==2 and '--fee-switch' in sys.argv:
                    connection.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,struct.pack('hh' if os.name=='nt' else 'ii',1,0))
                    stream.close()
                    connection.close()
                    connection=socket.create_connection((endpoint.hostname,endpoint.port))
                    stream=connection.makefile('r')
                    send({'id':10,'method':'login','params':{'address':address}})
                    for replacement in stream:
                        replacement=json.loads(replacement)
                        if replacement.get('method')=='job':
                            job=replacement['params']
                            submit(job,job['nonce_start'],3)
                        elif replacement.get('id')==3:
                            time.sleep(30)
                if message.get('id')==2 and '--reset' in sys.argv:
                    connection.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,struct.pack('hh' if os.name=='nt' else 'ii',1,0))
                    stream.close()
                    connection.close()
                    time.sleep(30)
                if message.get('method')=='job':
                    job=message['params']
                    if original is None:
                        original=job
                        submit(job,job['nonce_start'],2)
                    else:
                        submit(original,original['nonce_start']+1,3)
                        submit(job,job['nonce_start'],4)
                        submit({'job_id':'unknown'},0,5)
                        time.sleep(30)
        '''))
        fake.chmod(0o700)
        command = [sys.executable, str(Path(__file__).with_name('bench_pool_work.py')),
                   '--output', str(root / 'result'), '--miner', 'seine', '--executable', str(fake),
                   '--seconds', '1', '--warmup', '0', '--window-origin', 'launch',
                   '--stale-grace', str(grace), '--job-secs', '0.1' if rotate else '0']
        env = dict(os.environ)
        if tls:
            if shutil.which('openssl') is None:
                self.skipTest('TLS receiver test requires openssl to generate a disposable certificate')
            cert, key = root/'fixture.crt', root/'fixture.key'
            ca, ca_key, csr = root/'ca.crt', root/'ca.key', root/'fixture.csr'
            extensions = root/'extensions.cnf'
            extensions.write_text('subjectAltName=DNS:localhost\nbasicConstraints=critical,CA:FALSE\n'
                                  'keyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\n')
            for openssl_args in [
                ['req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(ca_key),
                 '-out',str(ca),'-days','1','-subj','/CN=Disposable fixture CA',
                 '-addext','basicConstraints=critical,CA:TRUE'],
                ['req','-new','-newkey','rsa:2048','-nodes','-keyout',str(key),
                 '-out',str(csr),'-subj','/CN=localhost'],
                ['x509','-req','-in',str(csr),'-CA',str(ca),'-CAkey',str(ca_key),
                 '-CAcreateserial','-out',str(cert),'-days','1','-extfile',str(extensions)],
            ]:
                subprocess.run(['openssl',*openssl_args],check=True,capture_output=True,timeout=15)
            env['FIXTURE_TEST_CA'] = str(ca)
            command[command.index('--miner')+1] = 'ntmminer'
            command += ['--tls-cert',str(cert),'--tls-key',str(key),
                        '--tls-name','wrong.invalid' if wrong_tls_name else 'localhost']
        if reset:
            command += ['--', '--reset']
        elif malformed:
            command += ['--', '--malformed']
        elif fee_switch:
            command += ['--', '--fee-switch']
        if os.name == 'nt':
            # Exercise the real native Job Object launcher with a harmless Python
            # client, inserting its script before the miner-style CLI arguments.
            command[command.index('--executable')+1] = sys.executable
            wrapper = (
                f'import sys; sys.path.insert(0, {str(Path(__file__).resolve().parent)!r}); '
                'import windows_job; original=windows_job.WindowsJobProcess; '
                f'windows_job.WindowsJobProcess=lambda argv, output: original([argv[0], {str(fake)!r}, *argv[1:]], output); '
                'import bench_pool_work; sys.argv=["bench_pool_work.py", *sys.argv[1:]]; '
                'raise SystemExit(bench_pool_work.main())'
            )
            command = [sys.executable, '-c', wrapper, *command[2:]]
        result = subprocess.run(command, capture_output=True, text=True, timeout=10, env=env)
        self.assertEqual(result.returncode, 1 if wrong_tls_name else 0, result.stderr + result.stdout)
        work = json.loads((root / 'result/work.json').read_text())
        wire = [json.loads(line) for line in (root / 'result/wire.jsonl').read_text().splitlines()]
        if tls and not wrong_tls_name:
            transport = [row for row in wire if row['direction'] == 'transport']
            self.assertEqual(len(transport), 1)
            self.assertEqual(transport[0]['tls_version'], 'TLSv1.3')
        acks = {row['message']['id']: row['message']['result'] for row in wire
                if row['direction'] == 'out' and row['message'].get('id') in [2,3,4,5]}
        return work, acks

    def test_tls13_fixture_collects_claims_with_certificate_validation(self):
        work, _ = self.run_case(0, rotate=False, tls=True)
        self.assertEqual(work['protocol_errors'], [])
        self.assertEqual(len(work['shares']), 1)
        self.assertTrue(work['shares'][0]['user_work'])
        self.assertEqual(work['transport']['tls_version'], 'TLSv1.3')
        self.assertNotIn('--mode', work['command'])

    def test_wrong_certificate_identity_cannot_produce_receipts(self):
        work, _ = self.run_case(0, rotate=False, tls=True, wrong_tls_name=True)
        self.assertEqual(work['shares'], [])
        self.assertTrue(work['protocol_errors'])

    def test_existing_plaintext_launch_commands_remain_unchanged(self):
        for miner in ['seine','longhorn']:
            args=SimpleNamespace(miner=miner,tls_cert=None,executable='/miner/tool',
                                 args=['--','--threads','2'])
            self.assertEqual(miner_command(args,'fixture-address',3333),
                ['/miner/tool','--mode','pool','--address','fixture-address',
                 '--pool-url','stratum+tcp://127.0.0.1:3333','--pool-worker','fixture',
                 '--threads','2'])

    def test_incomplete_tls_configuration_fails_before_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            for extra in [[], ['--tls-cert','missing.crt'], ['--tls-key','missing.key']]:
                result = subprocess.run([sys.executable,
                    str(Path(__file__).with_name('bench_pool_work.py')),
                    '--output',str(Path(directory)/'unused'),'--miner','ntmminer',
                    '--executable','must-never-launch',*extra],capture_output=True,text=True,timeout=5)
                self.assertEqual(result.returncode,2)
                self.assertIn('TLS',result.stderr)
                self.assertFalse((Path(directory)/'unused').exists())

    def test_replacement_preserves_old_header_but_rejects_stale_work(self):
        work, acks = self.run_case(0)
        self.assertEqual(work['protocol_errors'], [])
        first, stale, fresh, unknown = work['shares']
        self.assertEqual(stale['job'], first['job'])
        self.assertEqual(stale['header_base'], first['header_base'])
        self.assertNotEqual(fresh['header_base'], first['header_base'])
        self.assertNotEqual(fresh['job']['nonce_start'], first['job']['nonce_start'])
        self.assertTrue(stale['stale'])
        self.assertFalse(acks[3]['accepted'])
        self.assertTrue(acks[4]['accepted'])
        self.assertFalse(acks[5]['accepted'])
        self.assertIsNone(unknown['job'])
        self.assertEqual(work['rejected_receipts_in_window'], 2)

    def test_grace_allows_only_known_superseded_job(self):
        work, acks = self.run_case(2)
        self.assertTrue(acks[3]['accepted'])
        self.assertFalse(acks[5]['accepted'])
        self.assertEqual(work['stale_receipts_in_window'], 1)
        self.assertEqual(work['rejected_receipts_in_window'], 1)

    def test_default_static_case_never_replaces_job(self):
        work, acks = self.run_case(0, rotate=False)
        self.assertEqual(len(work['shares']), 1)
        self.assertTrue(acks[2]['accepted'])
        self.assertEqual(work['shares'][0]['job']['template_id'], 'fixture-template-user')
        self.assertEqual(work['shares'][0]['header_base'], work['header_base'])
        self.assertEqual(work['rejected_receipts_in_window'], 0)

    def test_unexpected_reset_during_measurement_is_not_hidden(self):
        work, _ = self.run_case(0, reset=True)
        self.assertEqual(work['protocol_errors'], [])
        self.assertTrue(work['connection_review_required'])
        resets = [event for event in work['connection_events'] if event['kind'] == 'peer_reset' and event['phase'] == 'measurement']
        self.assertEqual(len(resets), 1)
        self.assertEqual(resets[0]['phase'], 'measurement')
        self.assertEqual(resets[0]['role'], 'user')
        self.assertGreaterEqual(resets[0]['elapsed'], work['shares'][0]['elapsed'])
        self.assertEqual(len(work['shares']), 1, 'A disconnected miner earns no phantom work')

    def test_malformed_message_remains_a_protocol_error(self):
        work, _ = self.run_case(0, rotate=False, malformed=True)
        self.assertTrue(work['protocol_errors'])
        self.assertFalse(work['connection_review_required'])

    def test_fee_reset_and_user_reconnect_preserve_both_work_streams(self):
        work, _ = self.run_case(0, rotate=False, fee_switch=True)
        self.assertEqual(work['protocol_errors'], [])
        self.assertTrue(work['connection_review_required'])
        self.assertEqual([share['user_work'] for share in work['shares']], [False, True])
        self.assertNotEqual(work['shares'][0]['header_base'], work['shares'][1]['header_base'])
        resets = [event for event in work['connection_events'] if event['kind'] == 'peer_reset' and event['phase'] == 'measurement']
        self.assertEqual(len(resets), 1)
        self.assertEqual(resets[0]['role'], 'fee')


if __name__ == '__main__':
    unittest.main()
