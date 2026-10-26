#!/usr/bin/env python3
"""Local fixture harness. Never point at a production collector."""
import argparse
import json
import subprocess
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from alert_fixtures import messages

ROOT = Path(__file__).resolve().parent
PARSER = argparse.ArgumentParser(description=__doc__)
PARSER.add_argument('--port', type=int, default=9081)
PARSER.add_argument('--collector-port', type=int, default=9080)
ARGS = PARSER.parse_args()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def respond(self, status, data, content_type):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path == '/alerts.json':
            fixtures = messages()
            state = parse_qs(parsed.query).get('state', ['legacy'])[0]
            if state not in fixtures:
                self.respond(404, b'Unknown fixture state', 'text/plain')
                return
            revision = subprocess.check_output(['git', 'describe', '--always', '--dirty'], cwd=ROOT).decode().strip()
            body = {'source_revision': revision, 'fixture_only': True,
                    'note': 'Real sender payload; native Discord appearance requires an authorized test message.',
                    'states': list(fixtures), 'state': state, 'webhook_payload': fixtures[state]}
            self.respond(200, json.dumps(body, indent=2).encode(), 'application/json')
        elif self.path == '/fixture.json':
            self.respond(200, (ROOT.parent / 'diagnostics-fixture.json').read_bytes(), 'application/json')
        elif self.path == '/revision':
            revision = subprocess.check_output(['git', 'describe', '--always', '--dirty'], cwd=ROOT).decode().strip()
            self.respond(200, revision.encode(), 'text/plain')
        elif self.path in ('/', '/index.html'):
            self.respond(200, (ROOT / 'index.html').read_bytes(), 'text/html; charset=utf-8')
        else:
            self.respond(404, b'Not found', 'text/plain')

    def do_POST(self):
        if self.path != '/submit':
            self.respond(404, b'Not found', 'text/plain')
            return
        length = int(self.headers.get('Content-Length', 0))
        if length > 40000:
            self.respond(413, b'Too large', 'text/plain')
            return
        request = urllib.request.Request(
            f'http://127.0.0.1:{ARGS.collector_port}/v1/reports',
            self.rfile.read(length), {'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                status, body = response.status, response.read().decode()
        except urllib.error.HTTPError as error:
            status, body = error.code, error.read().decode()
        except (urllib.error.URLError, TimeoutError):
            status, body = 503, 'Local collector unavailable'
        self.respond(200, json.dumps({'status': status, 'body': body}).encode(), 'application/json')


if __name__ == '__main__':
    print(f'Fixture showcase: http://localhost:{ARGS.port}', flush=True)
    try:
        ThreadingHTTPServer(('0.0.0.0', ARGS.port), Handler).serve_forever()
    except KeyboardInterrupt:
        pass
