"""Explicit Windows integration checks, using a real private pinned runtime."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from kit.installer import install_project

ROOT = Path(__file__).resolve().parents[2]


class WindowsRuntimeSmoke(unittest.TestCase):
    def setUp(self):
        self.command = ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                        str(ROOT / 'kit/runtime/bootstrap.ps1')]

    def test_real_runtime_version_tk_arguments_and_cache_reuse(self):
        probe = ('import sys,json,tkinter,ssl,sqlite3; root=tkinter.Tk(); '
                 'root.withdraw(); root.destroy(); '
                 'print(json.dumps({"version":sys.version.split()[0],"args":sys.argv[1:]},ensure_ascii=True))')
        result = subprocess.run(self.command + ['-c', probe, 'Дом с пробелами', 'a&b'],
                                text=True, encoding='utf-8', capture_output=True, timeout=600)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        expected = next(line.split('=')[1] for line in (ROOT / 'kit/runtime/python.lock').read_text().splitlines() if line.startswith('version='))
        self.assertEqual(json.loads(result.stdout.splitlines()[-1]), {'version': expected, 'args': ['Дом с пробелами', 'a&b']})
        result = subprocess.run(self.command + ['--kit-runtime-path'], text=True, encoding='utf-8', capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(Path(result.stdout.strip()).is_file())
        self.assertNotIn('preparing', result.stdout)

    def test_copied_project_batch_entry_and_child_exit(self):
        with tempfile.TemporaryDirectory(prefix='kit-entry-') as temporary:
            project = Path(temporary) / 'Новый проект'
            install_project(ROOT, str(project))
            probe = project / 'probe.py'
            probe.write_text('import json,sys,subprocess\n'
                             'print(json.dumps(sys.argv[1:],ensure_ascii=True))\n'
                             'child=subprocess.run([sys.executable,"-c","import sys;sys.exit(7)"])\n'
                             'raise SystemExit(child.returncode)\n', encoding='utf-8')
            result = subprocess.run([str(project / 'kit/python.cmd'), str(probe), 'one two', 'Дом & бюджет'],
                                    text=True, encoding='utf-8', capture_output=True, timeout=45)
            self.assertEqual(result.returncode, 7, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout.strip()), ['one two', 'Дом & бюджет'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
