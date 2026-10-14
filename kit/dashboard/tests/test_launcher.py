"""Identity, lifecycle, CLI integration and concurrent real process launches."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch
import urllib.request
import webbrowser

from kit.dashboard import launcher
from kit.task_metrics import TaskMetrics, main


class LauncherUnit(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        TaskMetrics(self.root).start('task')
        self.state = {'service': launcher.SERVICE, 'version': launcher.VERSION,
                      'instance_id': 'a' * 32, 'pid': 123, 'project_root': str(self.root.resolve()),
                      'base_url': 'http://127.0.0.1:12345', 'control_token': 'token'}

    def test_remote_or_malformed_addresses_are_not_probed(self):
        for url in ('https://127.0.0.1:1234', 'http://example.com:1234', 'http://user@127.0.0.1:1',
                    'http://127.0.0.1:99999', 'http://127.0.0.1:1/path', None):
            with patch.object(launcher, 'local_request') as request:
                self.assertIsNone(launcher.health(self.root, dict(self.state, base_url=url)))
                request.assert_not_called()

    def test_wrong_instance_and_project_are_not_reused(self):
        response = Mock()
        response.__enter__ = Mock(return_value=io.StringIO(json.dumps(dict(self.state, instance_id='b' * 32))))
        response.__exit__ = Mock(return_value=False)
        with patch.object(launcher, 'local_request', return_value=response):
            self.assertIsNone(launcher.health(self.root, self.state))
        with patch.object(launcher, 'local_request') as request:
            self.assertIsNone(launcher.health(self.root, dict(self.state, project_root='another project')))
            request.assert_not_called()

    def test_registered_task_reuses_server_and_opens_its_own_url(self):
        launcher.write_state(self.root, self.state)
        with patch.object(launcher, 'health', return_value=self.state), \
                patch.object(launcher, 'start_process') as spawn, \
                patch.object(launcher.webbrowser, 'open', return_value=True) as browser:
            result = launcher.ensure_dashboard(self.root, 'task')
        self.assertFalse(result['started'])
        self.assertTrue(result['opened'])
        self.assertIn('task=task', result['url'])
        spawn.assert_not_called()
        browser.assert_called_once_with(result['url'], new=0)

    def test_missing_task_never_starts_a_process(self):
        with patch.object(launcher, 'start_process') as spawn:
            with self.assertRaises(ValueError):
                launcher.ensure_dashboard(self.root, 'missing')
            spawn.assert_not_called()

    def test_browser_failure_keeps_ready_server_and_returns_address(self):
        launcher.write_state(self.root, self.state)
        with patch.object(launcher, 'health', return_value=self.state), \
                patch.object(launcher.webbrowser, 'open', side_effect=webbrowser.Error('No browser')):
            result = launcher.ensure_dashboard(self.root, 'task')
        self.assertEqual(result['status'], 'ready')
        self.assertFalse(result['opened'])
        self.assertEqual(result['browser_error'], 'No browser')

    def test_start_timeout_terminates_only_the_new_child(self):
        process = Mock(pid=999)
        process.poll.return_value = None
        with patch.object(launcher, 'start_process', return_value=process), \
                patch.object(launcher, 'health', return_value=None):
            with self.assertRaises(TimeoutError):
                launcher.ensure_dashboard(self.root, 'task', open_browser=False, timeout=0.01)
        process.terminate.assert_called_once()
        process.wait.assert_called_once_with(timeout=5)

    def test_exited_child_reports_log_without_killing_anything(self):
        process = Mock(pid=999)
        process.poll.return_value = 1
        with patch.object(launcher, 'start_process', return_value=process):
            with self.assertRaisesRegex(RuntimeError, 'server.log'):
                launcher.ensure_dashboard(self.root, 'task', open_browser=False)
        process.terminate.assert_not_called()

    def test_project_lock_serializes_launches(self):
        failures = []
        def contend():
            try:
                with launcher.launch_lock(self.root, 0.05):
                    failures.append('unexpected access')
            except TimeoutError:
                failures.append('timeout')
        with launcher.launch_lock(self.root, 1):
            thread = threading.Thread(target=contend)
            thread.start()
            thread.join(timeout=2)
        self.assertEqual(failures, ['timeout'])
        with launcher.launch_lock(self.root, 1):
            pass


class MetricsDashboardCLI(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'kit').mkdir()
        (self.root / 'opencode.jsonc').write_text('{}', encoding='utf-8')

    def call(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err), patch.dict(os.environ, {'OPENCODE_KIT_DASHBOARD': 'auto'}):
            code = main(['--root', str(self.root), *args])
        return code, out.getvalue(), err.getvalue()

    def test_start_launches_after_journal_is_saved_and_keeps_json_output(self):
        def launch(root, task, open_browser):
            self.assertTrue((root / '.metrics' / task / 'events.jsonl').exists())
            self.assertFalse(open_browser)
            return {'status': 'ready', 'url': 'http://127.0.0.1:1/?task=task', 'opened': False}
        with patch('kit.task_metrics.launch_task_dashboard', side_effect=launch) as start:
            code, text, _ = self.call('start', '--task', 'task', '--no-browser')
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(text)['dashboard']['status'], 'ready')
        start.assert_called_once()
        self.assertNotIn('dashboard', TaskMetrics(self.root).read('task')[0])

    def test_launch_failure_does_not_destroy_or_reregister_task(self):
        with patch('kit.task_metrics.launch_task_dashboard', side_effect=TimeoutError('not ready')):
            code, text, error = self.call('start', '--task', 'task')
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(text)['dashboard']['status'], 'unavailable')
        self.assertIn('journal was saved', error)
        self.assertEqual(len(TaskMetrics(self.root).read('task')), 1)

    def test_disable_option_and_library_start_have_no_external_effects(self):
        with patch('kit.task_metrics.launch_task_dashboard') as launch:
            self.assertEqual(self.call('start', '--task', 'task', '--no-dashboard')[0], 0)
            TaskMetrics(self.root).start('library')
            launch.assert_not_called()

    def test_finish_does_not_launch_or_open_dashboard(self):
        TaskMetrics(self.root).start('task')
        with patch('kit.task_metrics.launch_task_dashboard') as launch:
            self.assertEqual(self.call('finish', '--task', 'task')[0], 0)
            launch.assert_not_called()


class RuntimeProcess(unittest.TestCase):
    """Use a copied kit in a real project to prove survival after CLI exit."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dashboard project ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = Path(__file__).resolve().parents[2]
        shutil.copytree(source, self.root / 'kit', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        (self.root / 'opencode.jsonc').write_text('{}', encoding='utf-8')
        self.addCleanup(lambda: launcher.stop_dashboard(self.root))

    def start_cli(self, task):
        env = dict(os.environ, OPENCODE_KIT_DASHBOARD='auto')
        result = subprocess.run([sys.executable, '-u', str(self.root / 'kit' / 'task_metrics.py'),
                                 'start', '--task', task, '--title', task, '--no-browser'],
                                cwd=self.root, env=env, capture_output=True, text=True, encoding='utf-8', timeout=25)
        self.assertEqual(result.returncode, 0, result.stderr)
        event = json.loads(result.stdout)
        self.assertEqual(event['dashboard']['status'], 'ready', result.stderr)
        return event['dashboard']

    def test_cli_exit_preserves_server_and_next_task_reuses_it(self):
        first = self.start_cli('first')
        second = self.start_cli('second')
        self.assertEqual(first['pid'], second['pid'])
        self.assertTrue(first['started'])
        self.assertFalse(second['started'])
        for task, result in [('first', first), ('second', second)]:
            url = result['url'].split('/?')[0] + '/api/task?task=' + task
            with urllib.request.urlopen(url, timeout=2) as response:
                self.assertEqual(json.load(response)['task'], task)

    def test_concurrent_task_starts_share_one_server(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(self.start_cli, ['first', 'second']))
        self.assertEqual(results[0]['pid'], results[1]['pid'])
        self.assertEqual(sum(item['started'] for item in results), 1)

    def test_controlled_stop_and_restart_create_new_instance(self):
        first = self.start_cli('first')
        self.assertTrue(launcher.stop_dashboard(self.root))
        second = self.start_cli('second')
        self.assertNotEqual(first['instance_id'], second['instance_id'])
        self.assertTrue(second['started'])


if __name__ == '__main__':
    unittest.main()
