"""Run explicitly inside a Debian container after installing the built .deb."""
import os
from pathlib import Path
import subprocess
import tempfile
import tkinter as tk
import unittest

from kit.installer_ui import InstallerWindow
from kit import installer
from kit.configurator import app, workflow


class InstalledLinuxDesktop(unittest.TestCase):
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
