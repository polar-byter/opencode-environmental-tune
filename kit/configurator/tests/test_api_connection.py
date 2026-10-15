"""Real loopback HTTP checks: the desktop uses the entered base URL and bearer key."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import unittest
from unittest.mock import patch
import json
import urllib.error

from kit.configurator import api_connection, sources, workflow


class ApiConnectionTests(unittest.TestCase):
    def test_explicit_probe_uses_read_only_endpoints_and_never_returns_account_data(self):
        requests=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_GET(self):
                requests.append((self.path,self.headers.get('Authorization')))
                if self.path=='/v1/key':
                    body=json.dumps({'data':{'label':'private-label','usage':123,'is_free_tier':True}}).encode()
                else: body=b'{"data":[{"id":"one"}]}'
                self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base=f'http://127.0.0.1:{server.server_port}/v1'
        try:
            self.assertEqual(api_connection.check(base,'key-for-test'),{'authenticated':False,'models':1})
            with patch.object(api_connection.openrouter,'is_openrouter',return_value=True):
                self.assertEqual(api_connection.check(base,'key-for-test'),{'authenticated':True})
            self.assertEqual(requests,[('/v1/models','Bearer key-for-test'),('/v1/key','Bearer key-for-test')])
        finally:
            server.shutdown();server.server_close();thread.join(2)

    def test_connection_errors_never_include_raw_server_text(self):
        for code,expected in ((401,'API key'),(403,'API key'),(404,'base URL'),(429,'429'),(500,'error')):
            message=api_connection.error_message(urllib.error.HTTPError('https://api/key',code,'secret-key',{},None))
            self.assertIn(expected,message);self.assertNotIn('secret-key',message)
        self.assertIn('timed out',api_connection.error_message(TimeoutError('secret-key')))
        self.assertNotIn('secret-key',api_connection.error_message(ValueError('secret-key')))

    def test_probe_rejects_redirects_and_invalid_authenticated_payload(self):
        requests=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_GET(self):
                requests.append(self.path)
                if self.path=='/redirect/models':
                    self.send_response(302);self.send_header('Location','/leak');self.end_headers()
                else:
                    body=b'{"data":{}}';self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base=f'http://127.0.0.1:{server.server_port}'
        try:
            with self.assertRaises(urllib.error.HTTPError):api_connection.check(base+'/redirect','private')
            self.assertNotIn('/leak',requests)
            with patch.object(api_connection.openrouter,'is_openrouter',return_value=True),self.assertRaises(ValueError):
                api_connection.check(base+'/invalid','private')
        finally:
            server.shutdown();server.server_close();thread.join(2)

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
