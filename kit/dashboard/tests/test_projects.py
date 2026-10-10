"""Tests for kit/dashboard/projects.py on temporary project folders."""
import json
from pathlib import Path
import tempfile
import unittest

from kit.dashboard import projects


def make_project(base: Path, name: str, base_config=None) -> Path:
    root = base / name
    (root / '.opencode').mkdir(parents=True)
    config = base_config or {'model': 'opencode-go/deepseek-v4.1-flash',
                             'agents': {'build': {'model': 'opencode-go/deepseek-v4.1-flash'},
                                        'executor': {'model': 'lmstudio/qwen'}, 'helper': {'mode': 'x'}}}
    (root / 'opencode.jsonc').write_text('// project config\n' + json.dumps(config), encoding='utf-8')
    return root


def add_task(root: Path, task: str, lines: list[str]):
    folder = root / '.metrics' / task
    folder.mkdir(parents=True)
    (folder / 'events.jsonl').write_text(''.join(line + '\n' for line in lines), encoding='utf-8')


def start(at, title):
    return json.dumps({'kind': 'start', 'at': at, 'session': None, 'title': title, 'event_id': 'e'})


class Step3Discover(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)

    def test_project_key(self):
        self.assertEqual(projects.project_key(Path('My Kit_v2'), set()), 'my-kit-v2')
        self.assertEqual(projects.project_key(Path('My Kit_v2'), {'my-kit-v2'}), 'my-kit-v2-2')
        self.assertEqual(projects.project_key(Path('My Kit_v2'), {'my-kit-v2', 'my-kit-v2-2'}), 'my-kit-v2-3')
        self.assertEqual(projects.project_key(Path('Кит'), set()), 'project')

    def test_discover(self):
        a = make_project(self.base, 'Kit')
        b = make_project(self.base / 'other', 'Kit')
        found = projects.discover([a, b, a / '.' ])
        self.assertEqual([(p.key, p.name) for p in found], [('kit', 'Kit'), ('kit-2', 'Kit')])
        self.assertEqual(found[0].root, a.resolve())

    def test_discover_errors(self):
        (self.base / 'empty').mkdir()
        for paths in ([], [self.base / 'empty'], [self.base / 'missing']):
            with self.assertRaises(ValueError):
                projects.discover(paths)


class Step3Tasks(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = make_project(Path(tmp.name), 'kit')
        self.project = projects.discover([self.root])[0]

    def test_task_dir_validation(self):
        self.assertEqual(projects.task_dir(self.project, 'task-1'), self.project.root / '.metrics' / 'task-1')
        for bad in ('..', 'a/b', 'CON', ''):
            with self.assertRaises(ValueError):
                projects.task_dir(self.project, bad)

    def test_no_metrics(self):
        self.assertEqual(projects.list_tasks(self.project), [])

    def test_list_tasks_newest_first_and_skips_broken(self):
        add_task(self.root, 'old', [start(100, 'Old')])
        add_task(self.root, 'new', [start(200, 'New'),
                                     json.dumps({'kind': 'finish', 'at': 250, 'ended': 250, 'event_id': 'f'})])
        add_task(self.root, 'broken', ['{bad', start(300, 'x')])
        add_task(self.root, 'empty', [])
        (self.root / '.metrics' / 'CON').mkdir()
        rows = projects.list_tasks(self.project)
        self.assertEqual([r['id'] for r in rows], ['new', 'old'])
        self.assertEqual((rows[0]['title'], rows[0]['status'], rows[0]['started_at'], rows[0]['last_event_at']),
                         ('New', 'finished', 200, 250))
        self.assertEqual(rows[1]['status'], 'running')


class Step3Models(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = make_project(Path(tmp.name), 'kit')
        self.project = projects.discover([self.root])[0]

    def test_without_choice_and_overlay(self):
        info = projects.model_choice(self.project)
        self.assertEqual(info['saved'], {})
        self.assertIsNone(info['overlay'])
        self.assertEqual(info['base'], {'model': 'opencode-go/deepseek-v4.1-flash',
                                        'agents': {'build': 'opencode-go/deepseek-v4.1-flash',
                                                   'executor': 'lmstudio/qwen'}})

    def test_with_choice_and_overlay(self):
        choice = {'masterChief': {'source': 'opencode', 'model': 'openai/gpt-6.1-sol'}}
        (self.root / '.opencode' / 'kit-models.json').write_text(json.dumps(choice), encoding='utf-8')
        overlay = {'model': 'openai/gpt-6.1-sol', 'agents': {'build': {'model': 'openai/gpt-6.1-sol'},
                                                             'executor': {'model': 'opencode-go/mimo-v2.6-pro'}}}
        (self.root / projects.OVERLAY_PATH).write_text('// Generated\n' + json.dumps(overlay), encoding='utf-8')
        info = projects.model_choice(self.project)
        self.assertEqual(info['saved'], choice)
        self.assertEqual(info['overlay'], {'model': 'openai/gpt-6.1-sol',
                                           'agents': {'build': 'openai/gpt-6.1-sol',
                                                      'executor': 'opencode-go/mimo-v2.6-pro'}})

    def test_broken_files_are_reported(self):
        (self.root / '.opencode' / 'kit-models.json').write_text('{oops', encoding='utf-8')
        (self.root / projects.OVERLAY_PATH).write_text('{oops', encoding='utf-8')
        info = projects.model_choice(self.project)
        self.assertIn('error', info['saved'])
        self.assertIn('error', info['overlay'])


if __name__ == '__main__':
    unittest.main()
