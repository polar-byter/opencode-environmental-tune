"""Function progress has explicit provenance and never guesses a total."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from kit.dashboard import tracking as t
from kit.task_metrics import TaskMetrics


class Tracking(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.metrics = TaskMetrics(self.root)
        self.metrics.start('task')
        (self.root / 'ARCHITECTURE.md').write_text('# Architecture <script>alert(1)</script>', encoding='utf-8')
        self.rows = [{'id': str(i), 'name': 'function' + str(i), 'file': 'app/code.py', 'work_item': 'Rules'} for i in range(3)]
        self.events = [{'kind': 'start', 'at': 100}, {'kind': 'delegation', 'at': 110, 'event_id': 'attempt', 'work_item': 'Rules', 'scope': 'rules', 'files': ['app/code.py']}]

    def publish(self):
        with patch.object(t.time, 'time', return_value=105):
            return t.publish_plan(self.root, 'task', 'ARCHITECTURE.md', self.rows)

    def report(self, **kwargs):
        data = dict(delegation_id='attempt', implemented_ids=['0', '1'], current_id='2', updated_at=115)
        data.update(kwargs)
        t.atomic_json(t.progress_folder(self.root, 'task') / 'attempt.json', data)

    def test_unknown_total_and_legacy_document_are_explicit(self):
        progress = t.function_progress(self.root, 'task', self.events)
        self.assertIsNone(progress['total'])
        self.assertFalse(progress['available'])
        self.assertFalse(t.architecture(self.root, 'task')['registered'])
        self.assertIsNone(t.architecture(self.root, 'task')['at'])

    def test_published_document_is_snapshot_and_revision_keeps_registration(self):
        first = self.publish()
        (self.root / 'ARCHITECTURE.md').write_text('changed', encoding='utf-8')
        self.assertIn('# Architecture', t.architecture(self.root, 'task')['text'])
        second = t.publish_plan(self.root, 'task', 'ARCHITECTURE.md', self.rows)
        self.assertEqual(second['revision'], 2)
        self.assertEqual(first['functions'][0]['registered_at'], second['functions'][0]['registered_at'])

    def test_reported_implementation_is_separate_from_acceptance(self):
        self.publish(); self.report()
        p = t.function_progress(self.root, 'task', self.events, now=120)
        self.assertEqual((p['implemented'], p['total'], p['accepted']), (2, 3, 0))
        self.assertEqual(p['current']['name'], 'function2')
        self.events.extend([{'kind': 'inspection', 'at': 125, 'delegation_id': 'attempt'}, {'kind': 'review', 'at': 130, 'delegation_id': 'attempt', 'result': 'accepted'}])
        p = t.function_progress(self.root, 'task', self.events, now=131)
        self.assertEqual((p['implemented'], p['accepted']), (3, 3))
        self.assertIsNone(p['current'])

    def test_stale_future_finished_and_inspected_current_are_not_live(self):
        self.publish(); self.report()
        for now in (300, 110):
            self.assertIsNone(t.function_progress(self.root, 'task', self.events, now=now)['current'])
        for event in ({'kind': 'finish', 'at': 121}, {'kind': 'inspection', 'at': 121, 'delegation_id': 'attempt'}):
            self.assertIsNone(t.function_progress(self.root, 'task', self.events + [event], now=122)['current'])

    def test_partial_wrong_attempt_and_foreign_function_reports_are_ignored(self):
        self.publish()
        path = t.progress_folder(self.root, 'task') / 'attempt.json'
        path.write_text('{', encoding='utf-8')
        self.assertEqual(t.function_progress(self.root, 'task', self.events)['implemented'], 0)
        for extra in ({'delegation_id': 'other'}, {'implemented_ids': ['foreign']}, {'implemented_ids': '0'}):
            self.report(**extra)
            self.assertEqual(t.function_progress(self.root, 'task', self.events)['implemented'], 0)

    def test_rework_preserves_attempt_history_and_clears_previous_completion(self):
        self.publish(); self.report()
        events = self.events + [{'kind': 'review', 'at': 125, 'delegation_id': 'attempt', 'result': 'rework'}, dict(self.events[1], event_id='retry', at=130)]
        self.assertEqual(len(t.work_items(events)[0]['attempts']), 2)
        self.assertEqual(t.function_progress(self.root, 'task', events)['implemented'], 0)

    def test_old_acceptance_does_not_accept_newly_registered_functions(self):
        self.publish()
        events = self.events + [{'kind': 'review', 'at': 104, 'delegation_id': 'attempt', 'result': 'accepted'}]
        self.assertEqual(t.function_progress(self.root, 'task', events)['accepted'], 0)

    def test_manifest_and_document_boundaries(self):
        for name in ('../secret.md', '.opencode/key.md', 'node_modules/a.md'):
            with self.assertRaises(ValueError): t.project_file(self.root, name, must_exist=False)
        with self.assertRaises(ValueError): t.validate_functions(self.root, self.rows + [self.rows[0]])
        self.publish()
        changed = [dict(row) for row in self.rows]; changed[0]['name'] = 'renamed'
        with self.assertRaises(ValueError): t.publish_plan(self.root, 'task', 'ARCHITECTURE.md', changed)

    def test_pending_executor_prevents_plan_changes(self):
        self.publish()
        self.metrics.append('task', 'delegation', event_id='pending', work_item='Rules', scope='rules', files=['app/code.py'])
        with self.assertRaises(ValueError): t.publish_plan(self.root, 'task', 'ARCHITECTURE.md', self.rows)


if __name__ == '__main__':
    unittest.main()
