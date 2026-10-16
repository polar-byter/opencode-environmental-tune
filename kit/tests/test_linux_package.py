"""Debian payload isolation, launcher permissions and portable API key storage."""
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from kit import installer, linux_package
from kit.configurator import keys, posix_keys, workflow


def members(data):
    assert data[:8] == b'!<arch>\n'
    result, offset = {}, 8
    while offset < len(data):
        header = data[offset:offset + 60]
        assert header[-2:] == b'`\n'
        size = int(header[48:58])
        result[header[:16].decode().strip().rstrip('/')] = data[offset + 60:offset + 60 + size]
        offset += 60 + size + size % 2
    return result


class LinuxPackageTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.source = self.root / 'source'
        self.source.mkdir()
        for name in (*installer.ROOT_FILES, 'install.py', 'LICENSE', 'kit/installer_ui.py',
                     'kit/configurator/assets/app-256.png', '.opencode/commands/module.md', 'docs/guide.md'):
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'public template')
        for name in ('.metrics/task/events.jsonl', '.opencode/kit-models.json', 'kit/.env', 'kit/credentials.json'):
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'private secret')

    def test_package_has_native_menu_launcher_dependencies_and_no_local_secrets(self):
        output = linux_package.build(self.source, self.root / 'kit.deb')
        parts = members(output.read_bytes())
        self.assertEqual(list(parts), ['debian-binary', 'control.tar.gz', 'data.tar.gz'])
        self.assertEqual(parts['debian-binary'], b'2.0\n')
        with tarfile.open(fileobj=io.BytesIO(parts['control.tar.gz']), mode='r:gz') as archive:
            control = archive.extractfile('control').read().decode()
            self.assertIn('Architecture: all', control)
            self.assertIn('python3 (>= 3.10), python3-tk, xdg-utils', control)
        with tarfile.open(fileobj=io.BytesIO(parts['data.tar.gz']), mode='r:gz') as archive:
            launcher = archive.getmember('usr/bin/opencode-kit-installer')
            self.assertEqual(launcher.mode, 0o755)
            self.assertEqual((launcher.uid, launcher.gid), (0, 0))
            self.assertEqual(archive.extractfile(launcher).read(), linux_package.LAUNCHER)
            self.assertIn('Terminal=false', archive.extractfile('usr/share/applications/opencode-kit.desktop').read().decode())
            self.assertIn('usr/share/opencode-kit/install.py', archive.getnames())
            for member in archive:
                self.assertFalse(member.issym() or member.islnk())
                if member.isfile():
                    self.assertNotIn(b'private secret', archive.extractfile(member).read())

    def test_build_is_reproducible_and_rejects_invalid_version(self):
        first = linux_package.build(self.source, self.root / 'a.deb').read_bytes()
        second = linux_package.build(self.source, self.root / 'b.deb').read_bytes()
        self.assertEqual(first, second)
        for version in ('', '../oops', '1\nDepends: bad', 'latest'):
            with self.assertRaises(ValueError):
                linux_package.build(self.source, self.root / 'invalid.deb', version)
        self.assertFalse((self.root / 'invalid.deb').exists())


class PosixKeysTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        for context in (patch.dict(os.environ, {'XDG_CONFIG_HOME': str(self.root / 'config')}, clear=True),
                        patch.object(keys, 'winreg', None)):
            context.start()
            self.addCleanup(context.stop)

    def test_key_survives_a_fresh_process_environment_outside_the_project(self):
        keys.save_user_variable('TEST_API_KEY', 'synthetic-test-key')
        keys.save_user_variable('OTHER_API_KEY', 'another-test-key')
        os.environ.pop('TEST_API_KEY')
        self.assertEqual(workflow.existing_key('TEST_API_KEY'), 'synthetic-test-key')
        self.assertEqual(keys.read_user_variable('OTHER_API_KEY'), 'another-test-key')
        self.assertEqual(json.loads(posix_keys.location().read_text())['TEST_API_KEY'], 'synthetic-test-key')
        if os.name == 'posix':
            self.assertEqual(posix_keys.location().stat().st_mode & 0o777, 0o600)
            self.assertEqual(posix_keys.location().parent.stat().st_mode & 0o777, 0o700)

    def test_invalid_key_name_does_not_create_a_store_and_corrupt_store_is_preserved(self):
        with self.assertRaises(ValueError):
            keys.save_user_variable('../TEST', 'value')
        self.assertFalse(posix_keys.location().exists())
        keys.save_user_variable('TEST_API_KEY', 'synthetic-test-key')
        path = posix_keys.location()
        path.write_text('{broken', encoding='utf-8')
        with self.assertRaises(ValueError):
            keys.save_user_variable('TEST_API_KEY', 'replacement')
        self.assertEqual(path.read_text(), '{broken')

    def test_shared_permissions_are_rejected_on_posix(self):
        if os.name != 'posix':
            # Windows CI verifies the same validation using POSIX stat metadata.
            with patch.object(posix_keys.os, 'name', 'posix'), patch.object(posix_keys.os, 'getuid', return_value=123, create=True):
                fake = unittest.mock.Mock()
                fake.stat.return_value = unittest.mock.Mock(st_uid=123, st_mode=0o644)
                with self.assertRaises(PermissionError):
                    posix_keys.private(fake)
            return
        keys.save_user_variable('TEST_API_KEY', 'synthetic-test-key')
        path = posix_keys.location()
        path.chmod(0o644)
        with self.assertRaises(PermissionError):
            workflow.existing_key('TEST_API_KEY')
        path.chmod(0o600)
