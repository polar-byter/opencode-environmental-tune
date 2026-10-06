"""Behavior tests for task metrics. All usage exports are synthetic fixtures."""
import json
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from task_metrics import TaskMetrics


def export(session='s1', parent=None, provider='lmstudio', model='any-new-model',
           tokens=None, created=2000, message='m1'):
    info = {'id': session}
    if parent:
        info['parentID'] = parent
    return {'info': info, 'messages': [{'info': {
        'id': message, 'sessionID': session, 'role': 'assistant',
        'time': {'created': created, 'completed': created + 10},
        'providerID': provider, 'modelID': model,
        'tokens': tokens if tokens is not None else {
            'input': 10, 'output': 5, 'reasoning': 2, 'cache': {'read': 3, 'write': 1}}},
        'parts': []}]}


class MetricsCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.metrics = TaskMetrics(self.root)

    def test_task_path_rejects_escape_and_reserved_names(self):
        for name in ('../other', 'a/b', 'a\\b', '.', 'CON', 'NUL', 'COM1', '', 'x'*81):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.metrics.task_dir(name)

    def test_start_and_duplicate(self):
        self.metrics.start('task', 's1')
        self.assertEqual(self.metrics.read('task')[0]['session'], 's1')
        with self.assertRaises((ValueError, FileExistsError)):
            self.metrics.start('task')

    def test_review_and_idempotent_finish(self):
        self.metrics.start('task')
        self.metrics.review('task', 'piece', 'rework')
        self.metrics.review('task', 'piece', 'accepted')
        report = self.metrics.finish('task')
        self.assertIn('нет данных', report)
        self.assertEqual(self.metrics.finish('task'), report)
        self.assertEqual(sum(e['kind']=='finish' for e in self.metrics.read('task')), 1)
        with self.assertRaises(ValueError):
            self.metrics.review('task', 'piece', 'accepted')

    def test_lock_excludes_second_writer(self):
        self.metrics.start('task')
        with self.metrics.lock('task'):
            with self.assertRaises((ValueError, FileExistsError)):
                self.metrics.review('task', 'x', 'rework')
        self.metrics.review('task', 'x', 'accepted')

    def test_unittest_statuses(self):
        cases = [('Ran 3 tests in 0.1s\n\nOK\n', 0, 'passed'),
                 ('Ran 0 tests in 0.1s\n\nOK\n', 0, 'empty'),
                 ('Ran 3 tests in 0.1s\n\nOK (skipped=1)\n', 0, 'skipped'),
                 ('Ran 3 tests in 0.1s\n\nFAILED (failures=1)\n', 1, 'failed'),
                 ('Ran 1 test in 0.1s\n\nOK (expected failures=1)\n', 0, 'skipped'),
                 ('build successful', 0, 'unknown'),
                 ('Ran 3 tests in 0.1s\n\nOK\n', 1, 'failed')]
        for output, code, expected in cases:
            with self.subTest(expected=expected, output=output):
                self.assertEqual(self.metrics.parse_tests(output, code)['status'], expected)

    def test_junit_counts_leaf_cases_once(self):
        path = self.root/'junit.xml'
        path.write_text('<testsuites tests="2"><testsuite tests="2"><testcase name="a"/><testcase name="b"><skipped/></testcase></testsuite></testsuites>')
        result = self.metrics.parse_tests('', 0, path)
        self.assertEqual(result['tests'], 2)
        self.assertEqual(result['skipped'], 1)
        self.assertNotEqual(result['status'], 'passed')

    def test_real_test_subprocess(self):
        self.metrics.start('task')
        (self.root/'test_ok.py').write_text('import unittest\nclass T(unittest.TestCase):\n def test_ok(self): self.assertEqual(2+2,4)\n')
        event = self.metrics.test('task', [sys.executable, '-m', 'unittest', 'test_ok', '-v'])
        self.assertEqual(event['status'], 'passed')
        self.assertEqual(event['tests'], 1)
        self.assertEqual(self.metrics.read('task')[-1]['kind'], 'test')

    def test_stale_junit_rejected(self):
        self.metrics.start('task')
        (self.root/'old.xml').write_text('<testsuite><testcase/></testsuite>')
        with self.assertRaises(ValueError):
            self.metrics.test('task', [sys.executable, '-c', 'pass'], junit='old.xml')

    def test_timeout_recorded(self):
        self.metrics.start('task')
        result = self.metrics.test('task', [sys.executable, '-c', 'import time; time.sleep(10)'], timeout=0.1)
        self.assertEqual(result['status'], 'timeout')
        self.assertEqual(result['returncode'], 124)

    def test_provider_groups_dedup_and_task_time(self):
        root = export(provider='cloud')
        child = export('s2', 's1')
        unrelated = export('s3')
        old = export(message='old', created=100)
        root['messages'] += old['messages']
        usage = self.metrics.parse_exports([root, child, child, unrelated], 's1', 1, 3)
        rows = {row['group']: row for row in usage['models']}
        self.assertEqual(rows['paid']['input'], 10)
        self.assertEqual(rows['local']['input'], 10)
        self.assertEqual(rows['local']['messages'], 1)
        self.assertNotIn('s3', usage['sessions'])

    def test_missing_usage_not_zero(self):
        usage = self.metrics.parse_exports([export(tokens={})], 's1', 1, 3)
        row = usage['models'][0]
        self.assertIsNone(row['input'])
        self.assertEqual(row['missing_usage'], 1)

    def test_invalid_tokens_and_missing_child_warn(self):
        data = export(tokens={'input': True, 'output': -1})
        data['messages'][0]['parts'] = [{'type':'tool','tool':'subagent','state':{'metadata':{'sessionId':'s2'}}}]
        usage = self.metrics.parse_exports([data], 's1', 1, 3)
        self.assertIsNone(usage['models'][0]['input'])
        self.assertTrue(any('s2' in w for w in usage['warnings']))

    def test_unfinished_message_excluded(self):
        data = export()
        del data['messages'][0]['info']['time']['completed']
        result = self.metrics.parse_exports([data], 's1', 1, 3)
        self.assertEqual(result['models'], [])
        self.assertTrue(result['warnings'])

    def test_conflicting_duplicate_rejected(self):
        with self.assertRaises(ValueError):
            self.metrics.parse_exports([export(), export(tokens={'input': 999,'output':1})], 's1', 1, 3)

    def test_collect_root_and_child_without_model_requests(self):
        root = export()
        root['messages'][0]['parts'] = [{'type':'tool','tool':'subagent','state':{'metadata':{'sessionID':'s2'}}}]
        child = export('s2', 's1')
        def run(args, **kwargs):
            from subprocess import CompletedProcess
            return CompletedProcess(args, 0, json.dumps(root if args[-1]=='s1' else child), '')
        with patch('task_metrics.subprocess.run', side_effect=run):
            self.assertEqual(len(self.metrics.collect_exports('s1')), 2)

    def test_finish_import_and_boundary(self):
        with patch('task_metrics.time.time', return_value=1):
            self.metrics.start('task','s1')
        path = self.root/'export.json'
        path.write_text(json.dumps(export()), encoding='utf-8')
        with patch('task_metrics.time.time', return_value=3):
            report = self.metrics.finish('task',[str(path)])
        self.assertIn('any-new-model', report)
        self.assertEqual(self.metrics.read('task')[-1]['usage']['models'][0]['input'],10)

    def test_no_cli_report_still_has_reviews(self):
        self.metrics.start('task','s1')
        self.metrics.review('task','x','rework')
        with patch.object(self.metrics,'collect_exports',side_effect=ValueError('CLI unavailable')):
            report=self.metrics.finish('task')
        self.assertIn('CLI unavailable',report)
        self.assertIn('нет данных',report)

    def test_v2_021_direct_messages(self):
        data = export()
        info = data['messages'][0]['info']
        info['type'] = info.pop('role')
        info['model'] = {'providerID': info.pop('providerID'), 'id': info.pop('modelID')}
        info['content'] = [{'type': 'text', 'text': 'not stored'}]
        data['messages'] = [info]
        result = self.metrics.parse_exports([data], 's1', 1, 3)
        self.assertEqual(result['models'][0]['input'], 10)
        self.assertEqual(result['models'][0]['group'], 'local')
        self.assertNotIn('not stored', json.dumps(result))

    def test_created_in_scope_but_completed_after_cutoff(self):
        data = export()
        data['messages'][0]['info']['time']['completed'] = 4000
        self.assertEqual(self.metrics.parse_exports([data], 's1', 1, 3)['models'], [])

    def test_missing_usage_poison_only_affected_counter(self):
        data = export()
        data['messages'] += export(message='m2', tokens={'output': 7})['messages']
        row = self.metrics.parse_exports([data], 's1', 1, 3)['models'][0]
        self.assertIsNone(row['input'])
        self.assertEqual(row['output'], 12)

    def test_collect_api_pagination_and_descendants(self):
        def fetch(executable, args):
            if args[:2] == ['session', 'export']:
                sid = args[-1]
                return export(sid, 's1' if sid != 's1' else None)
            parent = next(a for a in args if a.startswith('parentID=')).split('=',1)[1]
            if parent != 's1':
                return {'data': [], 'cursor': {'next': None}}
            if 'cursor=next-page' in args:
                return {'data': [{'id':'s3','parentID':'s1'}], 'cursor': {'next':None}}
            return {'data': [{'id':'s2','parentID':'s1'}], 'cursor': {'next':'next-page'}}
        with patch.object(self.metrics, 'cli_json', side_effect=fetch):
            result = self.metrics.collect_exports('s1', 'fake-cli')
        self.assertEqual({e['info']['id'] for e in result}, {'s1','s2','s3'})

    def test_collect_keeps_children_when_later_page_fails(self):
        for error in (ValueError('bad page'), OSError('offline'), subprocess.TimeoutExpired('cli', 30)):
            with self.subTest(error=type(error).__name__):
                def fetch(executable, args):
                    if args[:2] == ['session', 'export']:
                        sid = args[-1]
                        return export(sid, 's1' if sid != 's1' else None)
                    if 'parentID=s2' in args:
                        return {'data': [], 'cursor': {'next': None}}
                    if 'cursor=next-page' in args:
                        raise error
                    return {'data': [{'id': 's2', 'parentID': 's1'}], 'cursor': {'next': 'next-page'}}
                with patch.object(self.metrics, 'cli_json', side_effect=fetch):
                    result = self.metrics.collect_exports('s1', 'fake-cli')
                self.assertEqual({item['info']['id'] for item in result}, {'s1', 's2'})
                self.assertIn(str(error), result[0]['_metrics_warnings'][0])
                usage = self.metrics.parse_exports(result, 's1', 1, 3)
                self.assertEqual(usage['models'][0]['input'], 20)

    def test_multiple_test_summaries_not_accepted(self):
        output = 'Ran 1 test in 0.1s\nFAILED (errors=1)\nRan 1 test in 0.1s\nOK\n'
        self.assertEqual(self.metrics.parse_tests(output,0)['status'], 'unknown')

    def test_missing_executable_is_recorded(self):
        self.metrics.start('task')
        result = self.metrics.test('task', [str(self.root/'missing-command')])
        self.assertEqual(result['returncode'], 127)
        self.assertEqual(result['status'], 'failed')

    def test_bad_json_report_not_successful(self):
        self.metrics.start('task','s1')
        (self.root/'bad.json').write_text('not json')
        result = self.metrics.finish('task',['bad.json'])
        self.assertIn('нет данных',result)
        self.assertEqual(self.metrics.read('task')[-1]['usage']['models'], [])

    def test_unknown_provider_separate(self):
        data=export(provider=None)
        result=self.metrics.parse_exports([data],'s1',1,3)
        self.assertEqual(result['models'][0]['group'],'unknown')

    def test_report_counts_only_full_passes(self):
        start = self.metrics.start('task')
        with self.metrics.lock('task'):
            for status in ('passed','skipped','empty','failed','unknown','passed'):
                self.metrics.append('task','test',status=status,tests=2,failures=0,errors=0,skipped=0)
        self.metrics.review('task','x','rework')
        self.metrics.review('task','x','rework')
        self.metrics.review('task','x','accepted')
        report=self.metrics.finish('task')
        self.assertIn('**2 из 6**',report)
        self.assertIn('переделку: **2**',report)

    def test_finish_recreates_missing_report(self):
        self.metrics.start('task')
        report=self.metrics.finish('task')
        (self.metrics.task_dir('task')/'report.md').unlink()
        self.assertEqual(self.metrics.finish('task'),report)

    def test_missing_junit_report_is_unknown(self):
        result=self.metrics.parse_tests('',0,self.root/'absent.xml')
        self.assertEqual(result['status'],'unknown')


if __name__ == '__main__':
    unittest.main()
