"""Stand-in for seine's control API in the mining OS package tests.

    python3 scripts/package_test_api.py PORT TOKEN BODY_JSON

Serves BODY_JSON at GET /v1/miner/stats to requests with the bearer TOKEN.
The body is re-read on every request, so a test can change it between calls.
"""

import http.server
import sys

port, token, body_path = int(sys.argv[1]), sys.argv[2], sys.argv[3]


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.headers.get("Authorization") != f"Bearer {token}":
            self.send_response(401)
            self.end_headers()
            return
        if self.path != "/v1/miner/stats":
            self.send_response(404)
            self.end_headers()
            return
        with open(body_path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


http.server.HTTPServer(("127.0.0.1", port), Handler).serve_forever()
