"""Tests for kit/dashboard/server.py: routing and request checks, then one real local server."""
import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

from kit.dashboard import server


class Step7Routing(unittest.TestCase):
    def test_match(self):
        self.assertEqual(server.match_route('GET', '/'), ('page', {}))
        self.assertEqual(server.match_route('GET', '/api/projects/kit/tasks/t-1'),
                         ('task_view', {'project': 'kit', 'task': 't-1'}))
        self.assertEqual(server.match_route('GET', '/api/projects/kit/tasks/t-1/sessions'),
                         ('task_sessions', {'project': 'kit', 'task': 't-1'}))
        self.assertEqual(server.match_route('POST', '/api/projects/kit/settings/apply'),
                         ('settings_apply', {'project': 'kit'}))

    def test_no_match(self):
        for method, path in (('POST', '/api/meta'), ('GET', '/api/meta/'), ('GET', '/api/projects//tasks/x'),
                             ('GET', '/api/projects/kit/settings/save'), ('DELETE', '/'), ('GET', '/nope')):
            self.assertIsNone(server.match_route(method, path), (method, path))


class Step7Checks(unittest.TestCase):
    def test_host(self):
        self.assertTrue(server.host_allowed('127.0.0.1:8765', 8765))
        self.assertTrue(server.host_allowed('LOCALHOST:8765', 8765))
        for host in (None, '127.0.0.1:9999', 'evil.example:8765', '127.0.0.1', 'localhost.evil:8765'):
            self.assertFalse(server.host_allowed(host, 8765), host)

    def test_post(self):
        ok = {'x-dashboard-token': 'abc', 'content-type': 'application/json; charset=utf-8'}
        self.assertIsNone(server.post_allowed(ok, 'abc'))
        self.assertEqual(server.post_allowed({'content-type': 'application/json'}, 'abc'), 'missing token')
        self.assertEqual(server.post_allowed({**ok, 'x-dashboard-token': 'abd'}, 'abc'), 'wrong token')
        self.assertEqual(server.post_allowed({**ok, 'content-type': 'text/plain'}, 'abc'), 'json body required')

    def test_body(self):
        self.assertEqual(server.read_json_body('{"a": "ü"}'.encode('utf-8')), {'a': 'ü'})
        for raw in (b'[1]', b'{oops', b'x' * (server.MAX_BODY + 1)):
            with self.assertRaises(ValueError):
                server.read_json_body(raw)


class Step9LiveServer(unittest.TestCase):
    """End-to-end smoke test on a free port: meta, a refused POST and an unknown route."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / 'kit'
        root.mkdir()
        (root / 'opencode.jsonc').write_text('{"model": "a/b"}', encoding='utf-8')
        self.httpd = server.make_server(0, [root])
        thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)
        self.base = f'http://127.0.0.1:{self.httpd.port}'

    def call(self, path, method='GET', body=None, headers=None):
        request = urllib.request.Request(self.base + path, data=body, method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_meta_and_projects(self):
        status, meta = self.call('/api/meta')
        self.assertEqual((status, meta['projects']), (200, [{'key': 'kit', 'name': 'kit'}]))
        self.assertEqual(meta['token'], self.httpd.token)
        status, rows = self.call('/api/projects')
        self.assertEqual((status, rows[0]['tasks']), (200, []))

    def test_refusals(self):
        self.assertEqual(self.call('/api/projects/kit/settings/reset', 'POST', b'{}',
                                   {'Content-Type': 'application/json'})[0], 403)
        self.assertEqual(self.call('/api/meta', headers={'Host': 'evil.example'})[0], 403)
        self.assertEqual(self.call('/api/nope')[0], 404)
        self.assertEqual(self.call('/api/projects/ghost/settings')[0], 400)
        self.assertEqual(self.call('/api/projects/kit/tasks/CON')[0], 400)

    def test_allowed_post(self):
        status, result = self.call('/api/projects/kit/settings/reset', 'POST', b'{}',
                                   {'Content-Type': 'application/json', 'X-Dashboard-Token': self.httpd.token})
        self.assertEqual((status, result), (200, {'removed': False}))


if __name__ == '__main__':
    unittest.main()
