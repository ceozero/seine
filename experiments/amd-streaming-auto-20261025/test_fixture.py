import json
import socket
import threading
import unittest

from fixture import Server


class FixtureTest(unittest.TestCase):
    def test_keepalives_do_not_disconnect_or_hide_later_requests(self):
        server = Server(('127.0.0.1', 0))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with socket.create_connection(server.server_address, timeout=2) as conn:
                stream = conn.makefile('rb')
                for identifier in [1, 2]:
                    conn.sendall(b'\n\r\n \n' + json.dumps({'method': 'login', 'id': identifier}).encode() + b'\n')
                    self.assertEqual(json.loads(stream.readline())['id'], identifier)
                    self.assertEqual(json.loads(stream.readline())['method'], 'job')
                stream.close()
            self.assertEqual(len(server.events), 2)
            self.assertEqual(server.errors, [])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == '__main__':
    unittest.main()
