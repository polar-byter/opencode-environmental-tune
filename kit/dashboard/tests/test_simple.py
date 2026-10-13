"""Focused exercises for learning iteration 3, independent of a running server."""
import json
from http.client import HTTPMessage
from http.server import HTTPServer
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, call, patch

from kit.dashboard import simple


class Iteration3TaskView(unittest.TestCase):
    def test_returns_summary_instead_of_raw_events(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'events.jsonl'
            path.write_text(
                '{"kind":"start","at":100,"title":"Study"}\n'
                '{"kind":"test","at":110,"status":"passed"}\n',
                encoding='utf-8',
            )
            self.assertEqual(simple.task_view(path), {
                'title': 'Study', 'status': 'running', 'event_count': 2,
                'last_event_at': 110, 'work_runs': 1, 'green_work_runs': 1,
                'reworks': 0, 'executor_failures': 0,
            })

    def test_missing_file_has_clear_error(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, '^no events yet$'):
                simple.task_view(Path(folder) / 'missing.jsonl')

    def test_empty_file_has_clear_error(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'events.jsonl'
            path.write_text('', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, '^no events yet$'):
                simple.task_view(path)

    def test_reads_changed_file_on_next_call(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'events.jsonl'
            first = '{"kind":"start","at":100}\n'
            path.write_text(first, encoding='utf-8')
            self.assertEqual(simple.task_view(path)['event_count'], 1)
            path.write_text(
                first + '{"kind":"test","at":110,"status":"passed"}\n',
                encoding='utf-8',
            )
            result = simple.task_view(path)
            self.assertEqual(
                (result['event_count'], result['work_runs'], result['green_work_runs']),
                (2, 1, 1),
            )

    def test_invalid_journal_keeps_reader_error(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'events.jsonl'
            path.write_text('{"kind":"start","at":100}\n[]\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'line 2'):
                simple.task_view(path)

    def test_disk_error_is_not_hidden(self):
        error = OSError('cannot read file')
        with patch('kit.dashboard.simple.journal.read_events', side_effect=error):
            with self.assertRaises(OSError) as caught:
                simple.task_view(Path('events.jsonl'))
        self.assertIs(caught.exception, error)


class Iteration3SendBytes(unittest.TestCase):
    def assert_response(self, status, content_type, body):
        handler = Mock(spec=['send_response', 'send_header', 'end_headers', 'wfile'])
        result = simple.Handler.send_bytes(handler, status, content_type, body)
        self.assertIsNone(result)
        calls = handler.method_calls
        self.assertEqual(calls[:1], [call.send_response(status)])
        self.assertCountEqual(calls[1:4], [
            call.send_header('Content-Type', content_type),
            call.send_header('Content-Length', str(len(body))),
            call.send_header('Cache-Control', 'no-store'),
        ])
        self.assertEqual(calls[4:], [call.end_headers(), call.wfile.write(body)])

    def test_sends_status_headers_then_body(self):
        self.assert_response(200, 'text/plain; charset=utf-8', b'OK')

    def test_length_counts_utf8_bytes_not_characters(self):
        body = '\u041f\u0440\u0438\u0432\u0435\u0442'.encode('utf-8')
        self.assertEqual(len(body), 12)
        self.assert_response(200, 'text/plain; charset=utf-8', body)

    def test_empty_body_is_written_with_zero_length(self):
        self.assert_response(200, 'application/json', b'')

    def test_can_send_error_status(self):
        self.assert_response(404, 'text/plain; charset=utf-8', b'not found')

    def test_write_error_is_not_hidden(self):
        handler = Mock(spec=['send_response', 'send_header', 'end_headers', 'wfile'])
        error = OSError('connection closed')
        handler.wfile.write.side_effect = error
        with self.assertRaises(OSError) as caught:
            simple.Handler.send_bytes(handler, 200, 'text/plain', b'OK')
        self.assertIs(caught.exception, error)


def get_handler(path, host='localhost:49152'):
    headers = HTTPMessage()
    if host is not None:
        headers['Host'] = host
    return SimpleNamespace(
        headers=headers,
        path=path,
        server=SimpleNamespace(server_port=49152, server_address=('127.0.0.1', 49152),
                               journal_path=Path('events.jsonl')),
        send_bytes=Mock(),
    )


class Iteration3GetHost(unittest.TestCase):
    def assert_rejected(self, host):
        handler = get_handler('/api/task', host)
        with patch('kit.dashboard.simple.task_view') as view, \
                patch('kit.dashboard.simple.PAGE') as page:
            self.assertIsNone(simple.Handler.do_GET(handler))
        handler.send_bytes.assert_called_once()
        status, content_type, body = handler.send_bytes.call_args.args
        self.assertEqual(status, 403)
        self.assertEqual(content_type.split(';')[0], 'text/plain')
        self.assertIsInstance(body, bytes)
        view.assert_not_called()
        page.read_bytes.assert_not_called()

    def test_missing_host_is_rejected(self):
        self.assert_rejected(None)

    def test_foreign_host_is_rejected_before_reading(self):
        self.assert_rejected('example.test:49152')

    def test_wrong_port_is_rejected(self):
        for host in ['localhost:8765', '127.0.0.1:8765']:
            with self.subTest(host=host):
                self.assert_rejected(host)

    def test_port_is_required(self):
        for host in ['localhost', '127.0.0.1']:
            with self.subTest(host=host):
                self.assert_rejected(host)

    def test_suffix_userinfo_and_extra_text_are_rejected(self):
        for host in ['localhost.evil.test:49152', '127.0.0.1.evil.test:49152',
                     'user@localhost:49152', 'localhost:49152/path',
                     'localhost:49152,example.test:49152']:
            with self.subTest(host=host):
                self.assert_rejected(host)


class Iteration3GetRoutes(unittest.TestCase):
    def response(self, handler):
        handler.send_bytes.assert_called_once()
        status, content_type, body = handler.send_bytes.call_args.args
        self.assertIsInstance(body, bytes)
        return status, content_type, body

    def json_response(self, handler, expected_status, expected):
        status, content_type, body = self.response(handler)
        self.assertEqual(status, expected_status)
        self.assertEqual(content_type, 'application/json; charset=utf-8')
        self.assertEqual(json.loads(body.decode('utf-8')), expected)

    def test_root_returns_page_bytes(self):
        handler = get_handler('/')
        with patch('kit.dashboard.simple.PAGE') as page, \
                patch('kit.dashboard.simple.task_view') as view:
            page.read_bytes.return_value = b'<html>Study</html>'
            self.assertIsNone(simple.Handler.do_GET(handler))
        self.assertEqual(self.response(handler),
                         (200, 'text/html; charset=utf-8', b'<html>Study</html>'))
        page.read_bytes.assert_called_once_with()
        view.assert_not_called()

    def test_api_returns_utf8_json_summary(self):
        handler = get_handler('/api/task')
        summary = {'title': '\u0423\u0447\u0451\u0431\u0430', 'event_count': 2}
        with patch('kit.dashboard.simple.task_view', return_value=summary) as view:
            self.assertIsNone(simple.Handler.do_GET(handler))
        self.json_response(handler, 200, summary)
        view.assert_called_once_with(handler.server.journal_path)

    def test_local_hosts_are_allowed_case_insensitively(self):
        for host in ['localhost:49152', '127.0.0.1:49152', 'LOCALHOST:49152']:
            with self.subTest(host=host):
                handler = get_handler('/api/task', host)
                with patch('kit.dashboard.simple.task_view', return_value={'event_count': 1}):
                    simple.Handler.do_GET(handler)
                self.json_response(handler, 200, {'event_count': 1})

    def test_query_is_ignored_for_known_paths(self):
        for path in ['/?refresh=1', '/api/task?refresh=1']:
            with self.subTest(path=path):
                handler = get_handler(path)
                with patch('kit.dashboard.simple.PAGE') as page, \
                        patch('kit.dashboard.simple.task_view', return_value={'event_count': 1}):
                    page.read_bytes.return_value = b'<html></html>'
                    simple.Handler.do_GET(handler)
                if path.startswith('/api/task'):
                    self.json_response(handler, 200, {'event_count': 1})
                else:
                    self.assertEqual(self.response(handler),
                                     (200, 'text/html; charset=utf-8', b'<html></html>'))

    def test_unknown_path_returns_404_without_reading_files(self):
        handler = get_handler('/../../private.txt')
        with patch('kit.dashboard.simple.PAGE') as page, \
                patch('kit.dashboard.simple.task_view') as view:
            self.assertIsNone(simple.Handler.do_GET(handler))
        status, content_type, body = self.response(handler)
        self.assertEqual(status, 404)
        self.assertEqual(content_type.split(';')[0], 'text/plain')
        page.read_bytes.assert_not_called()
        view.assert_not_called()

    def test_value_error_becomes_json_400(self):
        handler = get_handler('/api/task')
        with patch('kit.dashboard.simple.task_view', side_effect=ValueError('line 2: bad event')):
            simple.Handler.do_GET(handler)
        self.json_response(handler, 400, {'error': 'line 2: bad event'})

    def test_journal_disk_error_becomes_safe_json_500(self):
        handler = get_handler('/api/task')
        with patch('kit.dashboard.simple.task_view', side_effect=OSError('private file path')):
            simple.Handler.do_GET(handler)
        self.json_response(handler, 500, {'error': 'cannot read journal or page'})

    def test_page_disk_error_becomes_safe_json_500(self):
        handler = get_handler('/')
        with patch('kit.dashboard.simple.PAGE') as page:
            page.read_bytes.side_effect = OSError('private file path')
            simple.Handler.do_GET(handler)
        self.json_response(handler, 500, {'error': 'cannot read journal or page'})

    def test_send_failure_does_not_send_a_second_response(self):
        handler = get_handler('/')
        error = OSError('connection closed')
        handler.send_bytes.side_effect = error
        with patch('kit.dashboard.simple.PAGE') as page:
            page.read_bytes.return_value = b'<html></html>'
            with self.assertRaises(OSError) as caught:
                simple.Handler.do_GET(handler)
        self.assertIs(caught.exception, error)
        handler.send_bytes.assert_called_once_with(
            200, 'text/html; charset=utf-8', b'<html></html>',
        )


class Iteration3MakeServer(unittest.TestCase):
    def test_creates_local_server_with_handler_and_returns_it(self):
        with patch('kit.dashboard.simple.HTTPServer') as constructor:
            server = simple.make_server(8765, Path('events.jsonl'))
        constructor.assert_called_once_with(('127.0.0.1', 8765), simple.Handler)
        self.assertIs(server, constructor.return_value)

    def test_stores_resolved_journal_path(self):
        path = Path('kit/dashboard/examples/../examples/events.jsonl')
        with patch('kit.dashboard.simple.HTTPServer'):
            server = simple.make_server(8765, path)
        self.assertEqual(server.journal_path, path.resolve())
        self.assertIsInstance(server.journal_path, Path)
        self.assertTrue(server.journal_path.is_absolute())

    def test_missing_journal_is_allowed_without_reading_it(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'missing.jsonl'
            with patch('kit.dashboard.simple.HTTPServer'), \
                    patch('kit.dashboard.simple.task_view') as view, \
                    patch('kit.dashboard.simple.journal.read_events') as reader:
                server = simple.make_server(8765, path)
            self.assertEqual(server.journal_path, path.resolve())
            self.assertFalse(path.exists())
            view.assert_not_called()
            reader.assert_not_called()

    def test_does_not_serve_requests_or_close_server(self):
        with patch('kit.dashboard.simple.HTTPServer') as constructor:
            simple.make_server(8765, Path('events.jsonl'))
        constructor.return_value.serve_forever.assert_not_called()
        constructor.return_value.handle_request.assert_not_called()
        constructor.return_value.shutdown.assert_not_called()
        constructor.return_value.server_close.assert_not_called()

    def test_constructor_error_is_not_hidden(self):
        error = OSError('port is occupied')
        with patch('kit.dashboard.simple.HTTPServer', side_effect=error):
            with self.assertRaises(OSError) as caught:
                simple.make_server(8765, Path('events.jsonl'))
        self.assertIs(caught.exception, error)

    def test_zero_port_creates_real_server_on_free_local_port(self):
        server = simple.make_server(0, Path('events.jsonl'))
        self.addCleanup(server.server_close)
        self.assertIsInstance(server, HTTPServer)
        self.assertEqual(server.server_address[0], '127.0.0.1')
        self.assertGreater(server.server_port, 0)
        self.assertEqual(server.server_port, server.server_address[1])
        self.assertIs(server.RequestHandlerClass, simple.Handler)
        self.assertEqual(server.journal_path, Path('events.jsonl').resolve())
