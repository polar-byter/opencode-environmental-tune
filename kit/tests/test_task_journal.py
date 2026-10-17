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


if __name__ == '__main__':
    unittest.main()
