"""Tests for kit/dashboard/live.py on temporary folders."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from kit.dashboard import live


class Step6Live(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def test_stamp(self):
        path = self.root / 'f.txt'
        self.assertIsNone(live.stamp(path))
        path.write_text('abc')
        size, mtime = live.stamp(path)
        self.assertEqual(size, 3)
        self.assertIsInstance(mtime, int)

    def test_watched_files(self):
        (self.root / '.metrics' / 'task-1').mkdir(parents=True)
        files = live.watched_files({'kit': self.root})
        self.assertEqual(set(files), {('kit', 'choice'), ('kit', 'overlay'), ('kit', 'task:task-1')})
        self.assertEqual(files[('kit', 'task:task-1')], self.root / '.metrics' / 'task-1' / 'events.jsonl')
        self.assertEqual(files[('kit', 'choice')], self.root / '.opencode' / 'kit-models.json')

    def test_watcher(self):
        journal_path = self.root / 'events.jsonl'
        choice = self.root / 'choice.json'
        files = {('kit', 'task:t'): journal_path, ('kit', 'choice'): choice}
        watcher = live.ChangeWatcher()
        self.assertEqual(watcher.poll(files), [])
        journal_path.write_text('{}\n')
        self.assertEqual(watcher.poll(files), [{'project': 'kit', 'name': 'task:t'}])
        self.assertEqual(watcher.poll(files), [])
        with journal_path.open('a') as handle:
            handle.write('{}\n')
        choice.write_text('{}')
        self.assertEqual(watcher.poll(files), [{'project': 'kit', 'name': 'choice'},
                                               {'project': 'kit', 'name': 'task:t'}])
        os.remove(choice)
        self.assertEqual(watcher.poll(files), [{'project': 'kit', 'name': 'choice'}])

    def test_sse_message(self):
        raw = live.sse_message('change', {'project': 'кит', 'text': 'a\nb'})
        self.assertTrue(raw.startswith(b'event: change\ndata: '))
        self.assertTrue(raw.endswith(b'\n\n'))
        body = raw.decode('utf-8')[len('event: change\ndata: '):-2]
        self.assertNotIn('\n', body)
        self.assertEqual(json.loads(body), {'project': 'кит', 'text': 'a\nb'})


if __name__ == '__main__':
    unittest.main()
