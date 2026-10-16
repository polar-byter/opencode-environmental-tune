"""Canonical work-item names and compatibility with existing JSONL journals."""
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from task_metrics import (DEFAULT_LIMITS, TaskMetrics, build_parser, limit_breach,
                          main, normalize_work_item)
from kit.dashboard.journal import parse_event, read_events


class WorkItemNames(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.metrics = TaskMetrics(self.root)

    def test_normalization_preserves_input_and_other_fields(self):
        event = {'kind': 'review', 'at': 1, 'piece': 'App', 'result': 'accepted'}
        original = dict(event)
        self.assertEqual(normalize_work_item(event),
                         {'kind': 'review', 'at': 1, 'work_item': 'App', 'result': 'accepted'})
        self.assertEqual(event, original)

    def test_canonical_and_unrelated_events_are_unchanged(self):
        for event in ({'work_item': 'App'}, {'kind': 'start'}, {}):
            self.assertIs(normalize_work_item(event), event)

    def test_equal_names_are_accepted_and_conflicting_names_rejected(self):
        self.assertEqual(normalize_work_item({'work_item': 'App', 'piece': 'App'}),
                         {'work_item': 'App'})
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            normalize_work_item({'work_item': 'App', 'piece': 'Other'})

    def test_new_commands_and_legacy_aliases_share_one_destination(self):
        for command, extra in (
                ('delegate', ['--files', 'app.py', '--requirements', 'requirements.json']),
                ('inspect', []), ('review', ['--result', 'rework'])):
            for option in ('--work-item', '--piece'):
                with self.subTest(command=command, option=option):
                    args = build_parser().parse_args(
                        [command, '--task', 'task', option, 'App', *extra])
                    self.assertEqual(args.work_item, 'App')
                    self.assertFalse(hasattr(args, 'piece'))

    def test_new_events_use_only_the_canonical_field(self):
        self.metrics.start('task')
        (self.root / 'app.py').write_text('value = 1\n', encoding='utf-8')
        attempt = self.metrics.delegate('task', work_item='App', files=['app.py'])
        inspected = self.metrics.inspect('task', work_item='App')
        reviewed = self.metrics.review('task', work_item='App', result='rework')
        for event in (attempt, inspected, reviewed):
            self.assertEqual(event['work_item'], 'App')
            self.assertNotIn('piece', event)
        raw = (self.metrics.task_dir('task') / 'events.jsonl').read_text(encoding='utf-8')
        self.assertNotIn('"piece"', raw)

    def test_legacy_pending_delegation_can_be_inspected_and_reviewed(self):
        self.metrics.start('task')
        (self.root / 'app.py').write_text('value = 1\n', encoding='utf-8')
        attempt = self.metrics.delegate('task', 'App', ['app.py'])
        path = self.metrics.task_dir('task') / 'events.jsonl'
        events = self.metrics.read('task')
        events[-1]['piece'] = events[-1].pop('work_item')
        legacy_text = ''.join(json.dumps(event) + '\n' for event in events)
        path.write_text(legacy_text, encoding='utf-8')
        self.assertEqual(self.metrics.read('task')[-1]['work_item'], 'App')
        self.assertEqual(path.read_text(encoding='utf-8'), legacy_text)
        inspected = self.metrics.inspect('task', 'App')
        reviewed = self.metrics.review('task', 'App', 'rework')
        self.assertEqual(inspected['delegation_id'], attempt['event_id'])
        self.assertEqual(reviewed['delegation_id'], attempt['event_id'])
        self.assertTrue(path.read_text(encoding='utf-8').startswith(legacy_text))
        self.assertTrue(all('piece' not in event for event in self.metrics.read('task')))

    def test_mixed_review_names_still_trigger_the_same_guard(self):
        events = [
            {'kind': 'review', 'at': 1, 'piece': 'App', 'result': 'rework'},
            {'kind': 'review', 'at': 2, 'work_item': 'App', 'result': 'rework'},
            {'kind': 'review', 'at': 3, 'piece': 'App', 'result': 'rework'},
        ]
        self.assertIn('App was sent back 3 times', limit_breach(events, DEFAULT_LIMITS))
        self.assertIn('piece', events[0])

    def test_legacy_failed_reviews_trigger_the_failure_guard(self):
        events = [{'kind': 'review', 'at': index, 'piece': 'App', 'result': 'failed'}
                  for index in range(3)]
        self.assertIn('executor failed 3 times on App', limit_breach(events, DEFAULT_LIMITS))

    def test_conflicting_journal_names_are_rejected_without_rewriting(self):
        self.metrics.start('task')
        path = self.metrics.task_dir('task') / 'events.jsonl'
        with path.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps({'kind': 'review', 'at': 1, 'work_item': 'App',
                                     'piece': 'Other', 'result': 'rework'}) + '\n')
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            self.metrics.read('task')
        self.assertEqual(path.read_bytes(), before)

    def test_legacy_command_writes_a_canonical_event(self):
        self.metrics.start('task')
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            result = main(['--root', str(self.root), 'review', '--task', 'task',
                           '--piece', 'App', '--result', 'rework'])
        self.assertEqual(result, 0)
        event = self.metrics.read('task')[-1]
        self.assertEqual(event['work_item'], 'App')
        self.assertNotIn('piece', event)

    def test_legacy_review_is_reported_and_finished(self):
        self.metrics.start('task')
        self.metrics.append('task', 'review', piece='App', result='rework')
        report = self.metrics.finish('task', language='ru')
        self.assertIn('Возвраты на переделку: **1**', report)

    def test_dashboard_parser_reads_legacy_and_canonical_names(self):
        for field in ('piece', 'work_item'):
            event = parse_event(json.dumps({'kind': 'review', 'at': 1, field: 'App'}), 1)
            self.assertEqual(event, {'kind': 'review', 'at': 1, 'work_item': 'App'})

    def test_dashboard_reader_normalizes_a_mixed_journal_without_rewriting(self):
        path = self.root / 'events.jsonl'
        text = ('{"kind":"start","at":0}\n'
                '{"kind":"delegation","at":1,"piece":"App"}\n'
                '{"kind":"review","at":2,"work_item":"App"}\n')
        path.write_text(text, encoding='utf-8')
        events = read_events(path)
        self.assertEqual([event['work_item'] for event in events[1:]], ['App', 'App'])
        self.assertTrue(all('piece' not in event for event in events))
        self.assertEqual(path.read_text(encoding='utf-8'), text)

    def test_dashboard_parser_rejects_conflicting_names_with_no_json_cause(self):
        with self.assertRaisesRegex(ValueError, 'line 7: Conflicting') as caught:
            parse_event('{"kind":"review","at":1,"work_item":"App","piece":"Other"}', 7)
        self.assertNotIsInstance(caught.exception.__cause__, json.JSONDecodeError)
