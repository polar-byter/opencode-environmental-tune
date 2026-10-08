"""Steps 1-2: choices.py. Run from the project root:

    py -m unittest discover -s kit/configurator/tests -t . -v

Until a function is implemented its tests end with NotImplementedError — that is expected.
"""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from kit import run_opencode
from kit.configurator import choices


class Step1BrainFromOpencode(unittest.TestCase):
    def test_returns_source_and_model(self):
        self.assertEqual(choices.brain_from_opencode('openai/gpt-6.1-sol'),
                         {'source': 'opencode', 'model': 'openai/gpt-6.1-sol'})

    def test_strips_spaces(self):
        self.assertEqual(choices.brain_from_opencode('  opencode-go/deepseek-v4.1-flash \n')['model'],
                         'opencode-go/deepseek-v4.1-flash')

    def test_model_without_provider_is_rejected(self):
        with self.assertRaises(ValueError):
            choices.brain_from_opencode('deepseek')

    def test_empty_model_is_rejected(self):
        for value in ('', '   '):
            with self.subTest(value=value), self.assertRaises(ValueError):
                choices.brain_from_opencode(value)


class Step1ApiChoice(unittest.TestCase):
    def test_returns_all_fields(self):
        self.assertEqual(choices.api_choice('https://api.example.com/v1', 'm', 'MY_KEY'),
                         {'source': 'api', 'baseURL': 'https://api.example.com/v1', 'model': 'm', 'keyEnv': 'MY_KEY'})

    def test_cleans_values(self):
        result = choices.api_choice(' http://localhost:8000/v1/ ', ' m ', ' MY_KEY ')
        self.assertEqual(result['baseURL'], 'http://localhost:8000/v1')
        self.assertEqual(result['model'], 'm')
        self.assertEqual(result['keyEnv'], 'MY_KEY')

    def test_url_must_be_http(self):
        for url in ('api.example.com/v1', 'ftp://example.com', ''):
            with self.subTest(url=url), self.assertRaises(ValueError):
                choices.api_choice(url, 'm', 'MY_KEY')

    def test_model_is_required(self):
        with self.assertRaises(ValueError):
            choices.api_choice('https://x/v1', ' ', 'MY_KEY')

    def test_key_itself_is_not_a_variable_name(self):
        for name in ('sk-abc123', '1KEY', 'MY KEY', ''):
            with self.subTest(name=name), self.assertRaises(ValueError):
                choices.api_choice('https://x/v1', 'm', name)


class Step1LmStudioChoice(unittest.TestCase):
    def test_without_instance(self):
        self.assertEqual(choices.lmstudio_choice(), {'source': 'lmstudio'})

    def test_blank_instance_is_none(self):
        for value in (None, '', '   '):
            with self.subTest(value=value):
                self.assertEqual(choices.lmstudio_choice(value), {'source': 'lmstudio'})

    def test_with_instance(self):
        self.assertEqual(choices.lmstudio_choice(' qwen-1 '), {'source': 'lmstudio', 'instance': 'qwen-1'})


class Step1BuildChoices(unittest.TestCase):
    def test_both_none_is_empty(self):
        self.assertEqual(choices.build_choices(None, None), {})

    def test_only_given_sections(self):
        brain = {'source': 'opencode', 'model': 'a/b'}
        executors = {'source': 'lmstudio'}
        self.assertEqual(choices.build_choices(brain, None), {'brain': brain})
        self.assertEqual(choices.build_choices(None, executors), {'executors': executors})
        self.assertEqual(choices.build_choices(brain, executors), {'brain': brain, 'executors': executors})


class Step2File(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / choices.CHOICES_PATH

    def test_missing_file_gives_empty_dict(self):
        self.assertEqual(choices.load_choices(self.root), {})

    def test_save_creates_folder_and_returns_path(self):
        data = {'brain': {'source': 'opencode', 'model': 'a/b'}}
        self.assertEqual(choices.save_choices(self.root, data), self.path)
        self.assertTrue(self.path.is_file())

    def test_save_then_load_round_trip(self):
        data = {'brain': {'source': 'api', 'baseURL': 'https://x/v1', 'model': 'модель', 'keyEnv': 'K'},
                'executors': {'source': 'lmstudio', 'instance': 'qwen'}}
        choices.save_choices(self.root, data)
        self.assertEqual(choices.load_choices(self.root), data)

    def test_saved_text_is_readable(self):
        choices.save_choices(self.root, {'brain': {'source': 'opencode', 'model': 'a/модель'}})
        text = self.path.read_text(encoding='utf-8')
        self.assertIn('модель', text)          # ensure_ascii=False
        self.assertIn('\n  "brain"', text)     # indent=2
        self.assertTrue(text.endswith('\n'))

    def test_no_temporary_file_is_left(self):
        choices.save_choices(self.root, {})
        self.assertEqual(sorted(p.name for p in self.path.parent.iterdir()), [self.path.name])

    def test_save_overwrites_previous(self):
        choices.save_choices(self.root, {'brain': {'source': 'opencode', 'model': 'a/b'}})
        choices.save_choices(self.root, {})
        self.assertEqual(choices.load_choices(self.root), {})

    def test_broken_file_is_a_value_error(self):
        self.path.parent.mkdir()
        for text in ('{broken', '[1, 2]'):
            with self.subTest(text=text):
                self.path.write_text(text, encoding='utf-8')
                with self.assertRaises(ValueError):
                    choices.load_choices(self.root)

    def test_reset(self):
        self.assertFalse(choices.reset_choices(self.root))
        choices.save_choices(self.root, {})
        self.assertTrue(choices.reset_choices(self.root))
        self.assertFalse(self.path.exists())


class Contract(unittest.TestCase):
    """What the configurator writes must be accepted by kit/run_opencode.py as is."""

    def test_launcher_reads_what_we_write(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'KIT_CONTRACT_KEY': 'x'}):
            root = Path(folder)
            data = choices.build_choices(
                choices.api_choice('https://api.example.com/v1', 'big', 'KIT_CONTRACT_KEY'),
                choices.lmstudio_choice('qwen-1'))
            choices.save_choices(root, data)
            loaded = run_opencode.load_choices(root)
        self.assertEqual(loaded['brain']['model'], 'big')
        self.assertEqual(loaded['executors'], {'source': 'lmstudio', 'instance': 'qwen-1'})

    def test_same_file_location(self):
        self.assertEqual(choices.CHOICES_PATH, Path('.opencode') / run_opencode.CHOICES_FILE)


if __name__ == '__main__':
    unittest.main()
