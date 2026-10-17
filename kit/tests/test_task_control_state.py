"""plain_path accepts ordinary folders under any spelling and rejects links anywhere in the path."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from kit.task_control_state import plain_path


def short_name(path: Path) -> Path | None:
    """Return the Windows 8.3 form of an existing path, or None when the volume has no short names."""
    if sys.platform != 'win32':
        return None
    import ctypes
    buffer = ctypes.create_unicode_buffer(32768)
    if not ctypes.windll.kernel32.GetShortPathNameW(str(path), buffer, len(buffer)):
        return None
    return Path(buffer.value) if buffer.value != str(path) else None


class PlainPathTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()

    def test_regular_folder_and_missing_file_are_accepted(self):
        folder = self.root / 'project'
        folder.mkdir()
        self.assertEqual(plain_path(folder), folder)
        self.assertEqual(plain_path(folder / 'missing' / 'state.json'), folder / 'missing' / 'state.json')

    def test_path_that_resolves_to_another_spelling_is_accepted(self):
        # Simulates C:\Users\RUNNER~1\... whose resolve() expands to the long name.
        folder = self.root / 'RUNNER~1'
        folder.mkdir()
        with patch.object(Path, 'resolve', return_value=self.root / 'runneradmin'):
            self.assertEqual(plain_path(folder), folder)

    def test_real_short_name_is_accepted(self):
        folder = self.root / 'a folder with a long name'
        folder.mkdir()
        short = short_name(folder)
        if short is None:
            self.skipTest('8.3 short names are not available on this volume')
        self.assertEqual(plain_path(short / 'state.json'), short / 'state.json')

    def test_parent_directory_reference_is_rejected(self):
        with self.assertRaises(ValueError):
            plain_path(self.root / 'a' / '..' / 'b')

    def test_symlink_anywhere_in_the_path_is_rejected(self):
        target = self.root / 'target'
        target.mkdir()
        link = self.root / 'link'
        try:
            link.symlink_to(target, target_is_directory=True)
        except OSError:
            self.skipTest('Creating symlinks needs a privilege on this system')
        for path in (link, link / 'state.json', link / 'missing' / 'state.json'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                plain_path(path)

    @unittest.skipUnless(sys.platform == 'win32', 'Junctions exist only on Windows')
    def test_junction_anywhere_in_the_path_is_rejected(self):
        target = self.root / 'target'
        target.mkdir()
        junction = self.root / 'junction'
        subprocess.run(['cmd', '/c', 'mklink', '/J', str(junction), str(target)],
                       check=True, capture_output=True, env=os.environ)
        for path in (junction, junction / 'state.json'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                plain_path(path)


if __name__ == '__main__':
    unittest.main()
