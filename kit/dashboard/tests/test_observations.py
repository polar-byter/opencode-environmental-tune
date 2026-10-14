"""Public session observations and non-blocking collection."""
from pathlib import Path
import threading
import time
import unittest

from kit.dashboard.observations import observations, attach_models, SessionReader


def exported(sid, model, parts, completed=120000):
    return {'info': {'id': sid}, 'messages': [{'id': 'message', 'type': 'assistant', 'time': {'created': 110000, 'completed': completed}, 'model': {'providerID': 'provider', 'id': model}, 'content': parts}]}


class Observations(unittest.TestCase):
    def test_actual_models_and_public_feed_exclude_reasoning_shell_and_output(self):
        exports = [exported('root', 'master', [
            {'type': 'reasoning', 'text': 'private thought'},
            {'type': 'text', 'text': 'Architecture is ready'},
            {'type': 'tool', 'name': 'task', 'state': {'status': 'completed', 'input': {'prompt': 'secret'}, 'output': 'hidden', 'metadata': {'sessionID': 'child'}}},
            {'type': 'tool', 'name': 'bash', 'state': {'input': {'command': 'secret key'}, 'output': 'hidden'}}]),
            exported('child', 'executor', [{'type': 'tool', 'name': 'edit', 'state': {'status': 'running', 'input': {'filePath': 'app/code.py'}}}], completed=None)]
        view = observations(exports, 'root', 100, 130)
        self.assertEqual(view['models'], {'master_chief': ['provider/master'], 'executor': ['provider/executor']})
        self.assertNotIn('secret', str(view)); self.assertNotIn('private thought', str(view)); self.assertNotIn('hidden', str(view))
        self.assertEqual(view['current'][0]['target'], 'app/code.py')
        items = [{'attempts': [{'at': 105, 'inspection_at': 115}]}]
        attach_models(items, view)
        self.assertEqual(items[0]['model'], 'provider/executor')

    def test_messages_outside_task_window_are_ignored(self):
        self.assertEqual(observations([exported('root', 'model', [])], 'root', 200, 300)['models']['master_chief'], [])

    def test_http_view_does_not_wait_for_collector(self):
        entered, release = threading.Event(), threading.Event()
        def collect(root, sid):
            entered.set(); release.wait(2); return [exported('root', 'master', [])]
        reader = SessionReader(collect=collect)
        events = [{'kind': 'start', 'session': 'root', 'at': 100}]
        before = time.monotonic()
        self.assertTrue(reader.view(Path.cwd(), events)['loading'])
        self.assertLess(time.monotonic() - before, .3)
        self.assertTrue(entered.wait(1)); release.set()
        for _ in range(100):
            if reader.view(Path.cwd(), events)['available']: break
            time.sleep(.01)
        self.assertTrue(reader.view(Path.cwd(), events)['available'])

    def test_failure_is_retriable_and_finished_success_is_cached(self):
        calls = []
        def collect(root, sid):
            calls.append(sid)
            if len(calls) == 1: raise ValueError('bad export')
            return [exported('root', 'master', [])]
        reader = SessionReader(collect=collect, ttl=0)
        events = [{'kind': 'start', 'session': 'root', 'at': 100}, {'kind': 'finish', 'at': 130}]
        for _ in range(100):
            value = reader.view(Path.cwd(), events)
            if value['available'] and not value['loading']: break
            time.sleep(.01)
        self.assertTrue(value['available'])
        for _ in range(3): reader.view(Path.cwd(), events)
        self.assertEqual(len(calls), 2)

    def test_no_session_never_calls_collector(self):
        reader = SessionReader(collect=lambda *args: self.fail('unexpected collection'))
        self.assertFalse(reader.view(Path.cwd(), [{'kind': 'start', 'at': 100}])['loading'])


if __name__ == '__main__':
    unittest.main()
