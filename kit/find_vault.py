# -*- coding: utf-8 -*-
"""
find_vault.py — locate Obsidian vaults and notes on this machine.

Seeking db order:
  1. Obsidian's own registry: %APPDATA%/obsidian/obsidian.json
  2. Fallback: scan common roots for directories containing a .obsidian folder.

Usage:
  py find_vault.py
  py find_vault.py --vault "Obsidian Vault"
  py find_vault.py --note "00. План работ.md"
  py find_vault.py --note "00. План работ.md" --json
  py find_vault.py --no-scan          # registry only, fast
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Windows console: cyrillic print correctly.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

VAULT_MARKER = ".obsidian"  

# To ignore
SKIP_DIRS = {
    "node_modules", "appdata", "windows", "program files", "program files (x86)",
    "$recycle.bin", "system volume information", ".git", "venv", ".venv",
    "__pycache__", "site-packages",
}

def path_key_normc_case(path: Path) -> str:
    """Return a normalized comparison key for a path."""
    return os.path.normcase(str(path))


def unique_paths(paths) -> list[Path]:
    visited: set[str] = set()
    result: list[Path] = []
    for path in paths:
        key = path_key_normc_case(path)
        if key not in visited:
            visited.add(key)
            result.append(path)
    return result


def obsidian_config_path() -> Path:
    """
    Returns the path to Obsidian's registry file (obsidian.json).

    Where Obsidian keeps it:
    - Windows: %APPDATA%/obsidian/obsidian.json
    - macOS:   ~/Library/Application Support/obsidian/obsidian.json
    - Linux:   $XDG_CONFIG_HOME/obsidian/obsidian.json, by default ~/.config/obsidian/obsidian.json

    APPDATA is checked first: it is set on Windows, and tests set it to point at a fake registry.
    Returns the path even if the file does not exist; callers check existence.
    """
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "obsidian" / "obsidian.json"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "obsidian" / "obsidian.json"
    config_home = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(config_home) / "obsidian" / "obsidian.json"


def read_obsidian_config(config_path: Path | None = None) -> dict:
    """
    Reads and parses Obsidian's registry JSON.

    Args:
    - config_path: explicit file to read. Defaults to obsidian_config_path().

    Returns:
    - Parsed dict on success.
    - {} if the file is missing, unreadable, invalid JSON, or not a JSON object.
      Never raises.

    Registry shape:
        {"vaults": {"<id>": {"path": "...", "open": true}, ...}}
    """
    path = Path(config_path) if config_path is not None else obsidian_config_path()
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def vaults_from_config(config: dict) -> list[Path]:
    """
    Extracts existing vault directories from a parsed registry.

    Args:
    - config: dict as returned by read_obsidian_config().

    Returns:
    - an absolute paths in registry order,that is not duplicated (case-insensitive).
    - skips entries without a path and folders that do not exist.
    - Returns [X] or [].
    """
    vaults = config.get("vaults", {}) if isinstance(config, dict) else {}
    if not isinstance(vaults, dict):
        return []

    paths = [
        Path(entry["path"])
        for entry in vaults.values()
        if isinstance(entry, dict) and entry.get("path")
    ]
    return unique_paths(path for path in paths if path.is_dir())


def default_scan_roots() -> list[Path]:
    """
    Common places to look for vaults when the registry is missing or empty.

    Returns:
    - Existing directories only: user home, Documents, Desktop, OneDrive and
      its Documents folders, the macOS iCloud folder of Obsidian,
      plus existing drive letters (C:, D:, ...) on Windows.
    """
    home = Path.home()
    candidates = [
        home,
        home / "Documents",
        home / "Desktop",
        home / "OneDrive",
        home / "OneDrive" / "Documents",
        home / "OneDrive" / "Документы",
        # macOS: vaults synced with iCloud live here.
        home / "Library" / "Mobile Documents" / "iCloud~md~obsidian" / "Documents",
    ]
    for letter in "CDEFGH":
        candidates.append(Path(f"{letter}:\\"))
    return [path for path in candidates if path.is_dir()]


def scan_for_vaults(roots=None, max_depth: int = 3) -> list[Path]:
    """
    Fallback discovery: find directories that contain a .obsidian folder.

    Args:
    - roots: iterable of Path to scan. Defaults to default_scan_roots().
    - max_depth: deepest directory level to inspect below each root
      (the root itself is level 0).

    Returns:
    - Paths to vault roots, de-duplicated (case-insensitive), sorted by path.
    - Never raises on permission errors; unreadable areas are skipped.

    Notes:
    - A directory is a vault when it directly contains a `.obsidian` entry.
    - The `.obsidian` folder itself is never descended into.
    - Heavy directories (node_modules, AppData, Windows, ...) are pruned.
    """
    if roots is None:
        roots = default_scan_roots()
    found: list[Path] = []

    for root in roots:
        root = Path(root)
        if not root.is_dir():
            continue
        try:
            for current, dirs, _files in os.walk(root):
                depth = len(Path(current).relative_to(root).parts)

                if VAULT_MARKER in dirs:
                    found.append(Path(current))
                    dirs.remove(VAULT_MARKER)

                if depth >= max_depth:
                    dirs[:] = []
                    continue

                dirs[:] = [
                    name for name in dirs
                    if not name.startswith(".") and name.lower() not in SKIP_DIRS
                ]
        except OSError:
            continue

    return sorted(unique_paths(found))


def list_vaults(config_path: Path | None = None, do_scan: bool = True) -> list[Path]:
    """
    enumerate vaults on this pc.
    Args:
    - config_path: registry file to read (used by tests cases).
    - do_scan: in case we don't find any vaults in the registry.
    Returns:
    - Registry vaults first, then scan-only vaults. with no duplicates.
    """
    vaults = vaults_from_config(read_obsidian_config(config_path))
    if do_scan:
        vaults += scan_for_vaults()
    return unique_paths(vaults)


def filter_vaults(vaults: list[Path], name: str | None) -> list[Path]:
    """
    Filters vaults by a case-insensitive substring of the folder name.
    Args:
    - vaults: list of vault paths.
    - name: substring to match; None or "" returns the input unchanged.
    Returns:
    - copy list with matching vaults.
    """
    if not name:
        return list(vaults)
    needle = name.casefold()
    return [vault for vault in vaults if needle in vault.name.casefold()]


def find_note(note_name: str, vaults=None) -> list[Path]:
    """
    Finds files named note_name inside the given vaults (recursive).
    Args:
    - note_name: file name to match, e.g. "00. План работ.md".
    - vaults: iterable of vault roots..
    Returns:
    - Sorted absolute Paths of matching files. Empty list if none found.
    """
    if vaults is None:
        vaults = list_vaults()
    matches: list[Path] = []
    for vault in vaults:
        vault = Path(vault)
        if not vault.is_dir():
            continue
        try:
            for path in vault.rglob(note_name):
                if path.is_file():
                    matches.append(path)
        except OSError:
            continue
    return sorted(matches)


def build_parser() -> argparse.ArgumentParser:
    """Builds the command-line parser. Kept separate so tests can reuse it."""
    parser = argparse.ArgumentParser(
        prog="find_vault.py",
        description="Locate Obsidian vaults and notes on this machine.",
    )
    parser.add_argument("--vault", help="filter vaults by a name substring")
    parser.add_argument("--note", help="find a note by file name inside the vaults")
    parser.add_argument("--json", action="store_true", help="print JSON instead of plain lines")
    parser.add_argument("--no-scan", action="store_true",
                        help="use only Obsidian's registry, skip the filesystem scan")
    return parser


def print_paths(paths: list[Path], as_json: bool) -> None:
    """Print paths as JSON or one path per line."""
    if as_json:
        print(json.dumps([str(path) for path in paths], ensure_ascii=False, indent=2))
    else:
        for path in paths:
            print(path)


def main(argv=None) -> int:
    """
    CLI entry point.

    Behavior and parameters:
    - No --note: prints vault paths (one per line or a JSON array).
    - With --note: prints matching note paths; exit code 1 if none.
    Returns:
    - 0 on success (at least one result), 1 otherwise.
    """
    args = build_parser().parse_args(argv)
    vaults = filter_vaults(list_vaults(do_scan=not args.no_scan), args.vault)

    if args.note:
        paths = find_note(args.note, vaults)
        empty_message = f"Not found: {args.note}"
    else:
        paths = vaults
        empty_message = "No Obsidian vaults found."

    print_paths(paths, args.json)
    if not paths:
        print(empty_message, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
