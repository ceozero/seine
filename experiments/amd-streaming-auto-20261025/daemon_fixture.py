"""Local daemon API fixture for long productive tests without external fee pools."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import time
from urllib.parse import urlsplit


class Handler(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def log_message(self,*args):pass
    def do_GET(self):
        self.server.events.append({'time':time.time(),'path':self.path})
        if self.headers.get('Authorization')!='Bearer native-fixture':
            self.server.errors.append('Missing fixture authentication')
            self.send_error(401);return
        path=urlsplit(self.path).path
        if path=='/api/events':
            self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
            try:
                while not self.server.stop.is_set():
                    self.wfile.write(b': keepalive\n\n');self.wfile.flush()
                    self.server.stop.wait(2)
            except (ConnectionError,OSError):pass
            self.close_connection=True
            return
        if path=='/api/mining/blocktemplate':
            payload={'block':{'header':{'height':1,'difficulty':1,'nonce':0},'txns':[]},'target':'00'*32,'header_base':'00'*92,'template_id':'native-automatic-streaming'}
            raw=json.dumps(payload).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers()
            try:self.wfile.write(raw)
            except (ConnectionError,OSError):pass
        else:
            self.server.errors.append('Unexpected route '+path);self.send_error(404)
    def do_POST(self):
        self.server.errors.append('Unexpected write '+self.path);self.send_error(500)


class Server(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self):
        self.events=[];self.errors=[];self.stop=threading.Event()
        super().__init__(('127.0.0.1',0),Handler)
    def finish(self):
        self.stop.set();self.shutdown();self.server_close()
