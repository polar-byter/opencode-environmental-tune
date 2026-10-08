"""Steps 3-4: sources.py. Network and OpenCode are replaced with fakes (unittest.mock)."""
import io
import json
import subprocess
import unittest
from unittest.mock import patch

from kit import lmstudio_models
from kit.configurator import sources

OPENCODE_OUTPUT = """
opencode-go/deepseek-v4.1-flash
openai/gpt-6.1-sol    (ChatGPT Plus)
lmstudio/qwen3-27b-coder
openai/gpt-6.1-sol
Some header without a slash

"""


class Step3ParseOpencode(unittest.TestCase):
    def test_references_sorted_and_unique(self):
        self.assertEqual(sources.parse_opencode_models(OPENCODE_OUTPUT), [
            'lmstudio/qwen3-27b-coder', 'openai/gpt-6.1-sol', 'opencode-go/deepseek-v4.1-flash'])

    def test_empty_output(self):
        self.assertEqual(sources.parse_opencode_models(''), [])


class Step3ParseApi(unittest.TestCase):
    def test_ids_sorted_and_unique(self):
        data = {'object': 'list', 'data': [{'id': 'b'}, {'id': 'a'}, {'id': 'b'}, {'name': 'no id'}, {'id': 7}, 'junk']}
        self.assertEqual(sources.parse_api_models(data), ['a', 'b'])

    def test_empty_list_is_fine(self):
        self.assertEqual(sources.parse_api_models({'data': []}), [])

    def test_missing_data_is_an_error(self):
        for data in ({}, {'data': 'x'}, {'models': []}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                sources.parse_api_models(data)


class Step4OpencodeModels(unittest.TestCase):
    def test_runs_models_command_without_shell(self):
        done = subprocess.CompletedProcess(['oc', 'models'], 0, stdout=OPENCODE_OUTPUT, stderr='')
        with patch.object(sources, 'find_opencode', return_value='oc.exe'), \
             patch.object(sources.subprocess, 'run', return_value=done) as run:
            self.assertIn('openai/gpt-6.1-sol', sources.opencode_models())
        self.assertEqual(run.call_args.args[0], ['oc.exe', 'models'])
        self.assertTrue(run.call_args.kwargs.get('capture_output'))
        self.assertTrue(run.call_args.kwargs.get('text'))
        self.assertEqual(run.call_args.kwargs.get('timeout'), sources.TIMEOUT)
        self.assertNotIn('shell', run.call_args.kwargs)

    def test_error_exit_is_a_value_error_with_details(self):
        done = subprocess.CompletedProcess(['oc', 'models'], 2, stdout='', stderr='not logged in')
        with patch.object(sources, 'find_opencode', return_value='oc.exe'), \
             patch.object(sources.subprocess, 'run', return_value=done):
            with self.assertRaisesRegex(ValueError, 'not logged in'):
                sources.opencode_models()

    def test_missing_opencode_is_a_value_error(self):
        with patch.object(sources, 'find_opencode', side_effect=ValueError('OpenCode CLI not found')):
            with self.assertRaises(ValueError):
                sources.opencode_models()


class Step4ApiModels(unittest.TestCase):
    def test_request_has_url_and_bearer_key(self):
        answer = io.BytesIO(json.dumps({'data': [{'id': 'm1'}]}).encode())
        with patch.object(sources.urllib.request, 'urlopen', return_value=answer) as call:
            self.assertEqual(sources.api_models('https://api.example.com/v1/', 'sk-secret'), ['m1'])
        request = call.call_args.args[0]
        self.assertEqual(request.full_url, 'https://api.example.com/v1/models')
        self.assertEqual(request.get_header('Authorization'), 'Bearer sk-secret')
        self.assertEqual(call.call_args.kwargs.get('timeout'), sources.TIMEOUT)


class Step4LmStudio(unittest.TestCase):
    def test_pairs_sorted_by_name(self):
        models = [lmstudio_models.LoadedModel('id-z', 'key-z', 'Zeta'),
                  lmstudio_models.LoadedModel('id-a', 'key-a', 'Alpha')]
        with patch.object(sources.lmstudio_models, 'loaded_models', return_value=models) as call:
            self.assertEqual(sources.lmstudio_instances('http://localhost:1/v1'),
                             [('id-a', 'Alpha'), ('id-z', 'Zeta')])
        call.assert_called_once_with('http://localhost:1/v1')


if __name__ == '__main__':
    unittest.main()
