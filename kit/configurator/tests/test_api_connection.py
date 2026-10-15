"""Real loopback HTTP checks: the desktop uses the entered base URL and bearer key."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import unittest

from kit.configurator import sources, workflow


class ApiConnectionTests(unittest.TestCase):
    def test_discovery_and_common_errors_against_real_compatible_endpoint(self):
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                requests.append((self.path, self.headers.get('Authorization')))
                if self.path == '/ok/v1/models':
                    code, body = 200, b'{"data":[{"id":"manual-model"},{"id":"other"}]}'
                elif self.path == '/denied/v1/models':
                    code, body = 401, b'private-provider-error-test-key'
                elif self.path == '/broken/v1/models':
                    code, body = 200, b'not-json-private-provider-error'
                else:
                    code, body = 404, b'private-provider-error-test-key'
                self.send_response(code)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            self.assertEqual(sources.api_models(base + '/ok/v1', 'test-key'), ['manual-model', 'other'])
            for path, expected in (('/denied/v1', 'API key'), ('/missing/v1', 'manually'), ('/broken/v1', 'manually')):
                with self.subTest(path=path), self.assertRaises(ValueError) as caught:
                    sources.api_models(base + path, 'test-key')
                message = workflow.model_error('api', caught.exception)
                self.assertIn(expected, message)
                self.assertNotIn('private-provider-error', message)
                self.assertNotIn('test-key', message)
            self.assertEqual(len(requests), 4)
            self.assertTrue(all(header == 'Bearer test-key' for path, header in requests))
            self.assertTrue(all(path.endswith('/models') for path, header in requests))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
