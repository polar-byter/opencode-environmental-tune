"""Contracts for the first two learning iterations, without HTTP or OpenCode."""
from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from kit.dashboard import console, journal


class Iteration1Console(unittest.TestCase):
    def test_prints_events_in_file_order(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'events.jsonl'
            path.write_text('{"kind":"start","at":1}\n{"kind":"test","at":2}\n',
                            encoding='utf-8')
            output = io.StringIO()
            with redirect_stdout(output):
                code = console.main([str(path)])
        self.assertEqual(code, 0)
        self.assertEqual(output.getvalue(), 'Events: 2\nstart @ 1\ntest @ 2\n')

    def test_missing_file_prints_zero(self):
        with tempfile.TemporaryDirectory() as folder:
            output = io.StringIO()
            with redirect_stdout(output):
                code = console.main([str(Path(folder) / 'missing.jsonl')])
        self.assertEqual((code, output.getvalue()), (0, 'Events: 0\n'))

    def test_read_errors_go_to_stderr(self):
        for error in (ValueError('line 2'), OSError('cannot read file')):
            with self.subTest(error=type(error).__name__):
                output, errors = io.StringIO(), io.StringIO()
                with patch('kit.dashboard.console.read_events', side_effect=error):
                    with redirect_stdout(output), redirect_stderr(errors):
                        code = console.main(['demo.jsonl'])
                self.assertEqual((code, output.getvalue()), (1, ''))
                self.assertEqual(errors.getvalue(), f'ERROR: {error}\n')


class Iteration1Reader(unittest.TestCase):
    def test_half_written_last_non_blank_line_is_ignored(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'events.jsonl'
            path.write_text('{"kind":"start","at":1}\n{"kind":"te\n\n',
                            encoding='utf-8')
            self.assertEqual(journal.read_events(path), [{'kind': 'start', 'at': 1}])

    def test_wrong_shape_in_the_middle_keeps_value_error(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'events.jsonl'
            path.write_text('{"kind":"start","at":1}\n[]\n'
                            '{"kind":"test","at":2}\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'line 2'):
                journal.read_events(path)

    def test_last_complete_json_with_wrong_shape_is_an_error(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'events.jsonl'
            path.write_text('{"kind":"start","at":1}\n[]\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'line 2'):
                journal.read_events(path)

    def test_blank_lines_do_not_change_error_line_numbers(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'events.jsonl'
            path.write_text('\n{"kind":"start","at":1}\n\n{bad\n'
                            '{"kind":"test","at":2}\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'line 4'):
                journal.read_events(path)


class Iteration2Summary(unittest.TestCase):
    def test_small_summary_excludes_baseline_and_separates_failures(self):
        events = [
            {'kind': 'start', 'at': 1, 'title': 'Demo'},
            {'kind': 'test', 'at': 2, 'phase': 'baseline', 'status': 'passed'},
            {'kind': 'review', 'at': 3, 'result': 'rework'},
            {'kind': 'review', 'at': 4, 'result': 'failed'},
            {'kind': 'test', 'at': 5, 'status': 'failed'},
            {'kind': 'test', 'at': 6, 'status': 'passed'},
            {'kind': 'finish', 'at': 7},
        ]
        self.assertEqual(journal.brief_summary(events), {
            'title': 'Demo', 'status': 'finished', 'event_count': 7,
            'last_event_at': 7, 'work_runs': 2, 'green_work_runs': 1,
            'reworks': 1, 'executor_failures': 1,
        })

    def test_started_task_has_no_runs(self):
        result = journal.brief_summary([{'kind': 'start', 'at': 1}])
        self.assertEqual(result['title'], 'Untitled task')
        self.assertEqual(result['status'], 'running')
        for key in ('work_runs', 'green_work_runs', 'reworks', 'executor_failures'):
            self.assertEqual(result[key], 0)

    def test_halt_then_resume(self):
        events = [{'kind': 'start', 'at': 1}, {'kind': 'halt', 'at': 2}]
        self.assertEqual(journal.brief_summary(events)['status'], 'halted')
        events.append({'kind': 'resume', 'at': 3})
        self.assertEqual(journal.brief_summary(events)['status'], 'running')

    def test_empty_or_missing_start_is_rejected(self):
        for events in ([], [{'kind': 'test', 'at': 1}]):
            with self.subTest(events=events), self.assertRaises(ValueError):
                journal.brief_summary(events)
