"""Tests for opencode_cli.py: the same OpenCode search order in every kit script.

A temporary folder plays LOCALAPPDATA and shutil.which is replaced, so the real
OpenCode installations on the machine do not matter.
"""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import opencode_cli
import run_opencode
import task_metrics


class OpencodeSearchOrder(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.local = Path(self.temp.name)
        self.desktop = self.local / opencode_cli.DESKTOP_CLI
        env = patch.dict(os.environ, {'LOCALAPPDATA': str(self.local)})
        env.start()
        self.addCleanup(env.stop)

    def install_desktop(self):
        self.desktop.parent.mkdir(parents=True)
        self.desktop.write_text('')

    def on_path(self, mapping):
        """Replace shutil.which with a lookup in a {command: path} dictionary."""
        return patch('shutil.which', side_effect=lambda name: mapping.get(name))

    def test_desktop_wins_over_native_cli_on_path(self):
        self.install_desktop()
        with self.on_path({'opencode': r'C:\old\opencode.exe'}):
            self.assertEqual(opencode_cli.locate_opencode(), str(self.desktop))
            self.assertEqual(run_opencode.find_opencode('opencode'), str(self.desktop))
            self.assertEqual(task_metrics.resolve_opencode('opencode'), str(self.desktop))

    def test_native_cli_on_path_without_desktop(self):
        with self.on_path({'opencode': '/usr/local/bin/opencode'}):
            self.assertEqual(run_opencode.find_opencode('opencode'), '/usr/local/bin/opencode')
            self.assertEqual(task_metrics.resolve_opencode('opencode'), '/usr/local/bin/opencode')

    def test_explicit_command_wins_over_desktop(self):
        self.install_desktop()
        with self.on_path({r'D:\tools\opencode.exe': r'D:\tools\opencode.exe'}):
            self.assertEqual(run_opencode.find_opencode(r'D:\tools\opencode.exe'), r'D:\tools\opencode.exe')
            self.assertEqual(task_metrics.resolve_opencode(r'D:\tools\opencode.exe'), r'D:\tools\opencode.exe')

    def test_wrapper_on_path_is_skipped_by_the_search(self):
        with self.on_path({'opencode': r'C:\npm\opencode.cmd'}):
            self.assertIsNone(opencode_cli.locate_opencode())
            with self.assertRaisesRegex(ValueError, 'not found'):
                run_opencode.find_opencode('opencode')
            # Reading exports works through a wrapper, so metrics keep it as the last resort.
            self.assertEqual(task_metrics.resolve_opencode('opencode'), r'C:\npm\opencode.cmd')

    def test_explicit_wrapper_is_rejected_by_the_launcher(self):
        with self.on_path({'opencode2': r'C:\npm\opencode2.cmd'}):
            with self.assertRaisesRegex(ValueError, 'wrappers are not supported'):
                run_opencode.find_opencode('opencode2')

    def test_nothing_found(self):
        with self.on_path({}):
            with self.assertRaisesRegex(ValueError, 'not found'):
                run_opencode.find_opencode('opencode')
            self.assertEqual(task_metrics.resolve_opencode('opencode'), 'opencode')

    def test_no_localappdata_means_no_desktop(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(opencode_cli.desktop_cli())


if __name__ == '__main__':
    unittest.main()
