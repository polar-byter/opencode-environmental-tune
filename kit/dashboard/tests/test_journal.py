"""Tests for kit/dashboard/journal.py. Journals are built in memory or in temporary folders."""
import json
from pathlib import Path
import tempfile
import unittest

from kit.dashboard import journal
from kit.task_metrics import DEFAULT_LIMITS, limit_breach


def ev(kind, at, **data):
    return dict(data, kind=kind, at=at, event_id=data.pop('event_id', f'{kind}-{at}'))


def start(at=100, limits=None, **data):
    return ev("start", at, session="ses_1", title="Task", limits=limits or dict(DEFAULT_LIMITS), **data)


def delegation(work_item, at, eid):
    return ev('delegation', at, work_item=work_item, files=[f'{work_item}.py'], scope=work_item, event_id=eid)


def inspection(work_item, at, eid, unexpected=()):
    return ev('inspection', at, work_item=work_item, delegation_id=eid, changed=[f'{work_item}.py'],
              unexpected=list(unexpected))


def review(work_item, at, eid, result='accepted', unexpected=()):
    return ev('review', at, work_item=work_item, delegation_id=eid, result=result, unexpected=list(unexpected))


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


class Step1Tail(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / 'events.jsonl'
        self.tail = journal.JournalTail(self.path)

    def append(self, text):
        with self.path.open('ab') as handle:
            handle.write(text.encode('utf-8'))

    def test_missing_file(self):
        self.assertEqual(self.tail.new_events(), [])

    def test_only_new_events_and_partial_line_waits(self):
        self.append('{"kind": "start", "at": 1}\n{"kind": "te')
        self.assertEqual([e['kind'] for e in self.tail.new_events()], ['start'])
        self.append('st", "at": 2}\n')
        self.assertEqual([e['at'] for e in self.tail.new_events()], [2])
        self.assertEqual(self.tail.new_events(), [])
        self.assertFalse(self.tail.reset)

    def test_recreated_file_restarts(self):
        self.append('{"kind": "start", "at": 1}\n{"kind": "test", "at": 2}\n')
        self.tail.new_events()
        self.path.write_bytes(b'{"kind": "start", "at": 9}\n')
        self.assertEqual([e['at'] for e in self.tail.new_events()], [9])
        self.assertTrue(self.tail.reset)
        self.tail.new_events()
        self.assertFalse(self.tail.reset)


class Step1Status(unittest.TestCase):
    def test_statuses(self):
        self.assertEqual(journal.task_status([start()]), journal.RUNNING)
        halted = [start(), ev('halt', 101, reason='r')]
        self.assertEqual(journal.task_status(halted), journal.HALTED)
        self.assertEqual(journal.task_status(halted + [ev('resume', 102, reason='ok')]), journal.RUNNING)
        self.assertEqual(journal.task_status(halted + [ev('finish', 103, ended=103)]), journal.FINISHED)
        with self.assertRaises(ValueError):
            journal.task_status([])


class Step1WorkItems(unittest.TestCase):
    def test_lifecycle_and_rework(self):
        events = [start(),
                  delegation('game', 110, 'd1'), inspection('game', 120, 'd1'),
                  review('game', 130, 'd1', 'rework'),
                  delegation('board', 135, 'd2'),
                  delegation('game', 140, 'd3'), inspection('game', 150, 'd3', ['README.md']),
                  review('game', 160, 'd3', 'accepted', ['README.md'])]
        rows = journal.work_items(events)
        self.assertEqual([r['work_item'] for r in rows], ['game', 'board'])
        game, board = rows
        self.assertEqual((game['attempts'], game['reworks'], game['state']), (2, 1, journal.ACCEPTED))
        self.assertEqual((game['started_at'], game['accepted_at']), (110, 160))
        self.assertEqual(game['unexpected'], ['README.md'])
        self.assertEqual(game['files'], ['game.py'])
        self.assertEqual((board['state'], board['accepted_at']), (journal.AT_EXECUTOR, None))

    def test_states_review_and_rework(self):
        events = [start(), delegation('a', 110, 'd1'), inspection('a', 120, 'd1'),
                  delegation('b', 125, 'd2'), inspection('b', 126, 'd2'), review('b', 127, 'd2', 'rework')]
        states = {r['work_item']: r['state'] for r in journal.work_items(events)}
        self.assertEqual(states, {'a': journal.IN_REVIEW, 'b': journal.REWORK})

    def test_failed_attempt_is_not_a_rework(self):
        events = [start(), delegation('a', 110, 'd1'), inspection('a', 111, 'd1'), review('a', 112, 'd1', 'failed')]
        row = journal.work_items(events)[0]
        self.assertEqual((row['state'], row['reworks'], row['failures']), (journal.FAILED, 0, 1))
        self.assertEqual((journal.summary(events)['reworks'], journal.summary(events)['failures']), (0, 1))

    def test_old_journal_without_delegation_id(self):
        old_review = ev('review', 130, work_item='a', result='accepted')
        events = [start(), delegation('a', 110, 'd1'), old_review, ev('review', 131, work_item='ghost', result='rework')]
        rows = journal.work_items(events)
        self.assertEqual([(r['work_item'], r['state']) for r in rows], [('a', journal.ACCEPTED)])


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


class Step1Guards(unittest.TestCase):
    def values(self, events):
        return {g['name']: (g['value'], g['limit'], g['detail']) for g in journal.guard_status(events)}

    def test_order_and_limits(self):
        rows = journal.guard_status([start()])
        self.assertEqual([r['name'] for r in rows], list(DEFAULT_LIMITS))
        self.assertTrue(all(r['value'] == 0 and r['detail'] is None for r in rows))

    def test_values_match_limit_breach(self):
        fail = dict(status='failed', category='tests_failed')
        events = [start(limits=dict(DEFAULT_LIMITS, max_failed_runs=2)),
                  test_event(101, scope='a', phase='baseline', **fail),
                  test_event(102, scope='a', **fail),
                  review('x', 103, 'd0', 'rework'), review('y', 104, 'd1', 'rework'), review('y', 105, 'd2', 'rework'),
                  test_event(106, scope='b', status='failed', category='no_result')]
        values = self.values(events)
        self.assertEqual(values['max_reworks'], (2, 3, 'y'))
        self.assertEqual(values['max_no_result'], (1, 3, None))
        self.assertEqual(values['max_failed_runs'], (1, 2, 'a'))
        self.assertEqual(values['max_runs'], (3, 60, None))
        self.assertIsNone(limit_breach(events, {**DEFAULT_LIMITS, 'max_failed_runs': 2}))
        events.append(test_event(107, scope='a', **fail))
        self.assertEqual(self.values(events)['max_failed_runs'], (2, 2, 'a'))
        self.assertIsNotNone(limit_breach(events, {**DEFAULT_LIMITS, 'max_failed_runs': 2}))

    def test_failures_use_the_rework_limit_separately(self):
        events = [start(), review('a', 101, 'd1', 'rework'),
                  review('b', 102, 'd2', 'failed'), review('b', 103, 'd3', 'failed')]
        self.assertEqual(self.values(events)['max_reworks'], (2, 3, 'b'))
        events.append(review('b', 104, 'd4', 'failed'))
        self.assertEqual(self.values(events)['max_reworks'], (3, 3, 'b'))
        self.assertIn('executor failed 3 times on b', limit_breach(events, DEFAULT_LIMITS))

    def test_green_full_run_and_resume_reset(self):
        fail = dict(status='failed', category='tests_failed')
        events = [start(), test_event(101, scope='a', **fail), test_event(102)]
        self.assertEqual(self.values(events)['max_failed_runs'][0], 0)
        events = [start(), test_event(101, scope='a', **fail), ev('resume', 102, reason='ok')]
        self.assertEqual(self.values(events)['max_runs'][0], 0)


class Step1Summary(unittest.TestCase):
    def test_summary(self):
        events = [start(), delegation('a', 110, 'd1'), inspection('a', 111, 'd1'),
                  review('a', 112, 'd1', 'rework'),
                  test_event(113, scope='a', phase='baseline', status='failed', category='tests_failed'),
                  test_event(114, scope='a'), test_event(115),
                  ev('finish', 120, ended=119)]
        s = journal.summary(events)
        self.assertEqual((s['title'], s['session'], s['status']), ('Task', 'ses_1', journal.FINISHED))
        self.assertEqual((s['started_at'], s['ended_at'], s['last_event_at']), (100, 119, 120))
        self.assertEqual((s['work_item_count'], s['reworks'], s['work_runs'], s['green_work_runs']), (1, 1, 2, 2))
        self.assertEqual(s['last_full']['at'], 115)
        self.assertIsNone(s['halt_reason'])

    def test_halt_reason_and_no_full_run(self):
        s = journal.summary([start(), ev('halt', 101, reason='too many reworks')])
        self.assertEqual((s['status'], s['halt_reason'], s['last_full'], s['ended_at']),
                         (journal.HALTED, 'too many reworks', None, None))


if __name__ == '__main__':
    unittest.main()
