"""The optional choice file of the model configurator, as read by run_opencode.py."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lmstudio_models as lm
import run_opencode as launcher

A = lm.LoadedModel('instance-a', 'model-a', 'A')
B = lm.LoadedModel('instance-b', 'model-b', 'B')
KEY = 'KIT_TEST_API_KEY'


class Choices(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        config = {
            'model': 'paid/master-chief',
            'agents': {
                'build': {'model': 'paid/master-chief', 'system': 'Master Chief prompt'},
                'executor': {'model': 'lmstudio/old', 'permissions': [{'action': 'shell', 'effect': 'deny'}]},
                'executor-fast': {'model': 'lmstudio/fast'},
            },
            'providers': {'lmstudio': {'models': {'old': {'modelID': 'model-b'}}}},
        }
        self.original = '// comments stay\n' + json.dumps(config)
        (self.root / 'opencode.jsonc').write_text(self.original, encoding='utf-8')
        (self.root / '.opencode').mkdir()
        self.env = patch.dict(launcher.os.environ, {KEY: 'secret-value'})
        self.env.start()
        self.addCleanup(self.env.stop)

    def write_choices(self, data):
        text = data if isinstance(data, str) else json.dumps(data)
        (self.root / '.opencode' / launcher.CHOICES_FILE).write_text(text, encoding='utf-8')

    def prepare(self, models=(A,), explicit=None):
        with patch.object(launcher, 'loaded_models', return_value=list(models)) as discovery:
            result = launcher.prepare(self.root, explicit)
        return result, discovery

    def overlay(self):
        text = (self.root / '.opencode/opencode.jsonc').read_text(encoding='utf-8')
        self.assertTrue(text.startswith(launcher.HEADER))
        return json.loads(text.removeprefix(launcher.HEADER))

    def api(self, model='remote-model'):
        return {'source': 'api', 'baseURL': 'https://api.example.com/v1/', 'model': model, 'keyEnv': KEY}

    # --- no file: behaviour unchanged ---------------------------------------

    def test_without_file_behaviour_is_unchanged(self):
        model, discovery = self.prepare()
        self.assertEqual(model, A)
        discovery.assert_called_once()
        config = self.overlay()
        self.assertEqual(set(config['agents']), {'executor', 'executor-fast'})
        self.assertEqual(set(config['providers']), {'lmstudio'})
        self.assertNotIn('model', config)

    def test_empty_object_is_the_default(self):
        self.write_choices({})
        model, _ = self.prepare()
        self.assertEqual(model, A)
        self.assertEqual(set(self.overlay()['agents']), {'executor', 'executor-fast'})
        self.assertNotIn('model', self.overlay())

    # --- Master Chief ---------------------------------------------------------------

    def test_master_chief_from_opencode_sets_build_and_plan_only(self):
        self.write_choices({'masterChief': {'source': 'opencode', 'model': 'openai/gpt-6.1-sol'}})
        model, _ = self.prepare()
        config = self.overlay()
        self.assertEqual(config['agents']['build'], {'model': 'openai/gpt-6.1-sol'})
        self.assertEqual(config['agents']['plan'], {'model': 'openai/gpt-6.1-sol'})
        # The main session uses the top-level model, so the overlay sets it too.
        self.assertEqual(config['model'], 'openai/gpt-6.1-sol')
        self.assertEqual(config['agents']['executor'], {'model': 'lmstudio/' + launcher.ALIAS})
        self.assertEqual(model, A)
        self.assertNotIn(launcher.MASTER_CHIEF_PROVIDER, config['providers'])

    def test_master_chief_api_adds_provider_with_key_name_not_key(self):
        self.write_choices({'masterChief': self.api()})
        self.prepare()
        config = self.overlay()
        provider = config['providers'][launcher.MASTER_CHIEF_PROVIDER]
        self.assertEqual(provider['package'], launcher.OPENAI_COMPATIBLE)
        self.assertEqual(provider['settings'], {'baseURL': 'https://api.example.com/v1'})
        self.assertEqual(provider['env'], [KEY])
        self.assertEqual(list(provider['models']), ['remote-model'])
        self.assertEqual(config['agents']['build']['model'], launcher.MASTER_CHIEF_PROVIDER + '/remote-model')
        self.assertEqual(config['model'], launcher.MASTER_CHIEF_PROVIDER + '/remote-model')
        text = (self.root / '.opencode/opencode.jsonc').read_text(encoding='utf-8')
        self.assertNotIn('secret-value', text)

    def test_master_chief_model_must_name_a_provider(self):
        self.write_choices({'masterChief': {'source': 'opencode', 'model': 'deepseek'}})
        with self.assertRaisesRegex(ValueError, 'provider/model'):
            self.prepare()

    # --- executors -----------------------------------------------------------

    def test_executors_api_skips_lm_studio(self):
        self.write_choices({'executors': self.api('coder')})
        model, discovery = self.prepare(models=[])
        self.assertIsNone(model)
        discovery.assert_not_called()
        config = self.overlay()
        ref = launcher.EXECUTOR_PROVIDER + '/coder'
        self.assertEqual(config['agents']['executor'], {'model': ref})
        self.assertEqual(config['agents']['executor-fast'], {'model': ref})
        self.assertNotIn('lmstudio', config['providers'])
        self.assertNotIn('build', config['agents'])
        self.assertNotIn('model', config)

    def test_executors_api_does_not_require_lm_studio_agents_in_source(self):
        source = json.loads(self.original.split('\n', 1)[1])
        source['agents']['executor']['model'] = 'other/model'
        (self.root / 'opencode.jsonc').write_text(json.dumps(source), encoding='utf-8')
        self.write_choices({'executors': self.api()})
        self.assertIsNone(self.prepare()[0])

    def test_executors_from_opencode_skip_lm_studio(self):
        self.write_choices({'executors': {'source': 'opencode', 'model': 'openrouter/qwen/qwen3-coder:free'}})
        model, discovery = self.prepare(models=[])
        self.assertIsNone(model)
        discovery.assert_not_called()
        config = self.overlay()
        self.assertEqual(config['agents']['executor'], {'model': 'openrouter/qwen/qwen3-coder:free'})
        self.assertEqual(config['agents']['executor-fast'], {'model': 'openrouter/qwen/qwen3-coder:free'})
        self.assertEqual(config['providers'], {})

    def test_command_line_model_conflicts_with_executors_from_opencode(self):
        self.write_choices({'executors': {'source': 'opencode', 'model': 'a/b'}})
        with self.assertRaisesRegex(ValueError, '--model'):
            self.prepare(explicit=A.id)

    def test_saved_instance_selects_among_several_loaded(self):
        self.write_choices({'executors': {'source': 'lmstudio', 'instance': A.id}})
        self.assertEqual(self.prepare(models=[A, B])[0], A)

    def test_command_line_model_wins_over_saved_instance(self):
        self.write_choices({'executors': {'source': 'lmstudio', 'instance': A.id}})
        self.assertEqual(self.prepare(models=[A, B], explicit=B.id)[0], B)

    def test_command_line_model_conflicts_with_executor_api(self):
        self.write_choices({'executors': self.api()})
        with self.assertRaisesRegex(ValueError, '--model'):
            self.prepare(explicit=A.id)

    def test_both_master_chief_and_executors_on_api(self):
        self.write_choices({'masterChief': self.api('big'), 'executors': self.api('small')})
        self.assertIsNone(self.prepare()[0])
        config = self.overlay()
        self.assertEqual(set(config['providers']), {launcher.MASTER_CHIEF_PROVIDER, launcher.EXECUTOR_PROVIDER})
        self.assertEqual(config['agents']['plan']['model'], launcher.MASTER_CHIEF_PROVIDER + '/big')
        self.assertEqual(config['agents']['executor']['model'], launcher.EXECUTOR_PROVIDER + '/small')

    # --- safety --------------------------------------------------------------

    def test_source_config_is_never_changed(self):
        self.write_choices({'masterChief': self.api(), 'executors': self.api()})
        self.prepare()
        self.assertEqual((self.root / 'opencode.jsonc').read_text(encoding='utf-8'), self.original)

    def test_choice_file_is_only_read(self):
        data = {'masterChief': {'source': 'opencode', 'model': 'openai/gpt-6.1-sol'}}
        self.write_choices(data)
        before = (self.root / '.opencode' / launcher.CHOICES_FILE).read_bytes()
        self.prepare()
        self.assertEqual((self.root / '.opencode' / launcher.CHOICES_FILE).read_bytes(), before)

    def test_switching_back_to_default_removes_previous_choices(self):
        self.write_choices({'masterChief': self.api(), 'executors': self.api()})
        self.prepare()
        (self.root / '.opencode' / launcher.CHOICES_FILE).unlink()
        self.prepare()
        config = self.overlay()
        self.assertEqual(set(config['agents']), {'executor', 'executor-fast'})
        self.assertEqual(set(config['providers']), {'lmstudio'})

    def test_missing_key_variable_stops_before_writing(self):
        self.prepare()
        before = (self.root / '.opencode/opencode.jsonc').read_bytes()
        self.write_choices({'masterChief': {**self.api(), 'keyEnv': 'KIT_TEST_MISSING_KEY'}})
        with patch.dict(launcher.os.environ, {}, clear=False):
            launcher.os.environ.pop('KIT_TEST_MISSING_KEY', None)
            with self.assertRaisesRegex(ValueError, 'KIT_TEST_MISSING_KEY'):
                self.prepare()
        self.assertEqual((self.root / '.opencode/opencode.jsonc').read_bytes(), before)

    def test_key_itself_in_key_env_is_rejected(self):
        self.write_choices({'masterChief': {**self.api(), 'keyEnv': 'sk-abc123-secret'}})
        with self.assertRaisesRegex(ValueError, 'variable name'):
            self.prepare()

    def test_invalid_files_are_explained(self):
        cases = [
            ('{broken', 'not valid JSON'),
            ('[]', 'JSON object'),
            ({'masterChief': {'source': 'magic'}}, 'masterChief.source'),
            ({'executors': {'source': 'cloud'}}, 'executors.source'),
            ({'executors': {'source': 'api', 'baseURL': 'ftp://x', 'model': 'm', 'keyEnv': KEY}}, 'http'),
            ({'executors': {'source': 'api', 'baseURL': 'https://x', 'keyEnv': KEY}}, 'executors.model'),
            ({'executors': {'source': 'lmstudio', 'instance': ''}}, 'instance'),
            ({'executors': {'source': 'opencode', 'model': 'no-provider'}}, 'executors.model'),
        ]
        for data, message in cases:
            with self.subTest(data=data):
                self.write_choices(data)
                with self.assertRaisesRegex(ValueError, message):
                    self.prepare()


class Launch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        config = {'agents': {'executor': {'model': 'lmstudio/x'}, 'executor-fast': {'model': 'lmstudio/x'}}}
        (self.root / 'opencode.jsonc').write_text(json.dumps(config), encoding='utf-8')
        (self.root / '.opencode').mkdir()

    def run_main(self, models):
        with patch.object(launcher.Path, 'cwd', return_value=self.root), \
             patch.object(launcher, 'find_opencode', return_value='opencode.exe'), \
             patch.object(launcher, 'loaded_models', return_value=models), \
             patch.dict(launcher.os.environ, {KEY: 'secret', 'OPENCODE_KIT_INSTANCE': 'stale'}), \
             patch.object(launcher.subprocess, 'call', return_value=0) as run:
            self.assertEqual(launcher.main(['--', 'run', 'hello']), 0)
        return run.call_args.kwargs['env']

    def test_lm_studio_launch_reports_instance(self):
        environment = self.run_main([A])
        self.assertEqual(environment['OPENCODE_KIT_EXECUTORS'], 'lmstudio')
        self.assertEqual(environment['OPENCODE_KIT_INSTANCE'], A.id)

    def test_api_launch_does_not_report_a_stale_instance(self):
        choice = {'executors': {'source': 'api', 'baseURL': 'https://x/v1', 'model': 'm', 'keyEnv': KEY}}
        (self.root / '.opencode' / launcher.CHOICES_FILE).write_text(json.dumps(choice), encoding='utf-8')
        environment = self.run_main([])
        self.assertEqual(environment['OPENCODE_KIT_EXECUTORS'], 'api')
        self.assertNotIn('OPENCODE_KIT_INSTANCE', environment)

    def test_opencode_launch_reports_the_source(self):
        choice = {'executors': {'source': 'opencode', 'model': 'a/b'}}
        (self.root / '.opencode' / launcher.CHOICES_FILE).write_text(json.dumps(choice), encoding='utf-8')
        environment = self.run_main([])
        self.assertEqual(environment['OPENCODE_KIT_EXECUTORS'], 'opencode')
        self.assertNotIn('OPENCODE_KIT_INSTANCE', environment)


if __name__ == '__main__':
    unittest.main()
