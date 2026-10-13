"""Run the current JavaScript exercise without a browser or a live server."""
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest


class InlineScripts(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.in_script = False
        self.parts = []
        self.ids = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'script':
            self.in_script = not attrs.get('src')

    def handle_endtag(self, tag):
        if tag == 'script':
            self.in_script = False

    def handle_data(self, data):
        if self.in_script:
            self.parts.append(data)


class PageChecks(unittest.TestCase):
    def check_scenario(self, scenario):
        node = os.environ.get('DASHBOARD_TEST_NODE') or shutil.which('node')
        self.assertIsNotNone(
            node, 'JavaScript checks need node on PATH or DASHBOARD_TEST_NODE.',
        )
        folder = Path(__file__).resolve().parent
        parser = InlineScripts()
        parser.feed((folder.parent / 'static' / 'simple.html').read_text(encoding='utf-8'))
        result = subprocess.run(
            [node, str(folder / 'simple_page_checks.js')],
            input=json.dumps({
                'source': ''.join(parser.parts), 'scenario': scenario, 'ids': parser.ids,
            }),
            text=True, encoding='utf-8', capture_output=True, timeout=5,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class Iteration3LoadTask(PageChecks):
    def test_success_returns_parsed_summary(self):
        self.check_scenario('success')

    def test_http_400_raises_server_error_message(self):
        self.check_scenario('http400')

    def test_http_500_raises_server_error_message(self):
        self.check_scenario('http500')

    def test_network_error_is_not_hidden(self):
        self.check_scenario('network')

    def test_invalid_json_error_is_not_hidden(self):
        self.check_scenario('json')

    def test_each_call_fetches_fresh_summary(self):
        self.check_scenario('fresh')


class Iteration3RenderTask(PageChecks):
    def test_displays_all_fields_and_finished_status(self):
        self.check_scenario('render_fields')

    def test_displays_running_status(self):
        self.check_scenario('render_running')

    def test_displays_halted_status(self):
        self.check_scenario('render_halted')

    def test_zero_counts_are_displayed_as_zero(self):
        self.check_scenario('render_zero')

    def test_title_is_literal_text_not_html(self):
        self.check_scenario('render_literal')

    def test_next_call_replaces_old_values_without_changing_data(self):
        self.check_scenario('render_repeat')
