"""
Its contents are used to detect unexpected changes in source files, done by delegated executors,
and to provide snapshots for executor edits, including new and Git-ignored source files.
It is a black box to the executor, which is not trusted to modify source files correctly.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

# Generated directories only. Source code must not be placed in these directories:
# they are excluded from the snapshot, so edits inside them are never detected.
# It is a way to exclude files that are not source files, and to avoid false positives in the snapshot.
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


def take_project_snapshot(root: Path) -> dict[str, str]:
    """
    Hash files outside excluded directories, regardless of Git ignore rules.
    Why SHA-256: a short fixed-size fingerprint per file is enough for comparison,
    so no file copies are stored, and two different contents practically never get the same hash.
    Returns {project-relative POSIX path: SHA-256 hex digest}.
    These hashes allow later comparison; they do not prevent or restore edits.
    """
    files_of_the_snapshot = {}
    #followlinks=False: do not follow symlinks, to avoid infinite loops and to avoid including files outside the project.
    for current, dirs, names in os.walk(root, followlinks=False):
        # [:] we modify existing dirs not create a new list,
        # so that os.walk() does not recurse into excluded directories.
        # ;walk uses the original dirs list to recurse, so we need to modify it in place.
        dirs[:] = sorted(d for d in dirs if d not in GENERATED)
        for name in dirs + names:
            path = Path(current) / name
            if path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
                raise ValueError(f'Snapshot cannot follow a symlink or junction: {path}')
        for name in sorted(names):
            path = Path(current) / name
            # why relative path: the "before" snapshot we made in one folder,
            # but the "after" snapshot may be made in isolated environments,
            # in a copy of the project  - it is the .metrics/<ID>/workspaces.
            # so we need to use relative paths to compare the two snapshots, and not absolute paths that may differ.
            files_of_the_snapshot[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files_of_the_snapshot


def compare_project_snapshots(before: dict[str, str], after: dict[str, str], allowed: list[str]) -> dict:
    """
    Compare two project snapshots and return {"changed": [...], "unexpected": [...]}.
    The "before" snapshot is usually the one taken before the delegated executor ran,
    the "after" snapshot is the one taken after it. With allowed=[] the function only
    answers whether anything changed at all (task_metrics.py uses it this way after tests).
    The "allowed" list is the list of files that are allowed to be changed by the delegated executor.
    The "changed" list is the list of files that have changed between the two snapshots.
    The "unexpected" list is the list of files that have changed but are not in the "allowed" list.
    """
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
