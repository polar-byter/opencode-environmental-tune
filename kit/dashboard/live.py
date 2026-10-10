"""Change detection for the live page (Server-Sent Events).

The browser keeps one EventSource connection to /api/stream. The server polls the files
that matter every POLL_SECONDS and sends one event per change; the page then reloads only
the affected part. Polling file size and mtime is enough: the kit appends to its journal
and rewrites the choice file and the overlay as whole files.

Status: SKELETON. Every function raises NotImplementedError until it is implemented.
"""
from __future__ import annotations

import json
from pathlib import Path

POLL_SECONDS = 1.0
HEARTBEAT_SECONDS = 15.0


def stamp(path: Path) -> tuple[int, int] | None:
    """(size, mtime_ns) of the file, or None when it does not exist or cannot be read."""
    raise NotImplementedError('dashboard step 6.1: stamp')


def watched_files(roots: dict[str, Path]) -> dict[tuple[str, str], Path]:
    """Files to watch, by (project key, name).

    For every project: ("choice", .opencode/kit-models.json), ("overlay",
    .opencode/opencode.jsonc), and ("task:<id>", .metrics/<id>/events.jsonl) for every
    existing task folder. The list is rebuilt on every poll so new tasks appear.
    """
    raise NotImplementedError('dashboard step 6.2: watched_files')


class ChangeWatcher:
    """Remembers the last stamp of every watched file.

    poll(files) compares the stamps with the previous call and returns change rows
    {"project", "name"} for files that appeared, changed or disappeared, sorted by
    (project, name). The very first call only records the stamps and returns [].
    """

    def __init__(self):
        self.stamps: dict[tuple[str, str], tuple[int, int] | None] | None = None

    def poll(self, files: dict[tuple[str, str], Path]) -> list[dict]:
        """See the class description."""
        raise NotImplementedError('dashboard step 6.3: ChangeWatcher.poll')


def sse_message(event: str, data: dict) -> bytes:
    """One Server-Sent Event: b"event: <event>\\ndata: <compact JSON>\\n\\n", UTF-8.
    The JSON is produced with ensure_ascii=False and separators=(",", ":"), so it has no
    newline inside (a newline would end the event early)."""
    raise NotImplementedError('dashboard step 6.4: sse_message')
