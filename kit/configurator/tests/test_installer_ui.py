"""Real Tk wizard state transitions; no provider calls or Desktop launch."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

from kit import installer, installer_ui
from kit.configurator import desktop


class InstallerWindowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.window = installer_ui.tk.Tk()
        self.window.withdraw()
        self.found = installer.Desktop(self.root / 'OpenCode.exe', self.root / 'opencode-cli.exe')
        with patch.object(installer_ui.installer, 'find_desktop', return_value=self.found):
            self.ui = installer_ui.InstallerWindow(self.window, language='ru')
        self.addCleanup(lambda: self.ui.close() if not self.ui.closed else None)

    def test_missing_desktop_blocks_install_and_explains_the_next_action(self):
        with patch.object(installer_ui.installer, 'find_desktop', return_value=None):
            self.ui.refresh_desktop()
        self.assertIn('disabled', self.ui.primary.state())
        self.assertIn('Desktop', self.ui.desktop_status.cget('text'))
        with patch.object(installer_ui.installer, 'find_desktop', return_value=self.found):
            self.ui.refresh_desktop()
        self.assertNotIn('disabled', self.ui.primary.state())

    def test_language_switch_keeps_custom_path_and_prompt(self):
        self.ui.path.set(str(self.root / 'Мой проект'))
        self.ui.prompt.delete('1.0', 'end')
        self.ui.prompt.insert('1.0', 'My own task')
        self.ui.language_choice.set('English')
        self.ui.change_language()
        self.assertEqual(self.ui.path.get(), str(self.root / 'Мой проект'))
        self.assertEqual(self.ui.prompt.get('1.0', 'end-1c'), 'My own task')
        self.assertEqual(self.ui.primary.cget('text'), 'Create project and configure models')

    def test_preparation_enables_open_and_optionally_requests_desktop(self):
        self.ui.project = self.root
        self.ui.configuration = Mock(preparing=False)
        with patch.object(installer_ui.installer, 'open_project') as open_project:
            self.ui.configured()
        self.ui.configuration.close.assert_called_once()
        open_project.assert_called_once_with(self.found, self.root)
        self.assertTrue(self.ui.prepared)
        self.assertIn('OpenCode', self.ui.primary.cget('text'))

    def test_disabling_auto_open_keeps_user_in_control(self):
        self.ui.project = self.root
        self.ui.configuration = Mock(preparing=False)
        self.ui.auto_open.set(False)
        with patch.object(installer_ui.installer, 'open_project') as open_project:
            self.ui.configured()
        open_project.assert_not_called()

    def test_close_during_copy_is_rejected_without_destroying_the_window(self):
        self.ui.busy = True
        self.ui.close()
        self.assertFalse(self.ui.closed)
        self.ui.busy = False

    def test_primary_and_footer_fit_at_minimum_size_in_both_languages(self):
        self.window.deiconify()
        self.window.geometry('740x740')
        for language in ('en', 'ru'):
            self.ui.language = language
            self.ui.localize()
            self.window.update()
            for widget in (self.ui.primary, self.ui.settings_button):
                self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(), self.window.winfo_rooty() + self.window.winfo_height())


if __name__ == '__main__':
    unittest.main()
