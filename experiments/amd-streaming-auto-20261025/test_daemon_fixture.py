import json
import threading
import unittest
from urllib.request import Request,urlopen
from daemon_fixture import Server

class DaemonFixtureTest(unittest.TestCase):
    def test_authenticated_templates_and_sse_stay_local(self):
        server=Server();thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            for route in ['/api/mining/blocktemplate?address=user','/api/mining/blocktemplate?address=fee']:
                request=Request(f'http://127.0.0.1:{server.server_port}'+route,headers={'Authorization':'Bearer native-fixture'})
                with urlopen(request,timeout=2) as response:body=json.load(response)
                self.assertEqual(len(bytes.fromhex(body['header_base'])),92)
                self.assertEqual(bytes.fromhex(body['target']),bytes(32))
            request=Request(f'http://127.0.0.1:{server.server_port}/api/events',headers={'Authorization':'Bearer native-fixture'})
            with urlopen(request,timeout=2) as response:self.assertEqual(response.readline(),b': keepalive\n')
            self.assertEqual(server.errors,[])
        finally:server.finish();thread.join(timeout=2)

if __name__=='__main__':unittest.main()
