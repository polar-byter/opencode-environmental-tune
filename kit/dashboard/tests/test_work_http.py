"""Settings launch authorization, deduplication and architecture viewer."""
import json
import subprocess
import unittest
from unittest.mock import Mock, patch

from kit.dashboard.tests import test_runtime
from kit.dashboard.tracking import publish_plan


class WorkHTTP(unittest.TestCase):
    setUp = test_runtime.RuntimeHTTP.setUp
    close = test_runtime.RuntimeHTTP.close
    request = test_runtime.RuntimeHTTP.request

    def settings_headers(self):
        return {'Origin': f'http://127.0.0.1:{self.server.server_port}', 'X-Dashboard-UI-Token': self.server.ui_token}

    def test_settings_requires_origin_and_ui_token(self):
        with patch.object(self.server, 'open_configurator') as launch:
            for headers in ({}, {'X-Dashboard-UI-Token': self.server.ui_token}, {'Origin': 'https://foreign', 'X-Dashboard-UI-Token': self.server.ui_token}, dict(self.settings_headers(), **{'X-Dashboard-UI-Token': self.server.control_token})):
                self.assertEqual(self.request('/api/models/open', 'POST', headers)[0], 403)
            launch.assert_not_called()

    def test_settings_success_failure_and_no_user_parameters(self):
        with patch.object(self.server, 'open_configurator', return_value={'status': 'started', 'reused': False}) as launch:
            self.assertEqual(self.request('/api/models/open', 'POST', self.settings_headers())[0], 200)
            self.assertEqual(self.request('/api/models/open?root=other', 'POST', self.settings_headers())[0], 400)
            self.assertEqual(launch.call_count, 1)
        with patch.object(self.server, 'open_configurator', side_effect=OSError('unavailable')):
            self.assertEqual(self.request('/api/models/open', 'POST', self.settings_headers())[0], 503)
        data = json.loads(self.request('/api/ui')[2])
        self.assertEqual(data['token'], self.server.ui_token)
        self.assertNotEqual(data['token'], self.server.control_token)
        self.assertEqual(self.request('/api/stop', 'POST', {'X-Dashboard-Token': data['token']})[0], 403)

    def test_process_launch_uses_server_project_and_reuses_live_process(self):
        process = Mock(pid=123)
        process.wait.side_effect = subprocess.TimeoutExpired('configurator', .35)
        process.poll.return_value = None
        with patch('kit.dashboard.runtime.subprocess.Popen', return_value=process) as launch:
            self.assertFalse(self.server.open_configurator()['reused'])
            self.assertTrue(self.server.open_configurator()['reused'])
            self.assertEqual(launch.call_count, 1)
            self.assertEqual(launch.call_args.kwargs['cwd'], self.root.resolve())
            self.assertEqual(launch.call_args.args[0][-2:], ['-m', 'kit.configurator.app'])
            process.poll.return_value = 0
            self.server.open_configurator()
            self.assertEqual(launch.call_count, 2)

    def test_early_process_failure_is_reported(self):
        with patch('kit.dashboard.runtime.subprocess.Popen', return_value=Mock(pid=1)):
            with self.assertRaises(RuntimeError): self.server.open_configurator()

    def test_architecture_is_escaped_snapshot_and_not_arbitrary_file(self):
        (self.root / 'ARCHITECTURE.md').write_text('<script>window.hacked=1</script>', encoding='utf-8')
        publish_plan(self.root, 'first', 'ARCHITECTURE.md', [{'id': 'fn', 'name': 'hello', 'file': 'app/a.py', 'work_item': 'Hello'}])
        (self.root / 'ARCHITECTURE.md').write_text('new text', encoding='utf-8')
        code, _, body = self.request('/architecture?task=first')
        self.assertEqual(code, 200); self.assertIn('&lt;script&gt;', body); self.assertNotIn('<script>', body)
        self.assertEqual(self.request('/architecture?task=missing')[0], 404)
        self.assertEqual(self.request('/architecture?task=../secret')[0], 400)
        work = json.loads(self.request('/api/task?task=first')[2])['work']
        self.assertTrue(work['architecture']['registered'])
        self.assertEqual(work['progress']['total'], 1)

    def test_corrupt_auxiliary_record_preserves_primary_statistics(self):
        folder = self.metrics.task_dir('first') / 'progress'; folder.mkdir()
        (folder / 'plan.json').write_text('{', encoding='utf-8')
        code, _, body = self.request('/api/task?task=first')
        self.assertEqual(code, 200)
        value = json.loads(body)
        self.assertEqual(value['event_count'], 1)
        self.assertIn('error', value['work'])


if __name__ == '__main__':
    unittest.main()
