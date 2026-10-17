"""Behavior tests for delegation evidence, file boundaries and scoped loop guards."""
import json
import io
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import time
from task_metrics import TaskHalted, TaskMetrics, main
from delegation_guard import read_requirements, review_checks, take_project_snapshot


class EvidenceFilesWithBom(unittest.TestCase):
    """PowerShell writes UTF-8 with a BOM by default; both evidence readers accept it."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def write_bom(self, name, data):
        path = self.root / name
        path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8-sig')
        self.assertTrue(path.read_bytes().startswith(b'\xef\xbb\xbf'))
        return path

    def test_requirements_with_bom(self):
        path = self.write_bom('req.json', ['Ход в занятую клетку отклоняется'])
        self.assertEqual(read_requirements(path), ['Ход в занятую клетку отклоняется'])

    def test_checks_with_bom(self):
        check = {'requirement': 'r', 'code': 'c', 'test': 't', 'verified': True}
        self.assertEqual(review_checks(self.write_bom('checks.json', [check])), [check])


class PipelineControls(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.metrics = TaskMetrics(self.root)
        self.metrics.start('task', limits={'max_failed_runs': 2})
        (self.root / 'app.py').write_text('value = 1\n')
        (self.root / 'test_ok.py').write_text('import unittest\nclass T(unittest.TestCase):\n def test_ok(self): pass\n')
        self.command = [sys.executable, '-m', 'unittest', 'test_ok']
        self.checks = Path('.metrics/task/checks.json')
        (self.root / self.checks).write_text(json.dumps([
            {'requirement': 'value is two', 'code': 'app.py:value',
             'test': 'test_ok.T.test_ok', 'verified': True}]))

    def begin(self):
        return self.metrics.delegate('task', 'App', ['app.py'])

    def test_failed_attempt_without_changes_is_not_a_rework(self):
        self.begin()
        self.metrics.inspect('task', 'App')
        event = self.metrics.review('task', 'App', 'failed')
        self.assertEqual((event['result'], event['changed']), ('failed', []))
        report = self.metrics.render('task', self.metrics.read('task'), {'models': [], 'warnings': []}, time.time())
        self.assertIn('Возвраты на переделку: **0**', report)
        self.assertIn('Сбои исполнителя без результата', report)

    def test_failed_is_refused_when_the_executor_changed_files(self):
        self.begin()
        (self.root / 'app.py').write_text('value = 2\n')
        self.metrics.inspect('task', 'App')
        with self.assertRaisesRegex(ValueError, 'not failed: app.py'):
            self.metrics.review('task', 'App', 'failed')
        self.metrics.review('task', 'App', 'rework')

    def test_repeated_executor_failures_stop_the_task(self):
        for attempt in range(3):
            self.begin()
            event = self.metrics.review('task', 'App', 'failed')
        self.assertIn('executor failed 3 times on App', event['halt'])
        with self.assertRaises(TaskHalted):
            self.begin()

    def test_new_file_outside_scope_is_detected_without_git(self):
        self.begin()
        (self.root / 'surprise.py').write_text('value = 2')
        self.metrics.test('task', self.command, scope='App')
        with self.assertRaisesRegex(ValueError, 'unexpected files: surprise.py'):
            self.metrics.review('task', 'App', 'accepted', self.checks)
        event = self.metrics.review('task', 'App', 'rework')
        self.assertEqual(event['unexpected'], ['surprise.py'])

    def test_modified_and_deleted_other_files_are_detected(self):
        for action in ('modify', 'delete'):
            with self.subTest(action=action):
                (self.root / 'test_ok.py').write_text('original')
                self.begin()
                if action == 'modify':
                    (self.root / 'test_ok.py').write_text('changed')
                else:
                    (self.root / 'test_ok.py').unlink()
                event = self.metrics.review('task', 'App', 'rework')
                self.assertEqual(event['unexpected'], ['test_ok.py'])

    def test_gitignored_source_files_are_not_hidden(self):
        (self.root / '.gitignore').write_text('secret-test.py\n')
        self.begin()
        (self.root / 'secret-test.py').write_text('changed')
        event = self.metrics.review('task', 'App', 'rework')
        self.assertIn('secret-test.py', event['unexpected'])

    def test_green_tests_and_requirement_evidence_are_required(self):
        attempt = self.begin()
        (self.root / 'app.py').write_text('value = 2\n')
        with self.assertRaisesRegex(ValueError, '--checks'):
            self.metrics.review('task', 'App', 'accepted')
        with self.assertRaisesRegex(ValueError, 'green test run'):
            self.metrics.review('task', 'App', 'accepted', self.checks)
        self.metrics.test('task', self.command, scope='Other')
        with self.assertRaisesRegex(ValueError, 'green test run'):
            self.metrics.review('task', 'App', 'accepted', self.checks)
        self.metrics.test('task', self.command, scope='App')
        review = self.metrics.review('task', 'App', 'accepted', self.checks)
        self.assertEqual(review['delegation_id'], attempt['event_id'])
        self.assertEqual(review['changed'], ['app.py'])
        self.assertEqual(len(review['checks']), 1)

    def test_unverified_check_is_rejected(self):
        self.begin()
        self.metrics.test('task', self.command, scope='App')
        (self.root / self.checks).write_text('[{"requirement":"x","code":"x","test":"x","verified":false}]')
        with self.assertRaisesRegex(ValueError, 'verified=true'):
            self.metrics.review('task', 'App', 'accepted', self.checks)

    def test_review_cannot_drop_a_requirement_from_the_original_spec(self):
        path = self.root / '.metrics/task/requirements.json'
        path.write_text('["null checked before map access", "unknown ID rejected"]')
        self.metrics.delegate('task', 'App', ['app.py'], requirements=path)
        self.metrics.test('task', self.command, scope='App')
        (self.root / self.checks).write_text(json.dumps([
            {'requirement': 'unknown ID rejected', 'code': 'app.py', 'test': 'test_unknown', 'verified': True}]))
        with self.assertRaisesRegex(ValueError, 'every frozen requirement'):
            self.metrics.review('task', 'App', 'accepted', self.checks)

    def test_tracked_tasks_cannot_record_reviews_without_a_delegation(self):
        self.metrics.start('tracked', track_delegations=True)
        with self.assertRaisesRegex(ValueError, 'Register the executor'):
            self.metrics.review('tracked', 'App', 'accepted')
        with self.assertRaisesRegex(ValueError, 'requirements file'):
            self.metrics.delegate('tracked', 'App', ['app.py'])

    def test_inspection_separates_executor_edits_from_new_reviewer_tests(self):
        self.begin()
        (self.root / 'app.py').write_text('value = 2')
        self.metrics.inspect('task', 'App')
        (self.root / 'additional_test.py').write_text('reviewer test')
        self.metrics.test('task', self.command, scope='App')
        event = self.metrics.review('task', 'App', 'accepted', self.checks)
        self.assertEqual(event['changed'], ['app.py'])
        self.assertEqual(event['reviewer_changes'], ['additional_test.py'])

    def test_inspection_cannot_be_overwritten_to_hide_unexpected_edits(self):
        self.begin()
        (self.root / 'surprise.py').write_text('bad edit')
        self.metrics.inspect('task', 'App')
        (self.root / 'surprise.py').unlink()
        with self.assertRaisesRegex(ValueError, 'already inspected'):
            self.metrics.inspect('task', 'App')
        self.metrics.test('task', self.command, scope='App')
        with self.assertRaisesRegex(ValueError, 'unexpected files'):
            self.metrics.review('task', 'App', 'accepted', self.checks)

    def test_source_cannot_change_after_inspection_and_still_be_accepted(self):
        self.begin()
        self.metrics.inspect('task', 'App')
        (self.root / 'app.py').write_text('Master Chief implementation')
        self.metrics.test('task', self.command, scope='App')
        with self.assertRaisesRegex(ValueError, 'source changed after inspection'):
            self.metrics.review('task', 'App', 'accepted', self.checks)

    def test_new_reviewer_test_after_green_requires_another_run(self):
        self.begin()
        self.metrics.inspect('task', 'App')
        self.metrics.test('task', self.command, scope='App')
        (self.root / 'new_test.py').write_text('reviewer test added after green')
        with self.assertRaisesRegex(ValueError, 'changed since the green test'):
            self.metrics.review('task', 'App', 'accepted', self.checks)
        self.metrics.test('task', self.command, scope='App')
        self.metrics.review('task', 'App', 'accepted', self.checks)

    def test_test_command_cannot_mutate_source_and_still_prove_acceptance(self):
        self.begin()
        self.metrics.inspect('task', 'App')
        def execute(*args):
            (self.root / 'test_ok.py').write_text('changed by test command')
            return '', 0, dict(status='passed', tests=1, failures=0, errors=0, skipped=0), 'passed'
        with patch.object(self.metrics, 'execute', side_effect=execute):
            self.metrics.test('task', self.command, scope='App')
        with self.assertRaisesRegex(ValueError, 'changed since the green test'):
            self.metrics.review('task', 'App', 'accepted', self.checks)

    def test_attempt_is_limited_to_one_file(self):
        with self.assertRaisesRegex(ValueError, 'exactly one source file'):
            self.metrics.delegate('task', 'App', ['app.py', 'test_ok.py'])

    def test_cli_tracked_delegation_review_full_test_and_finish(self):
        def cli(*args):
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                return main(['--root', str(self.root), *args])
        self.assertEqual(cli('start', '--task', 'cli', '--track-delegations'), 0)
        folder = self.root / '.metrics/cli'
        (folder / 'requirements.json').write_text('["value is two"]')
        (folder / 'checks.json').write_text((self.root / self.checks).read_text())
        (self.root / 'test_ok.py').write_text(
            'import unittest, app\nclass T(unittest.TestCase):\n def test_ok(self): self.assertEqual(app.value, 2)\n')
        self.assertEqual(cli('delegate', '--task', 'cli', '--work-item', 'App', '--files', 'app.py',
                             '--requirements', '.metrics/cli/requirements.json'), 0)
        (self.root / 'app.py').write_text('value = 2\n')
        self.assertEqual(cli('inspect', '--task', 'cli', '--work-item', 'App'), 0)
        self.assertEqual(cli('test', '--task', 'cli', '--scope', 'App', '--', *self.command), 0)
        self.assertEqual(cli('review', '--task', 'cli', '--work-item', 'App', '--result', 'accepted',
                             '--checks', '.metrics/cli/checks.json'), 0)
        self.assertEqual(cli('test', '--task', 'cli', '--scope', 'full', '--', *self.command), 0)
        self.assertEqual(cli('finish', '--task', 'cli', '--language', 'ru'), 2)  # UI/UX stage missing
        self.assertEqual(cli('ux-review', '--task', 'cli', '--not-applicable', 'у модуля нет интерфейса'), 0)
        self.assertEqual(cli('finish', '--task', 'cli', '--language', 'ru'), 0)
        report = (folder / 'report.md').read_text(encoding='utf-8')
        self.assertIn('Этап улучшения UI/UX не требуется: у модуля нет интерфейса.', report)
        self.assertIn('без записанного ревью: **0**', report)
        self.assertIn('Полный набор тестов: **1 из 1**', report)

    def test_cli_inspect_returns_failure_for_unexpected_edits(self):
        self.begin()
        (self.root / 'unexpected.txt').write_text('executor change')
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            result = main(['--root', str(self.root), 'inspect', '--task', 'task', '--work-item', 'App'])
        self.assertEqual(result, 1)

    def test_pending_attempt_prevents_new_delegation_and_is_reported(self):
        self.begin()
        with self.assertRaisesRegex(ValueError, 'pending delegation'):
            self.begin()
        with self.assertRaisesRegex(ValueError, 'match'):
            self.metrics.review('task', 'Other', 'rework')
        report = self.metrics.finish('task', language='ru')
        self.assertIn('без записанного ревью: **1**', report)
        self.assertIn('Не завершено ревью: App', report)

    def test_scoped_green_is_not_full_project_success(self):
        self.metrics.test('task', self.command, scope='App')
        report = self.metrics.finish('task', language='ru')
        self.assertIn('Полный набор тестов: **0 из 0**', report)
        self.assertIn('готовность всей задачи не подтверждена', report)

    def test_green_baseline_is_not_a_successful_implementation_run(self):
        self.metrics.test('task', self.command, scope='App', phase='baseline')
        report = self.metrics.finish('task', language='ru')
        self.assertIn('Полностью успешные прогоны: **0 из 0**', report)
        self.assertIn('Начальные проверки до реализации (baseline): **1**', report)

    def test_generated_reports_do_not_look_like_executor_edits(self):
        self.begin()
        target = self.root / 'target' / 'surefire-reports'
        target.mkdir(parents=True)
        (target / 'TEST-App.xml').write_text('<testsuite/>')
        self.metrics.test('task', self.command, scope='App')
        event = self.metrics.review('task', 'App', 'accepted', self.checks)
        self.assertEqual(event['unexpected'], [])

    def test_source_paths_cannot_escape_or_name_generated_files(self):
        for path in ('../app.py', '.metrics/task/checks.json', str(self.root / 'app.py')):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.metrics.delegate('task', 'App', [path])
        if sys.platform == 'win32':
            for path in ('C:app.py', '\\app.py'):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    self.metrics.delegate('task', 'App', [path])

    def failing_run(self, scope, phase='work'):
        parsed = dict(status='failed', tests=1, failures=1, errors=0, skipped=0)
        with patch.object(self.metrics, 'execute', return_value=('', 1, parsed, 'tests_failed')):
            return self.metrics.test('task', ['fake'], scope=scope, phase=phase)

    def test_initial_red_baseline_does_not_use_failed_budget(self):
        self.failing_run('App', 'baseline')
        self.assertNotIn('halt', self.failing_run('App'))
        self.assertIn('halt', self.failing_run('App'))

    def test_unrelated_module_failure_does_not_accumulate(self):
        self.assertNotIn('halt', self.failing_run('App'))
        self.assertNotIn('halt', self.failing_run('Other'))
        self.assertIn('halt', self.failing_run('App'))

    def test_full_green_resets_each_scope_failed_budget(self):
        self.failing_run('App')
        self.metrics.test('task', self.command)
        self.assertNotIn('halt', self.failing_run('App'))

    def test_baseline_cannot_hide_failures_after_work_has_started(self):
        self.failing_run('App')
        with self.assertRaisesRegex(ValueError, 'Baseline'):
            self.failing_run('App', 'baseline')

    def test_repeated_baseline_is_rejected(self):
        self.failing_run('App', 'baseline')
        with self.assertRaisesRegex(ValueError, 'Baseline'):
            self.failing_run('App', 'baseline')

    def test_baseline_build_failure_still_counts_as_no_result(self):
        # Expected red tests do not excuse broken builds or an unreadable test runner.
        parsed = dict(status='failed', tests=None, failures=None, errors=None, skipped=None)
        with patch.object(self.metrics, 'execute', return_value=('', 1, parsed, 'no_result')):
            for scope in ('A', 'B', 'C'):
                event = self.metrics.test('task', ['fake'], scope=scope, phase='baseline')
        self.assertIn('no readable result', event['halt'])


if __name__ == '__main__':
    unittest.main()
