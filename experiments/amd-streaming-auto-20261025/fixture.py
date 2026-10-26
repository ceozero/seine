"""Loopback-only Stratum fixture; blank lines are keepalives, not JSON."""
import hashlib
import json
import socketserver
import time


def address():
    digest = hashlib.sha3_256(b'blocknet_stealth_address_checksum' + b'blocknet_mainnet' + bytes(64)).digest()[:4]
    value = int.from_bytes(digest, 'big')
    encoded = ''
    while value:
        value, digit = divmod(value, 58)
        encoded = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'[digit] + encoded
    return '1' * 64 + encoded


class Fixture(socketserver.StreamRequestHandler):
    def handle(self):
        try:
            for raw in self.rfile:
                if not raw.strip():
                    continue
                req = json.loads(raw)
                self.server.events.append({'time': time.time(), 'method': req.get('method')})
                if req.get('method') == 'login':
                    response = {'id': req['id'], 'status': 'ok', 'result': {'protocol_version': 2, 'capabilities': ['login_negotiation', 'submit_claimed_hash']}}
                    work = {'method': 'job', 'params': {'job_id': 'native-streaming-validation', 'header_base': '00' * 92, 'target': '00' * 32, 'network_target': '00' * 32, 'height': 1, 'nonce_start': 0, 'nonce_end': 2**63 - 1}}
                    self.wfile.write((json.dumps(response) + '\n' + json.dumps(work) + '\n').encode())
                    self.wfile.flush()
                elif req.get('method') == 'submit':
                    self.server.errors.append('Impossible-target solution')
        except (ConnectionError, OSError):
            pass
        except (ValueError, KeyError) as error:
            self.server.errors.append(repr(error))


class Server(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address):
        self.events = []
        self.errors = []
        super().__init__(address, Fixture)
