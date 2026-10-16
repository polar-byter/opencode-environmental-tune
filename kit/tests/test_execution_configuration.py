"""Compatibility of saved choices, role preparation and exact usage attribution."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from kit import run_opencode
from kit.configurator import app, workflow
from kit.task_metrics import TaskMetrics
from kit.dashboard.observations import attach_models


class ConfigurationTests(unittest.TestCase):
    def test_third_role_and_every_limit_survive_form_round_trip(self):
        form = dict(app.EMPTY_FORM, bug_fixer_source='api', bug_fixer_url='https://fix.example/v1',
                    bug_fixer_model='strong', bug_fixer_key_env='FIX_KEY', max_executors='2',
                    max_repeated_actions='5', fixer_max_steps='48', fixer_max_seconds='900',
                    executor_max_attempts='5', fixer_max_attempts='12', max_attempts='17')
        choice = app.form_to_choices(form)
        self.assertEqual(choice['bugFixer']['keyEnv'], 'FIX_KEY')
        self.assertEqual(choice['execution']['maxExecutors'], 2)
        self.assertEqual(app.choices_to_form(choice), form)

    def test_disabled_fixer_ignores_old_key_draft(self):
        with patch.object(workflow, 'existing_key', return_value=''):
            choice, keys = workflow.validate(dict(app.EMPTY_FORM), {'bug_fixer': 'do-not-save'})
        self.assertNotIn('bugFixer', choice)
        self.assertNotIn('execution', choice)
        self.assertFalse(keys)

    def test_invalid_parallelism_fails_before_any_key_is_saved(self):
        with patch.object(workflow.keys, 'save_user_variable') as save:
            for number in ('0', '9', '2.5', 'True'):
                with self.subTest(number=number), self.assertRaises(workflow.FormError):
                    workflow.validate(dict(app.EMPTY_FORM, max_executors=number), {})
            save.assert_not_called()

    def test_launcher_uses_canonical_prompts_and_new_defaults_without_lmstudio(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agents = {'build': {'model': 'opencode/deepseek-v4.1-flash-free'},
                      'executor': {'model': 'opencode/mimo-v2.6-flash-free'},
                      'executor-fast': {'model': 'opencode/mimo-v2.6-flash-free'},
                      'bug-fixer': {'model': 'opencode/deepseek-v4.1-flash-free', 'disabled': False}}
            (root / 'opencode.jsonc').write_text(json.dumps({'agents': agents}), encoding='utf-8')
            folder = root / 'kit/prompts';folder.mkdir(parents=True)
            (folder / 'master-chief.md').write_text('# Canonical Chief\nRead this.', encoding='utf-8')
            (folder / 'README.ru.md').write_text('Human explanation must not be injected', encoding='utf-8')
            with patch.object(run_opencode, 'loaded_models', side_effect=AssertionError('No LM Studio needed')):
                run_opencode.prepare(root)
            overlay = json.loads(run_opencode.strip_jsonc((root / '.opencode/opencode.jsonc').read_text(encoding='utf-8')))
            self.assertEqual(overlay['agents']['executor']['model'], agents['executor']['model'])
            self.assertEqual(overlay['agents']['build']['system'], '# Canonical Chief\nRead this.')
            self.assertFalse(overlay['agents']['bug-fixer']['disabled'])
            self.assertNotIn('Human explanation', json.dumps(overlay))
            (root / '.opencode/kit-models.json').write_text(json.dumps({'executors': {
                'source': 'opencode', 'model': 'opencode/mimo-v2.6-flash-free'}}), encoding='utf-8')
            run_opencode.prepare(root)
            disabled = json.loads(run_opencode.strip_jsonc((root / '.opencode/opencode.jsonc').read_text(encoding='utf-8')))
            self.assertTrue(disabled['agents']['bug-fixer']['disabled'])

    def test_usage_is_deduplicated_then_attached_to_exact_session(self):
        def export(sid, parent, mid, number):
            return {'info': {'id': sid, 'parentID': parent}, 'messages': [{
                'id': mid, 'type': 'assistant', 'time': {'created': 10000, 'completed': 11000},
                'model': {'providerID': 'opencode', 'id': 'mimo-v2.6-flash-free'},
                'tokens': {'input': number, 'output': 2, 'reasoning': 0, 'cache': {'read': 0, 'write': 0}}}]}
        root = export('root', None, 'chief', 3)
        a, b = export('a', 'root', 'same-message-id', 10), export('b', 'root', 'same-message-id', 20)
        usage = TaskMetrics(Path.cwd()).parse_exports([root, a, a, b], 'root', 0, 20)
        self.assertEqual(usage['models'][0]['input'], 33)
        items = [{'attempts': [{'at': 1, 'workspace': 'one', 'session': 'a'}]},
                 {'attempts': [{'at': 1, 'workspace': 'two', 'session': 'b'}]},
                 {'attempts': [{'at': 1, 'workspace': 'unbound'}]}]
        attach_models(items, {'session_models': {'a': 'actual/A', 'b': 'actual/B'}, 'usage': usage,
                              'calls': [{'at': 2, 'session': 'b'}]})
        self.assertEqual(items[0]['model'], 'actual/A')
        self.assertEqual(items[1]['attempts'][0]['usage'][0]['input'], 20)
        self.assertIsNone(items[0]['attempts'][0]['usage'][0]['cost_usd'])
        self.assertIsNone(items[2]['model'])


if __name__ == '__main__':
    unittest.main()
