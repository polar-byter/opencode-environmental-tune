"""Prevent unloaded-model fallback and verify the actual OpenCode launch boundary."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lmstudio_models as lm
import run_opencode as launcher
import pipeline_smoke
import check_env

A = lm.LoadedModel('instance-a', 'model-a', 'A')
B = lm.LoadedModel('instance-b', 'model-b', 'B')


class Discovery(unittest.TestCase):
    def test_only_loaded_language_instances_are_selected(self):
        data = {'models': [
            {'type': 'llm', 'key': 'unloaded', 'loaded_instances': []},
            {'type': 'embedding', 'key': 'embedding', 'loaded_instances': [{'id': 'vector'}]},
            {'type': 'llm', 'key': 'model-a', 'display_name': 'A', 'loaded_instances': [{'id': 'instance-a', 'config': {'context_length': 8192}}]},
        ]}
        with patch.object(lm.urllib.request, 'urlopen', return_value=io.BytesIO(json.dumps(data).encode())) as call:
            self.assertEqual(lm.loaded_models('http://localhost:9999/v1/'), [A])
        self.assertEqual(call.call_args.args[0].full_url, 'http://localhost:9999/api/v1/models')
        self.assertEqual(call.call_args.args[0].get_method(), 'GET')

    def test_unknown_api_does_not_fall_back(self):
        with patch.object(lm.urllib.request, 'urlopen', return_value=io.BytesIO(b'{"data":[{"id":"downloaded"}]}')):
            with self.assertRaisesRegex(ValueError, 'Unsupported'):
                lm.loaded_models()

    def test_bad_instance_is_an_error(self):
        data = {'models': [{'type': 'llm', 'key': 'a', 'loaded_instances': [{}]}]}
        with patch.object(lm.urllib.request, 'urlopen', return_value=io.BytesIO(json.dumps(data).encode())):
            with self.assertRaisesRegex(ValueError, 'without an ID'):
                lm.loaded_models()


class Selection(unittest.TestCase):
    def test_sole_loaded_instance_wins_over_unloaded_config(self):
        self.assertEqual(lm.select_model([A], preferred='not-loaded'), A)

    def test_loaded_config_preference_resolves_multiple_models(self):
        self.assertEqual(lm.select_model([A, B], preferred='model-b'), B)

    def test_explicit_instance_wins(self):
        self.assertEqual(lm.select_model([A, B], preferred='model-b', explicit=A.id), A)

    def test_explicit_unloaded_model_is_not_replaced(self):
        with self.assertRaisesRegex(ValueError, 'does not identify'):
            lm.select_model([A], explicit='unloaded')

    def test_no_loaded_model_is_an_error(self):
        with self.assertRaisesRegex(ValueError, 'No language model'):
            lm.select_model([])

    def test_ambiguous_models_are_not_selected_by_list_order(self):
        with self.assertRaisesRegex(ValueError, 'Several'):
            lm.select_model([A, B], preferred='unloaded')

    def test_multiple_instances_of_one_model_require_instance_id(self):
        other = lm.LoadedModel('second-a', 'model-a', 'A')
        with self.assertRaisesRegex(ValueError, 'does not identify'):
            lm.select_model([A, other], preferred='model-a')
        self.assertEqual(lm.select_model([A, other], explicit='second-a'), other)


class Launch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = {
            'model': 'paid/brain',
            'agents': {'executor': {'model': 'lmstudio/old', 'permissions': [{'action': 'shell', 'effect': 'deny'}]}, 'executor-fast': {'model': 'lmstudio/fast'}},
            'providers': {'lmstudio': {'models': {'old': {'modelID': 'unloaded'}}}},
        }
        self.original = '// My comments stay\n' + json.dumps(self.config)
        (self.root / 'opencode.jsonc').write_text(self.original, encoding='utf-8')

    def prepare(self):
        with patch.object(launcher, 'loaded_models', return_value=[A]):
            return launcher.prepare(self.root)

    def test_both_agents_use_exact_instance_and_source_is_unchanged(self):
        self.assertEqual(self.prepare(), A)
        self.assertEqual((self.root / 'opencode.jsonc').read_text(encoding='utf-8'), self.original)
        text = (self.root / '.opencode/opencode.jsonc').read_text(encoding='utf-8')
        config = json.loads(text.removeprefix(launcher.HEADER))
        self.assertEqual(config['providers']['lmstudio']['models'][launcher.ALIAS]['modelID'], A.id)
        self.assertEqual(set(config['agents']), {'executor', 'executor-fast'})
        self.assertTrue(all(a == {'model': 'lmstudio/loaded-executor'} for a in config['agents'].values()))
        self.assertNotIn('settings', config['providers']['lmstudio'])
        self.assertNotIn('model', config)  # cloud brain preserved by config merge

    def test_next_launch_refreshes_our_selection(self):
        self.prepare()
        with patch.object(launcher, 'loaded_models', return_value=[B]):
            launcher.prepare(self.root)
        self.assertIn(B.id, (self.root / '.opencode/opencode.jsonc').read_text())

    def test_user_overlay_is_never_overwritten(self):
        folder = self.root / '.opencode'
        folder.mkdir()
        for name in ('opencode.json', 'opencode.jsonc'):
            path = folder / name
            path.write_text('{"model":"mine"}')
            with self.assertRaisesRegex(ValueError, 'Existing'):
                self.prepare()
            self.assertEqual(path.read_text(), '{"model":"mine"}')
            path.unlink()

    def test_discovery_error_preserves_previous_overlay(self):
        self.prepare()
        path = self.root / '.opencode/opencode.jsonc'
        before = path.read_bytes()
        with patch.object(launcher, 'loaded_models', side_effect=OSError('offline')):
            with self.assertRaises(OSError):
                launcher.prepare(self.root)
        self.assertEqual(path.read_bytes(), before)

    def test_no_model_does_not_start_cli(self):
        with patch.object(launcher.Path, 'cwd', return_value=self.root), \
             patch.object(launcher, 'find_opencode', return_value='opencode.exe'), \
             patch.object(launcher, 'loaded_models', return_value=[]), \
             patch.object(launcher.subprocess, 'call') as run:
            self.assertEqual(launcher.main(['--', 'run', 'hello']), 1)
        run.assert_not_called()

    def test_arguments_forwarded_without_shell_and_exit_code_preserved(self):
        args = ['run', '--standalone', 'text with spaces & symbols']
        with patch.object(launcher.Path, 'cwd', return_value=self.root), \
             patch.object(launcher, 'find_opencode', return_value='opencode.exe'), \
             patch.object(launcher, 'loaded_models', return_value=[A]), \
             patch.object(launcher.subprocess, 'call', return_value=7) as run:
            self.assertEqual(launcher.main(['--', *args]), 7)
        run.assert_called_once_with(['opencode.exe', *args], cwd=self.root)

    def test_run_uses_fresh_private_server_by_default(self):
        with patch.object(launcher.Path, 'cwd', return_value=self.root), \
             patch.object(launcher, 'find_opencode', return_value='opencode.exe'), \
             patch.object(launcher, 'loaded_models', return_value=[A]), \
             patch.object(launcher.subprocess, 'call', return_value=0) as run:
            self.assertEqual(launcher.main(['--', 'run', 'hello']), 0)
        run.assert_called_once_with(['opencode.exe', 'run', '--standalone', 'hello'], cwd=self.root)

    def test_desktop_reload_updates_config_without_running_a_task(self):
        with patch.object(launcher.Path, 'cwd', return_value=self.root), \
             patch.object(launcher, 'find_opencode', return_value='opencode.exe'), \
             patch.object(launcher, 'loaded_models', return_value=[A]), \
             patch.object(launcher.subprocess, 'call', return_value=0) as run:
            self.assertEqual(launcher.main(['--prepare-only', '--reload']), 0)
        run.assert_called_once_with(['opencode.exe', 'reload'], cwd=self.root)


class Diagnostics(unittest.TestCase):
    def test_check_env_refuses_ambiguous_selection_before_generation(self):
        with patch.object(check_env, 'http_post_json') as post:
            self.assertFalse(check_env.live_test([A, B]))
        post.assert_not_called()

    def test_smoke_refuses_unloaded_explicit_model_before_generation(self):
        with patch.object(pipeline_smoke, 'load_config', return_value={}), \
             patch.object(pipeline_smoke, 'loaded_models', return_value=[A]), \
             patch.object(pipeline_smoke, 'run_smoke') as run:
            self.assertEqual(pipeline_smoke.main(['--model', 'unloaded']), 1)
        run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
