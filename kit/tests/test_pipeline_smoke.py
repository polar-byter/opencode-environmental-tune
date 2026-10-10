# -*- coding: utf-8 -*-
"""test_pipeline_smoke.py — unit tests for pipeline_smoke.py.

Only the pure parts are tested (config parsing, model resolution, markdown
stripping). The network part is exercised by running the script manually.
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pipeline_smoke
from lmstudio_models import LoadedModel


SAMPLE_CONFIG = {
    "agents": {"executor": {"model": "lmstudio/qwen3-27b-coder"}},
    "providers": {
        "lmstudio": {
            "models": {
                "qwen3-27b-coder": {"modelID": "qwen3.8-27b-real-name"},
            }
        }
    },
}


class TempCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)


class TestLoadConfig(TempCase):
    def test_missing_file_returns_empty(self):
        self.assertEqual(pipeline_smoke.load_config(self.root / "nope.jsonc"), {})

    def test_invalid_json_returns_empty(self):
        bad = self.root / "bad.jsonc"
        bad.write_text("{not json", encoding="utf-8")
        self.assertEqual(pipeline_smoke.load_config(bad), {})

    def test_jsonc_with_comments_is_parsed(self):
        good = self.root / "good.jsonc"
        good.write_text('{\n  // comment\n  "model": "x",\n}\n', encoding="utf-8")
        self.assertEqual(pipeline_smoke.load_config(good), {"model": "x"})


class TestResolveExecutorModel(unittest.TestCase):
    def test_maps_alias_to_real_model_id(self):
        self.assertEqual(
            pipeline_smoke.resolve_executor_model(SAMPLE_CONFIG),
            "qwen3.8-27b-real-name",
        )

    def test_override_wins(self):
        self.assertEqual(
            pipeline_smoke.resolve_executor_model(SAMPLE_CONFIG, "spark-x2.5-4b"),
            "spark-x2.5-4b",
        )

    def test_non_lmstudio_provider_returns_none(self):
        config = {"agents": {"executor": {"model": "opencode-go/deepseek-v4.1-flash"}}}
        self.assertIsNone(pipeline_smoke.resolve_executor_model(config))

    def test_missing_executor_returns_none(self):
        self.assertIsNone(pipeline_smoke.resolve_executor_model({}))

    def test_unknown_alias_returns_alias(self):
        config = {"agents": {"executor": {"model": "lmstudio/unknown-model"}}}
        self.assertEqual(
            pipeline_smoke.resolve_executor_model(config), "unknown-model"
        )

    def test_model_without_provider_prefix_returned_as_is(self):
        config = {"agents": {"executor": {"model": "plain-model"}}}
        self.assertEqual(pipeline_smoke.resolve_executor_model(config), "plain-model")


class TestStripMarkdown(unittest.TestCase):
    def test_removes_python_fence(self):
        raw = "```python\ndef f():\n    return 1\n```"
        self.assertEqual(pipeline_smoke.strip_markdown(raw), "def f():\n    return 1")

    def test_keeps_plain_code(self):
        self.assertEqual(pipeline_smoke.strip_markdown("def f(): pass"), "def f(): pass")

    def test_removes_bare_fence(self):
        raw = "```\ncode\n```"
        self.assertEqual(pipeline_smoke.strip_markdown(raw), "code")


class TestMainWorkdir(TempCase):
    def test_default_removes_workdir_even_on_error(self):
        created = []
        def run(workdir, model, base):
            self.assertTrue(workdir.is_dir())
            created.append(workdir)
            raise RuntimeError('smoke failed')
        with patch.object(pipeline_smoke, 'load_config', return_value=SAMPLE_CONFIG), \
             patch.object(pipeline_smoke, 'loaded_models', return_value=[LoadedModel('qwen3.8-27b-real-name', 'qwen3.8-27b-real-name', 'Qwen')]), \
             patch.object(pipeline_smoke, 'run_smoke', side_effect=run):
            with self.assertRaises(RuntimeError):
                pipeline_smoke.main([])
        self.assertFalse(created[0].exists())

    def test_keep_preserves_workdir(self):
        workdir = self.root / 'kept'
        workdir.mkdir()
        with patch.object(pipeline_smoke, 'load_config', return_value=SAMPLE_CONFIG), \
             patch.object(pipeline_smoke, 'loaded_models', return_value=[LoadedModel('qwen3.8-27b-real-name', 'qwen3.8-27b-real-name', 'Qwen')]), \
             patch.object(pipeline_smoke.tempfile, 'mkdtemp', return_value=str(workdir)), \
             patch.object(pipeline_smoke, 'run_smoke', return_value=1) as run:
            self.assertEqual(pipeline_smoke.main(['--keep']), 1)
        run.assert_called_once_with(workdir, 'qwen3.8-27b-real-name', pipeline_smoke.LMSTUDIO_BASE)
        self.assertTrue(workdir.is_dir())


class TestSkeletons(unittest.TestCase):
    def test_skeleton_has_spec_and_placeholder(self):
        skeleton = pipeline_smoke.master_chief_skeleton_app()
        self.assertIn("Spec:", skeleton)
        self.assertIn("NotImplementedError", skeleton)
        self.assertIn("def percent", skeleton)
        self.assertIn("def discount", skeleton)

    def test_tests_skeleton_imports_both_functions(self):
        tests = pipeline_smoke.master_chief_skeleton_tests()
        self.assertIn("from calculator import percent, discount", tests)


if __name__ == "__main__":
    unittest.main(verbosity=2)
