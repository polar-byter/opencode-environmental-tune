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

    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            self.in_script = not dict(attrs).get('src')

    def handle_endtag(self, tag):
        if tag == 'script':
            self.in_script = False

    def handle_data(self, data):
        if self.in_script:
            self.parts.append(data)


class Iteration3LoadTask(unittest.TestCase):
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
            input=json.dumps({'source': ''.join(parser.parts), 'scenario': scenario}),
            text=True, encoding='utf-8', capture_output=True, timeout=5,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

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
