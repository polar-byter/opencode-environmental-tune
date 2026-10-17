"""TaskJournal.append: what the journal writes and what it refuses."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from journal import TaskJournal  # noqa: E402


class AppendTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.journal = TaskJournal(Path(folder.name))
        self.journal.task_dir('task').mkdir(parents=True)
        self.journal.append('task', 'start', title='Task')

    def test_journal_sets_time_and_id_itself(self):
        event = self.journal.append('task', 'resume', reason='ok', at=0, event_id='fake')
        self.assertNotEqual(event['at'], 0)
        self.assertNotEqual(event['event_id'], 'fake')
        self.assertEqual(self.journal.read('task')[-1], event)

    def test_unknown_kind_is_refused_before_writing(self):
        with self.assertRaisesRegex(ValueError, 'reveiw'):
            self.journal.append('task', 'reveiw', result='accepted')
        self.assertEqual([e['kind'] for e in self.journal.read('task')], ['start'])


class ReadTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.journal = TaskJournal(Path(folder.name))
        self.journal.task_dir('task').mkdir(parents=True)
        self.path = self.journal.task_dir('task') / 'events.jsonl'

    def write(self, *lines):
        self.path.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    def assert_refused(self, message):
        with self.assertRaisesRegex(ValueError, message):
            self.journal.read('task')

    def test_good_journal(self):
        self.write('{"kind": "start", "at": 1}', '{"kind": "test", "at": 2}')
        self.assertEqual([e['kind'] for e in self.journal.read('task')], ['start', 'test'])

    def test_each_problem_names_its_line(self):
        start = '{"kind": "start", "at": 1}'
        cases = [
            ((start, '{oops'), 'line 2: invalid JSON'),
            ((start, '[1, 2]'), 'line 2: not a JSON object'),
            ((start, '{"kind": "test", "at": true}'), 'line 2: missing or invalid "at"'),
            ((start, '{"kind": "test", "at": -5}'), 'line 2: missing or invalid "at"'),
            ((start, '{"kind": "reveiw", "at": 2}'), "line 2: unknown event type 'reveiw'"),
            (('{"kind": "test", "at": 1}',), 'line 1: the first event must be "start"'),
        ]
        for lines, message in cases:
            with self.subTest(message=message):
                self.write(*lines)
                self.assert_refused(message)

    def test_missing_and_empty_journal(self):
        self.assert_refused('Cannot read task task')
        self.path.write_text('', encoding='utf-8')
        self.assert_refused('the journal is empty')


if __name__ == '__main__':
    unittest.main()
