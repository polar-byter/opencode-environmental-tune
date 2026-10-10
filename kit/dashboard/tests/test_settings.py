"""Tests for kit/dashboard/settings.py. The registry and the launcher are replaced by fakes."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from kit.configurator import app
from kit.dashboard import settings

SECRET = 'sk-abcdefgh12345678'


class FakeKeys:
    """Replaces the registry functions of kit.configurator.keys."""

    def __init__(self):
        self.store = {}

    def patches(self):
        return [patch('kit.configurator.keys.read_user_variable', side_effect=self.store.get),
                patch('kit.configurator.keys.save_user_variable', side_effect=self.store.__setitem__),
                patch('kit.configurator.keys.key_is_set', side_effect=lambda n: bool(self.store.get(n)))]


class Base(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.keys = FakeKeys()
        for p in self.keys.patches():
            p.start()
            self.addCleanup(p.stop)
        env = patch.dict(os.environ, {}, clear=False)
        env.start()
        self.addCleanup(env.stop)
        for name in ('OCK_MASTER_CHIEF_API_KEY', 'OCK_EXECUTOR_API_KEY', 'OCK_TEST_KEY'):
            os.environ.pop(name, None)

    def choice_file(self):
        path = self.root / '.opencode' / 'kit-models.json'
        return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None

    def api_form(self, **extra):
        return dict(master_chief_source='api', master_chief_model='big', master_chief_url='https://api.example.com/v1',
                    master_chief_key_env='OCK_TEST_KEY', exec_source='opencode',
                    exec_model='opencode-go/mimo-v2.6-pro', **extra)


class Step4Keys(Base):
    def test_key_state_masks_and_never_returns_the_value(self):
        self.keys.store['OCK_TEST_KEY'] = SECRET
        state = settings.key_state('OCK_TEST_KEY')
        self.assertEqual(state, {'name': 'OCK_TEST_KEY', 'set': True, 'masked': 'sk-a…5678'})
        self.assertNotIn(SECRET, json.dumps(state))

    def test_key_from_environment_only(self):
        os.environ['OCK_TEST_KEY'] = SECRET
        with patch('kit.configurator.keys.key_is_set', return_value=True):
            self.assertEqual(settings.key_state('OCK_TEST_KEY')['masked'], 'sk-a…5678')

    def test_missing_and_invalid_names(self):
        self.assertEqual(settings.key_state('OCK_TEST_KEY'), {'name': 'OCK_TEST_KEY', 'set': False, 'masked': ''})
        with patch('kit.configurator.keys.read_user_variable') as reader:
            self.assertEqual(settings.key_state('sk-abc 123'), {'name': 'sk-abc 123', 'set': False, 'masked': ''})
            reader.assert_not_called()


class Step4Form(Base):
    def test_get_settings_default_and_saved(self):
        self.assertEqual(settings.get_settings(self.root)['form'], app.EMPTY_FORM)
        (self.root / '.opencode').mkdir()
        (self.root / '.opencode' / 'kit-models.json').write_text(json.dumps(
            {'executors': {'source': 'opencode', 'model': 'opencode-go/mimo-v2.6-pro'}}), encoding='utf-8')
        data = settings.get_settings(self.root)
        self.assertEqual((data['form']['exec_source'], data['form']['exec_model']), ('opencode', 'opencode-go/mimo-v2.6-pro'))
        self.assertEqual(set(data['keys']), {'master_chief', 'executor'})

    def test_get_settings_broken_file(self):
        (self.root / '.opencode').mkdir()
        (self.root / '.opencode' / 'kit-models.json').write_text('[1]', encoding='utf-8')
        data = settings.get_settings(self.root)
        self.assertEqual(data['form'], app.EMPTY_FORM)
        self.assertIn('error', data)

    def test_clean_form(self):
        form = settings.clean_form({'exec_source': ' opencode ', 'master_chief_key': SECRET, 'evil': 'x'})
        self.assertEqual(set(form), set(app.EMPTY_FORM))
        self.assertEqual(form['exec_source'], 'opencode')
        with self.assertRaisesRegex(ValueError, 'exec_model'):
            settings.clean_form({'exec_model': 5})


class Step4Buttons(Base):
    def test_save_writes_choice_and_key_name_only(self):
        result = settings.save_settings(self.root, self.api_form(master_chief_key=f' {SECRET} '))
        self.assertEqual(result['keys'], ['OCK_TEST_KEY'])
        self.assertEqual(self.keys.store['OCK_TEST_KEY'], SECRET)
        text = (self.root / '.opencode' / 'kit-models.json').read_text(encoding='utf-8')
        self.assertNotIn(SECRET, text)
        self.assertEqual(self.choice_file()['masterChief']['keyEnv'], 'OCK_TEST_KEY')
        self.assertNotIn(SECRET, json.dumps(result))

    def test_invalid_form_stores_nothing(self):
        bad = self.api_form(master_chief_key=SECRET)
        bad['master_chief_url'] = 'ftp://nope'
        with self.assertRaises(ValueError):
            settings.save_settings(self.root, bad)
        self.assertEqual(self.keys.store, {})
        self.assertIsNone(self.choice_file())

    def test_blank_key_is_not_saved(self):
        result = settings.save_settings(self.root, self.api_form(master_chief_key='   '))
        self.assertEqual((result['keys'], self.keys.store), ([], {}))

    def test_apply_and_reset(self):
        with patch('kit.configurator.app.apply_choices', return_value=(0, 'Master Chief: ok')) as apply:
            result = settings.apply_settings(self.root, self.api_form())
        apply.assert_called_once_with(self.root)
        self.assertEqual((result['code'], result['output']), (0, 'Master Chief: ok'))
        self.assertEqual(settings.reset_settings(self.root), {'removed': True})
        self.assertEqual(settings.reset_settings(self.root), {'removed': False})


class Step4Models(Base):
    def test_sources(self):
        with patch('kit.configurator.sources.opencode_models', return_value=['a/b']):
            self.assertEqual(settings.model_list('opencode'), ['a/b'])
        with patch('kit.configurator.sources.lmstudio_instances', return_value=[('id-1', 'Qwen')]):
            self.assertEqual(settings.model_list('lmstudio'), ['id-1'])
        self.keys.store['OCK_TEST_KEY'] = SECRET
        with patch('kit.configurator.sources.api_models', return_value=['m']) as api:
            self.assertEqual(settings.model_list('api', 'https://x/v1', 'OCK_TEST_KEY'), ['m'])
        api.assert_called_once_with('https://x/v1', SECRET)

    def test_errors(self):
        with self.assertRaisesRegex(ValueError, 'OCK_TEST_KEY is not set'):
            settings.model_list('api', 'https://x/v1', 'OCK_TEST_KEY')
        with self.assertRaises(ValueError):
            settings.model_list('magic')


if __name__ == '__main__':
    unittest.main()
