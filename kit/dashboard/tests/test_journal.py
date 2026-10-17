"""Tests for kit/dashboard/journal.py. Journals are built in memory or in temporary folders."""
import json
from pathlib import Path
import tempfile
import unittest

from kit.dashboard import journal
from kit.task_metrics import DEFAULT_LIMITS


def ev(kind, at, **data):
    return dict(data, kind=kind, at=at, event_id=data.pop('event_id', f'{kind}-{at}'))


def start(at=100, limits=None, **data):
    return ev("start", at, session="ses_1", title="Task", limits=limits or dict(DEFAULT_LIMITS), **data)


def test_event(at, status='passed', category='passed', scope='full', phase=None, **counts):
    data = dict(status=status, category=category, scope=scope, tests=counts.get('tests', 3),
                failures=counts.get('failures', 0), errors=0, skipped=0, duration_seconds=1.5)
    if phase:
        data['phase'] = phase
    return ev('test', at, **data)


class Step1ParseAndRead(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / 'events.jsonl'

    def write(self, text):
        self.path.write_bytes(text.encode('utf-8'))

    def test_parse_event_checks_shape(self):
        self.assertEqual(journal.parse_event('{"kind": "start", "at": 1}', 1)['kind'], 'start')
        for bad in ('[1]', '{"kind": "start"}', '{"kind": 5, "at": 1}', '{"kind": "x", "at": true}', '{oops'):
            with self.assertRaisesRegex(ValueError, 'line 7'):
                journal.parse_event(bad, 7)

    def test_missing_file_is_empty(self):
        self.assertEqual(journal.read_events(self.path), [])

    def test_blank_lines_and_bom(self):
        self.write('﻿{"kind": "start", "at": 1}\n\n{"kind": "test", "at": 2}\n')
        self.assertEqual([e['kind'] for e in journal.read_events(self.path)], ['start', 'test'])

    def test_half_written_last_line_is_ignored(self):
        self.write('{"kind": "start", "at": 1}\n{"kind": "te')
        self.assertEqual(len(journal.read_events(self.path)), 1)

    def test_bad_line_in_the_middle_raises(self):
        self.write('{"kind": "start", "at": 1}\n{bad\n{"kind": "test", "at": 2}\n')
        with self.assertRaisesRegex(ValueError, 'line 2'):
            journal.read_events(self.path)


class Step1Status(unittest.TestCase):
    def test_statuses(self):
        self.assertEqual(journal.task_status([start()]), journal.RUNNING)
        halted = [start(), ev('halt', 101, reason='r')]
        self.assertEqual(journal.task_status(halted), journal.HALTED)
        self.assertEqual(journal.task_status(halted + [ev('resume', 102, reason='ok')]), journal.RUNNING)
        self.assertEqual(journal.task_status(halted + [ev('finish', 103, ended=103)]), journal.FINISHED)
        with self.assertRaises(ValueError):
            journal.task_status([])


class Step1Tests(unittest.TestCase):
    def test_rows_keep_unknown_counters(self):
        raw = ev('test', 120, status='failed', category='no_result', scope='game', phase='baseline',
                 tests=None, failures=None, errors=None, skipped=None, duration_seconds=2.0)
        rows = journal.test_runs([start(), raw, test_event(130)])
        self.assertEqual(rows[0]['tests'], None)
        self.assertEqual((rows[0]['phase'], rows[0]['scope'], rows[0]['duration']), ('baseline', 'game', 2.0))
        self.assertEqual((rows[1]['phase'], rows[1]['scope']), ('work', 'full'))

    def test_missing_scope_means_full(self):
        raw = ev('test', 120, status='passed', category='passed')
        self.assertEqual(journal.test_runs([start(), raw])[0]['scope'], 'full')

    def test_empty_and_non_test_events_return_empty(self):
        self.assertEqual(journal.test_runs([]), [])
        events = [start(), ev('halt', 110), ev('resume', 120), ev('finish', 130)]
        self.assertEqual(journal.test_runs(events), [])

    def test_rows_have_exact_fields_and_defaults(self):
        raw = ev('test', 110, tests=5, status='passed')
        self.assertEqual(journal.test_runs([start(), raw, ev('finish', 120)]), [{
            'at': 110, 'scope': 'full', 'phase': 'work', 'status': 'passed',
            'category': None, 'tests': 5, 'failures': None, 'errors': None,
            'skipped': None, 'duration': None,
        }])

    def test_preserves_file_order_without_changing_events(self):
        first = ev('test', 130, scope='reader', phase='baseline', duration_seconds=2.5)
        second = ev('test', 120, tests=8)
        events = [start(), first, ev('review', 140, result='accepted'), second]
        original = [dict(event) for event in events]
        rows = journal.test_runs(events)
        self.assertEqual([row['at'] for row in rows], [130, 120])
        self.assertEqual((rows[0]['scope'], rows[0]['phase'], rows[0]['duration']),
                         ('reader', 'baseline', 2.5))
        self.assertEqual(events, original)
        self.assertIsNot(rows[0], first)
        self.assertIsNot(rows[1], second)

    def test_known_zero_counts_stay_zero(self):
        raw = ev('test', 110, tests=0, failures=0, errors=0, skipped=0, duration_seconds=0)
        row = journal.test_runs([raw])[0]
        for field in ('tests', 'failures', 'errors', 'skipped', 'duration'):
            self.assertEqual(row[field], 0)


if __name__ == '__main__':
    unittest.main()
