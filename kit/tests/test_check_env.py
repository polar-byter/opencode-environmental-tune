# -*- coding: utf-8 -*-
"""test_check_env.py — unit tests for check_env.strip_jsonc.

These tests pin the behavior of the JSONC cleaner: comments are removed,
but "//" inside strings must survive.
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import check_env


class TestStripJsonc(unittest.TestCase):
    def test_removes_line_comment(self):
        out = check_env.strip_jsonc('{\n  "a": 1 // comment\n}')
        self.assertEqual(json.loads(out), {"a": 1})

    def test_keeps_double_slash_inside_string(self):
        out = check_env.strip_jsonc('{"url": "http://example.com//x"}')
        self.assertEqual(json.loads(out), {"url": "http://example.com//x"})

    def test_removes_trailing_comma_before_brace(self):
        out = check_env.strip_jsonc('{"a": 1,}')
        self.assertEqual(json.loads(out), {"a": 1})

    def test_removes_trailing_comma_before_bracket(self):
        out = check_env.strip_jsonc('{"a": [1, 2,]}')
        self.assertEqual(json.loads(out), {"a": [1, 2]})

    def test_removes_block_comment(self):
        out = check_env.strip_jsonc('{"a": 1 /* c */ }')
        self.assertEqual(json.loads(out), {"a": 1})

    def test_removes_block_comment_across_lines(self):
        out = check_env.strip_jsonc('{\n  /* one\n  two */\n  "a": 1\n}')
        self.assertEqual(json.loads(out), {"a": 1})

    def test_keeps_escaped_quote_in_string(self):
        out = check_env.strip_jsonc('{"a": "he said \\"hi\\""}')
        self.assertEqual(json.loads(out), {"a": 'he said "hi"'})

    def test_comment_after_value_on_same_line(self):
        out = check_env.strip_jsonc('{\n "model": "x", // Master Chief\n "a": 1\n}')
        self.assertEqual(json.loads(out), {"model": "x", "a": 1})

    def test_real_config_parses(self):
        config = check_env.CONFIG_PATH
        if not config.exists():
            self.skipTest("opencode.jsonc not found")
        data = json.loads(check_env.strip_jsonc(config.read_text(encoding="utf-8")))
        self.assertIn("agents", data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
