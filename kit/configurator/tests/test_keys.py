"""Steps 5-6: keys.py. The Windows registry is replaced with a small fake,
so the tests never touch the real environment and run on any system."""
import os
import unittest
from unittest.mock import patch

from kit.configurator import keys


class FakeKey:
    def __init__(self, store):
        self.store = store

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeWinreg:
    """Just enough of the winreg module for keys.py."""
    HKEY_CURRENT_USER = 'HKCU'
    KEY_SET_VALUE = 2
    REG_SZ = 1

    def __init__(self):
        self.values = {}
        self.opened = []

    def OpenKey(self, root, path, reserved=0, access=0):
        self.opened.append((root, path, access))
        return FakeKey(self.values)

    def QueryValueEx(self, key, name):
        if name not in key.store:
            raise FileNotFoundError(name)
        return key.store[name], self.REG_SZ

    def SetValueEx(self, key, name, reserved, kind, value):
        key.store[name] = value


class Step5Pure(unittest.TestCase):
    def test_valid_names(self):
        for name in ('OCK_MASTER_CHIEF_API_KEY', '_x', 'a1'):
            with self.subTest(name=name):
                self.assertIs(keys.is_valid_env_name(name), True)

    def test_invalid_names(self):
        for name in ('', '1A', 'MY KEY', 'sk-abc', 'KEY\n'):
            with self.subTest(name=name):
                self.assertIs(keys.is_valid_env_name(name), False)

    def test_mask(self):
        self.assertEqual(keys.mask('sk-abcdefgh12345678'), 'sk-a…5678')
        self.assertEqual(keys.mask('123456789'), '1234…6789')
        self.assertEqual(keys.mask('12345678'), '••••')
        self.assertEqual(keys.mask('abc'), '••••')
        self.assertEqual(keys.mask(''), '')


class Step6Registry(unittest.TestCase):
    def setUp(self):
        self.fake = FakeWinreg()
        patcher = patch.object(keys, 'winreg', self.fake)
        patcher.start()
        self.addCleanup(patcher.stop)
        notify = patch.object(keys, 'notify_windows')
        self.notify = notify.start()
        self.addCleanup(notify.stop)
        environment = patch.dict(os.environ, {}, clear=False)
        environment.start()
        self.addCleanup(environment.stop)
        os.environ.pop('KIT_TEST_KEY', None)

    def test_absent_variable_is_none(self):
        self.assertIsNone(keys.read_user_variable('KIT_TEST_KEY'))

    def test_save_writes_registry_and_process_environment(self):
        keys.save_user_variable('KIT_TEST_KEY', 'sk-123')
        self.assertEqual(self.fake.values['KIT_TEST_KEY'], 'sk-123')
        self.assertEqual(os.environ['KIT_TEST_KEY'], 'sk-123')
        self.assertIn(('HKCU', keys.ENVIRONMENT_KEY, self.fake.KEY_SET_VALUE), self.fake.opened)
        self.notify.assert_called_once()

    def test_read_after_save(self):
        keys.save_user_variable('KIT_TEST_KEY', 'sk-123')
        self.assertEqual(keys.read_user_variable('KIT_TEST_KEY'), 'sk-123')

    def test_save_rejects_bad_input_and_writes_nothing(self):
        for name, value in (('sk-oops', 'value'), ('KIT_TEST_KEY', '')):
            with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                keys.save_user_variable(name, value)
        self.assertEqual(self.fake.values, {})
        self.notify.assert_not_called()

    def test_key_is_set_from_environment_or_registry(self):
        self.assertFalse(keys.key_is_set('KIT_TEST_KEY'))
        self.fake.values['KIT_TEST_KEY'] = 'from-registry'
        self.assertTrue(keys.key_is_set('KIT_TEST_KEY'))
        self.fake.values.clear()
        os.environ['KIT_TEST_KEY'] = 'from-process'
        self.assertTrue(keys.key_is_set('KIT_TEST_KEY'))

    def test_empty_value_does_not_count(self):
        self.fake.values['KIT_TEST_KEY'] = ''
        self.assertFalse(keys.key_is_set('KIT_TEST_KEY'))


if __name__ == '__main__':
    unittest.main()
