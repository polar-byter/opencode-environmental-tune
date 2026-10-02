# -*- coding: utf-8 -*-
"""test_find_vault.py — unit tests for find_vault.py.

All tests use temporary directories, so they never depend on the real machine
or on a real Obsidian installation.
"""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

# find_vault.py lives in the project root, tests in tests/.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import find_vault


class TempCase(unittest.TestCase):
    """Base class: gives every test a fresh temporary directory."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def make_vault(self, name="Vault"):
        vault = self.root / name
        (vault / find_vault.VAULT_MARKER).mkdir(parents=True)
        return vault


class TestReadConfig(TempCase):
    def test_missing_file_returns_empty_dict(self):
        self.assertEqual(find_vault.read_obsidian_config(self.root / "nope.json"), {})

    def test_invalid_json_returns_empty_dict(self):
        bad = self.root / "bad.json"
        bad.write_text("{not valid json", encoding="utf-8")
        self.assertEqual(find_vault.read_obsidian_config(bad), {})

    def test_valid_json_is_parsed(self):
        good = self.root / "good.json"
        good.write_text(json.dumps({"vaults": {"a": {"path": str(self.root)}}}), encoding="utf-8")
        self.assertIn("vaults", find_vault.read_obsidian_config(good))

    def test_non_object_json_returns_empty_dict(self):
        arr = self.root / "arr.json"
        arr.write_text("[1, 2, 3]", encoding="utf-8")
        self.assertEqual(find_vault.read_obsidian_config(arr), {})


class TestVaultsFromConfig(TempCase):
    def test_keeps_existing_and_skips_missing(self):
        real = self.root / "vaultA"
        real.mkdir()
        config = {"vaults": {
            "1": {"path": str(real)},
            "2": {"path": str(self.root / "ghost")},
            "3": {},
        }}
        self.assertEqual(find_vault.vaults_from_config(config), [real])

    def test_deduplicates(self):
        real = self.root / "vaultA"
        real.mkdir()
        config = {"vaults": {"1": {"path": str(real)}, "2": {"path": str(real)}}}
        self.assertEqual(find_vault.vaults_from_config(config), [real])

    def test_malformed_config_returns_empty(self):
        self.assertEqual(find_vault.vaults_from_config({"vaults": "oops"}), [])


class TestScan(TempCase):
    def test_finds_vault_under_root(self):
        vault = self.make_vault("MyVault")
        found = find_vault.scan_for_vaults(roots=[self.root], max_depth=3)
        self.assertIn(vault, found)

    def test_does_not_descend_below_max_depth(self):
        deep = self.root / "a" / "b" / "c" / "Vault"
        (deep / find_vault.VAULT_MARKER).mkdir(parents=True)
        found = find_vault.scan_for_vaults(roots=[self.root], max_depth=2)
        self.assertNotIn(deep, found)

    def test_root_itself_can_be_a_vault(self):
        (self.root / find_vault.VAULT_MARKER).mkdir()
        found = find_vault.scan_for_vaults(roots=[self.root], max_depth=1)
        self.assertIn(self.root, found)

    def test_ignores_non_vault_dirs(self):
        (self.root / "just_a_folder").mkdir()
        found = find_vault.scan_for_vaults(roots=[self.root], max_depth=3)
        self.assertEqual(found, [])


class TestFilterVaults(TempCase):
    def test_case_insensitive_substring(self):
        vaults = [Path("C:/x/Obsidian Vault"), Path("C:/y/Other")]
        self.assertEqual(find_vault.filter_vaults(vaults, "obsidian"), [vaults[0]])

    def test_none_returns_copy(self):
        vaults = [Path("C:/x/A")]
        result = find_vault.filter_vaults(vaults, None)
        self.assertEqual(result, vaults)
        self.assertIsNot(result, vaults)


class TestFindNote(TempCase):
    def test_finds_nested_note(self):
        vault = self.make_vault("Vault")
        note = vault / "sub" / "00. План работ.md"
        note.parent.mkdir()
        note.write_text("x", encoding="utf-8")
        self.assertEqual(find_vault.find_note("00. План работ.md", [vault]), [note])

    def test_missing_note_returns_empty(self):
        vault = self.make_vault("Vault")
        self.assertEqual(find_vault.find_note("nope.md", [vault]), [])

    def test_skips_missing_vault_dir(self):
        self.assertEqual(find_vault.find_note("x.md", [self.root / "ghost"]), [])


class TestMain(TempCase):
    def setUp(self):
        super().setUp()
        self.vault = self.make_vault("Vault")
        note = self.vault / "00. План работ.md"
        note.write_text("x", encoding="utf-8")
        self.note = note

        appdata = self.root / "appdata"
        (appdata / "obsidian").mkdir(parents=True)
        (appdata / "obsidian" / "obsidian.json").write_text(
            json.dumps({"vaults": {"1": {"path": str(self.vault)}}}),
            encoding="utf-8",
        )
        self._old_appdata = os.environ.get("APPDATA")
        os.environ["APPDATA"] = str(appdata)
        self.addCleanup(self._restore_appdata)

    def _restore_appdata(self):
        if self._old_appdata is None:
            os.environ.pop("APPDATA", None)
        else:
            os.environ["APPDATA"] = self._old_appdata

    def test_lists_vaults(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = find_vault.main(["--no-scan"])
        self.assertEqual(code, 0)
        self.assertIn(str(self.vault), out.getvalue())

    def test_finds_note_and_returns_zero(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = find_vault.main(["--note", "00. План работ.md", "--no-scan"])
        self.assertEqual(code, 0)
        self.assertIn(str(self.note), out.getvalue())

    def test_missing_note_returns_one(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = find_vault.main(["--note", "nope.md", "--no-scan"])
        self.assertEqual(code, 1)

    def test_json_output(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = find_vault.main(["--note", "00. План работ.md", "--no-scan", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.getvalue()), [str(self.note)])


if __name__ == "__main__":
    unittest.main(verbosity=2)
