"""Language negotiation, presentation boundaries and frozen-report integrity."""
import copy
import http.client
import json
import os
from pathlib import Path
import shutil
from string import Formatter
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

from kit import localization
from kit.configurator import i18n
from kit.dashboard import runtime
from kit.task_metrics import TaskMetrics


class LanguageSelection(unittest.TestCase):
    def test_locale_names_priorities_and_unsupported_fallback(self):
        self.assertEqual(localization.choose_language(['de-DE', 'ru_RU.UTF-8', 'en-US']), 'ru')
        self.assertEqual(localization.choose_language(['fr', None, []]), 'en')
        self.assertEqual(localization.request_language('ru;q=0.1, en-US;q=0.9'), 'en')
        self.assertEqual(localization.request_language('ru;q=0, en;q=0.2'), 'en')
        self.assertEqual(localization.request_language('ru;q=invalid, fr'), 'en')

    def test_windows_ui_language_and_posix_message_environment(self):
        with patch.object(localization.sys, 'platform', 'win32'), patch.object(localization, 'windows_language', return_value='ru_RU'):
            self.assertEqual(localization.system_language(), 'ru')
        with patch.object(localization.sys, 'platform', 'linux'), patch.dict(os.environ, {'LC_MESSAGES': 'ru_RU.UTF-8'}, clear=True):
            self.assertEqual(localization.system_language(), 'ru')
        with patch.object(localization.sys, 'platform', 'linux'), patch.dict(os.environ, {'LC_ALL': 'C.UTF-8', 'LANG': 'ru_RU'}, clear=True):
            self.assertEqual(localization.system_language(), 'en')

    def test_saved_choice_overrides_environment_without_model_changes(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(localization, 'system_language', return_value='ru'):
            root = Path(folder)
            self.assertIsNone(localization.saved_language(root))
            self.assertEqual(i18n.load_language(root), 'ru')
            i18n.save_language(root, 'en')
            self.assertEqual(localization.load_language(root), 'en')
            self.assertFalse((root / '.opencode').exists())
            before = (root / localization.PREFERENCES).read_bytes()
            for invalid in ('fr', '', ['ru'], None):
                with self.assertRaises(ValueError):
                    localization.save_language(root, invalid)
                self.assertEqual((root / localization.PREFERENCES).read_bytes(), before)

    def test_catalog_placeholders_and_user_values_are_preserved(self):
        formatter = Formatter()
        for source, translated in localization.catalog().items():
            with self.subTest(source=source):
                fields = lambda value: sorted(field for _, field, _, _ in formatter.parse(value) if field is not None)
                self.assertEqual(fields(source), fields(translated))
        self.assertEqual(localization.text('## 📊 Task report · {title}', 'en', title='Задача {title}'), '## 📊 Task report · Задача {title}')
        self.assertEqual(localization.text('Unregistered message', 'ru'), 'Unregistered message')

    def test_presentation_never_translates_public_messages_titles_or_identifiers(self):
        value = {'title': 'Исполнитель', 'task': 'review', 'control': {'message': 'Основная модель и все связанные исполнители приостановлены.'},
                 'work': {'sessions': {'reason': 'Читаем сессии OpenCode', 'feed': [{'text': 'Нет данных'}]},
                          'items': [{'id': 'Исполнитель'}]}, 'tokens': {'totals': {'input': None}}}
        before = copy.deepcopy(value)
        result = localization.task_presentation(value, 'en')
        self.assertIn('paused', result['control']['message'])
        self.assertEqual(result['work']['sessions']['reason'], 'Reading OpenCode sessions')
        self.assertEqual(result['work']['sessions']['feed'], value['work']['sessions']['feed'])
        self.assertEqual(result['work']['items'], value['work']['items'])
        self.assertEqual(result['title'], 'Исполнитель')
        self.assertIsNone(result['tokens']['totals']['input'])
        self.assertEqual(value, before)

    def test_browser_dictionary_substitution_does_not_translate_or_execute_data(self):
        node = shutil.which('node')
        self.assertIsNotNone(node, 'Node.js is needed for dashboard JavaScript development tests')
        script = r'''
const assert = require('node:assert/strict');
const fs = require('node:fs');
const api = require('./kit/dashboard/static/localization.js');
const catalog = JSON.parse(fs.readFileSync('kit/locales/ru.json', 'utf8'));
assert.equal(api.choose(['de-DE', 'ru-RU']), 'ru');
assert.equal(api.choose(['fr']), 'en');
const ui = api.create(catalog, 'ru');
assert.equal(ui.text('Refresh'), 'Обновить');
const original = '<script>globalThis.changed=true</script> Нет данных {0}';
const tr = ui.template.bind(ui);
assert.equal(tr`Working on function ${original} · ${'a.py'}`, 'Работает над функцией ' + original + ' · a.py');
ui.set('en');
assert.equal(ui.text('Refresh'), 'Refresh');
assert.equal(tr`Working on function ${original} · ${'a.py'}`, 'Working on function ' + original + ' · a.py');
assert.equal(globalThis.changed, undefined);
assert.notEqual((12345).toLocaleString(ui.locale), (12345).toLocaleString('ru-RU'));
'''
        result = subprocess.run([node, '-e', script], cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)


class LocalizedHTTP(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.metrics = TaskMetrics(self.root)
        self.metrics.start('example', title='Моя задача <script>')
        self.server = runtime.DashboardServer(self.root)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .05}, daemon=True)
        self.thread.start()
        self.addCleanup(self.close)

    def close(self):
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()

    def request(self, path, method='GET', value=None, authorized=True, language='en'):
        headers = {'Accept-Language': language}
        body = None
        if value is not None:
            body = json.dumps(value)
            headers['Content-Type'] = 'application/json'
        if authorized:
            headers.update(Origin=f'http://127.0.0.1:{self.server.server_port}', **{'X-Dashboard-UI-Token': self.server.ui_token})
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            return response.status, response.read().decode('utf-8')
        finally:
            connection.close()

    def test_bootstrap_contains_only_catalog_and_saved_choice(self):
        status, body = self.request('/api/i18n')
        self.assertEqual(status, 200)
        value = json.loads(body)
        self.assertEqual(set(value), {'catalog', 'saved_language'})
        self.assertIsNone(value['saved_language'])
        self.assertEqual(value['catalog']['Refresh'], 'Обновить')
        self.assertEqual(self.request('/localization.js')[0], 200)
        self.assertNotIn(self.server.control_token, body)
        self.assertNotIn(self.server.ui_token, body)

    def test_manual_language_save_requires_auth_and_never_changes_events(self):
        journal = self.metrics.task_dir('example') / 'events.jsonl'
        before = journal.read_bytes()
        self.assertEqual(self.request('/api/language', 'POST', {'language': 'ru'}, authorized=False)[0], 403)
        self.assertFalse((self.root / localization.PREFERENCES).exists())
        self.assertEqual(self.request('/api/language', 'POST', {'language': 'ru'})[0], 200)
        self.assertEqual(localization.saved_language(self.root), 'ru')
        self.assertEqual(self.request('/api/language', 'POST', {'language': 'xx'})[0], 400)
        self.assertEqual(self.request('/api/language', 'POST', {'language': 'en', 'path': 'elsewhere'})[0], 400)
        self.assertEqual(localization.saved_language(self.root), 'ru')
        self.assertEqual(journal.read_bytes(), before)
        self.assertFalse((self.root / '.opencode').exists())

    def test_language_changes_generated_fields_but_not_task_title(self):
        for language, expected in [('en', 'The function list for this task has not been published yet'), ('ru', 'Список функций для этой задачи ещё не опубликован')]:
            status, body = self.request('/api/task?task=example', language=language)
            self.assertEqual(status, 200)
            value = json.loads(body)
            self.assertEqual(value['title'], 'Моя задача <script>')
            self.assertEqual(value['work']['progress']['reason'], expected)

    def test_frozen_report_renders_both_languages_without_writing_or_recounting(self):
        self.metrics.append('example', 'test', status='passed', scope='full', tests=3, failures=0, errors=0, skipped=0)
        self.metrics.finish('example', language='ru')
        home = self.metrics.task_dir('example')
        before = {name: (home / name).read_bytes() for name in ('events.jsonl', 'report.md')}
        english = self.request('/api/report?task=example&lang=en')[1]
        russian = self.request('/api/report?task=example&lang=ru')[1]
        self.assertIn('Task report', english)
        self.assertIn('Итоги задачи', russian)
        self.assertIn('tests: 3', english)
        self.assertIn('тестов: 3', russian)
        self.assertIn('Моя задача &lt;script&gt;', english)
        self.assertNotIn('Токены — нет данных', english)
        self.assertEqual(before, {name: (home / name).read_bytes() for name in before})

    def test_document_viewer_localizes_chrome_but_preserves_escaped_source(self):
        (self.root / 'run.py').write_text('print("Не переводить <script>")', encoding='utf-8')
        status, body = self.request('/launch-file?task=example&lang=en')
        self.assertEqual(status, 200)
        self.assertIn('lang="en"', body)
        self.assertIn('Launch file', body)
        self.assertIn('Не переводить &lt;script&gt;', body)
        self.assertNotIn('<script>', body)
