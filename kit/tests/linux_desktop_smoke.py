"""Run explicitly inside a Debian container after installing the built .deb."""
import os
from pathlib import Path
import subprocess
import sys
import sysconfig
import tempfile
import tkinter as tk
import unittest

from kit.installer_ui import InstallerWindow
from kit import installer
from kit.configurator import app, workflow


class InstalledLinuxDesktop(unittest.TestCase):
    def test_desktop_bootstrap_runs_gui_child_and_preserves_its_exit_code(self):
        code = 'import tkinter,sys; w=tkinter.Tk(); w.update(); w.after(100,w.destroy); w.mainloop(); sys.exit(7)'
        result = subprocess.run(['sh', '/usr/share/opencode-kit/kit/runtime/desktop.sh', '-c', code],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 7, result.stdout + result.stderr)

    def test_cancel_during_native_preparation_stops_its_child_group(self):
        with tempfile.TemporaryDirectory(prefix='kit-cancel-') as temporary:
            folder = Path(temporary)
            desktop = folder / 'desktop.sh'
            desktop.write_bytes(Path('/usr/share/opencode-kit/kit/runtime/desktop.sh').read_bytes())
            (folder / 'bootstrap.sh').write_text('trap "exit 143" TERM\nsleep 30 &\nwait\n')
            binaries = folder / 'bin'
            binaries.mkdir()
            zenity = binaries / 'zenity'
            zenity.write_text('#!/bin/sh\nsleep 0.3\nexit 1\n')
            zenity.chmod(0o755)
            env = dict(os.environ, PATH=str(binaries) + ':' + os.environ['PATH'])
            result = subprocess.run(['sh', str(desktop)], env=env, capture_output=True, text=True, timeout=8)
            self.assertEqual(result.returncode, 130, result.stdout + result.stderr)

    def test_exact_pinned_runtime_and_relocated_virtual_environment(self):
        source = Path('/usr/share/opencode-kit')
        expected = next(line.split('=')[1] for line in (source / 'kit/runtime/python.lock').read_text().splitlines() if line.startswith('version='))
        self.assertEqual(sys.version.split()[0], expected)
        self.assertEqual(sysconfig.get_config_var('prefix'), sys.base_prefix)
        self.assertTrue(Path(sysconfig.get_config_var('INCLUDEPY')).is_dir())
        self.assertTrue(Path(sysconfig.get_config_var('LIBDIR')).is_dir())
        pip = Path(sys.executable).parent / f'pip{sys.version_info.major}.{sys.version_info.minor}'
        result = subprocess.run([str(pip), '--version'], check=True, capture_output=True, text=True)
        self.assertIn(sys.base_prefix, result.stdout)
        with tempfile.TemporaryDirectory(prefix='kit-runtime-') as temporary:
            environment = Path(temporary) / 'venv with spaces'
            subprocess.run([sys.executable, '-m', 'venv', str(environment)], check=True, capture_output=True)
            python = environment / 'bin/python'
            result = subprocess.run([str(python), '-m', 'pip', '--version'], check=True, capture_output=True, text=True)
            self.assertIn(str(environment), result.stdout)
            # Global shared runtime is not used as the application's environment.
            result = subprocess.run([str(python), '-c', 'import sys;print(sys.prefix)'], check=True, capture_output=True, text=True)
            self.assertEqual(result.stdout.strip(), str(environment))

    def test_package_menu_and_executable_launcher(self):
        subprocess.run(['dpkg-query', '-W', 'opencode-kit'], check=True, capture_output=True)
        subprocess.run(['desktop-file-validate', '/usr/share/applications/opencode-kit.desktop'], check=True)
        self.assertTrue(os.access('/usr/bin/opencode-kit-installer', os.X_OK))

    def test_real_wizard_opens_without_terminal_and_draws_in_both_languages(self):
        window = tk.Tk()
        wizard = InstallerWindow(window, language='en')
        try:
            window.update()
            self.assertTrue(window.winfo_viewable())
            self.assertGreater(window.winfo_width(), 700)
            wizard.language = 'ru'
            wizard.localize()
            window.update()
            self.assertIn('OpenCode', window.title())
        finally:
            wizard.close()

    def test_installed_payload_creates_a_project_and_saves_api_settings_as_user(self):
        self.assertNotEqual(os.getuid(), 0)
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / 'Projects' / 'Дом'
            installer.install_project(Path('/usr/share/opencode-kit'), str(project))
            form = dict(app.EMPTY_FORM, master_chief_source='opencode', master_chief_model='example/chief',
                        exec_source='api', exec_url='https://example.invalid/v1', exec_model='example',
                        exec_key_env='SMOKE_TEST_KEY')
            path, choices = workflow.save(project, form, {'exec': 'synthetic-test-key'})
            os.environ.pop('SMOKE_TEST_KEY')
            self.assertEqual(workflow.existing_key('SMOKE_TEST_KEY'), 'synthetic-test-key')
            self.assertNotIn('synthetic-test-key', path.read_text())
            self.assertTrue((project / 'kit/run_opencode.py').is_file())


if __name__ == '__main__':
    unittest.main()
