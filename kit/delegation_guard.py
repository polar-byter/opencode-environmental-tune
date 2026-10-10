"""Content snapshots for executor edits, including new and Git-ignored source files."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

# Generated directories only. Source code must not be placed in these directories.
GENERATED = {'.git', '.metrics', '__pycache__', '.venv', 'node_modules', 'target', 'build', 'dist', 'bin', 'obj'}


def source_path(root: Path, name: str) -> str:
    """Require a project-relative regular source file outside generated directories."""
    path = Path(name)
    if path.anchor or '..' in path.parts or not path.parts or any(p in GENERATED for p in path.parts):
        raise ValueError('Delegated files must be project-relative source files')
    target = root / path
    if (not target.resolve().is_relative_to(root) or
            target.resolve() != target.absolute() or not target.is_file()):
        raise ValueError('Delegated file must exist and must not be a symlink or junction')
    return path.as_posix()


def snapshot(root: Path) -> dict[str, str]:
    """Hash files outside excluded directories, regardless of Git ignore rules.

    These hashes allow later comparison; they do not prevent or restore edits.
    """
    files = {}
    for current, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in GENERATED)
        for name in dirs + names:
            path = Path(current) / name
            if path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
                raise ValueError(f'Snapshot cannot follow a symlink or junction: {path}')
        for name in sorted(names):
            path = Path(current) / name
            files[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def compare(before: dict[str, str], after: dict[str, str], allowed: list[str]) -> dict:
    """Detect added, removed and modified files; never revert user files automatically."""
    changed = sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))
    return dict(changed=changed, unexpected=[p for p in changed if p not in allowed])


def review_checks(path: Path) -> list[dict]:
    """Require explicit requirement/code/test evidence; correctness remains reviewer judgement."""
    import json
    # utf-8-sig also accepts a BOM: PowerShell writes UTF-8 files with one by default.
    checks = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(checks, list) or not checks:
        raise ValueError('Review checks must be a non-empty JSON list')
    for item in checks:
        if (not isinstance(item, dict) or item.get('verified') is not True or
                any(not isinstance(item.get(k), str) or not item[k].strip()
                    for k in ('requirement', 'code', 'test'))):
            raise ValueError('Each check needs requirement, code, test and verified=true')
    return checks


def read_requirements(path: Path) -> list[str]:
    """Read and validate unique, non-blank requirements; delegate saves them."""
    import json
    items = json.loads(path.read_text(encoding='utf-8-sig'))  # BOM-tolerant, see review_checks
    if (not isinstance(items, list) or not items or
            any(not isinstance(item, str) or not item.strip() for item in items) or
            len(set(items)) != len(items)):
        raise ValueError('Requirements must be a non-empty JSON list of unique strings')
    return items
