"""OpenCode sessions of a task: token usage by model group and the live activity feed.

Exporting sessions runs the OpenCode CLI and takes seconds, so results are cached per
root session for CACHE_SECONDS. The CLI is found by kit/opencode_cli.py (through
TaskMetrics.collect_exports) — the same OpenCode the rest of the kit uses.

Status: SKELETON. Every function raises NotImplementedError until it is implemented.
"""
from __future__ import annotations

from pathlib import Path
import threading
import time

from ..task_metrics import TaskMetrics
from . import activity

CACHE_SECONDS = 15
GROUPS = ('paid', 'local', 'free', 'unknown')
TOKEN_FIELDS = ('input', 'output', 'reasoning', 'cache_read', 'cache_write')


def group_totals(usage: dict) -> dict:
    """Sum the rows of TaskMetrics.parse_exports(...)["models"] by their "group".

    Returns {group: {field: total}} for every group in GROUPS (all fields 0 when the group
    has no rows). If any row of a group has None in a field, the group total of that field
    is None: an unknown part makes the sum unknown.
    """
    raise NotImplementedError('dashboard step 5.1: group_totals')


def session_roles(exports: list[dict], root_session: str) -> dict:
    """{session id: role}: "master_chief" for root_session, "executor" for every other
    exported session (children are created by the Master Chief's task tool)."""
    raise NotImplementedError('dashboard step 5.2: session_roles')


class SessionCache:
    """Cached exports per (project root, root session).

    fetch(root, session) returns the list of exports from
    TaskMetrics(root).collect_exports(session); a second call within CACHE_SECONDS returns the
    cached list without running the CLI. `clock` is injectable for tests (default
    time.monotonic). The cache is shared by server threads, so access is guarded by a lock.
    On error the exception propagates and nothing is cached.
    """

    def __init__(self, clock=time.monotonic, collect=None):
        self.clock = clock
        # collect(root, session) -> exports; tests pass a fake instead of the real CLI.
        self.collect = collect or (lambda root, session: TaskMetrics(root).collect_exports(session))
        self.lock = threading.Lock()
        self.entries: dict[tuple[str, str], tuple[float, list[dict]]] = {}

    def fetch(self, root: Path, session: str) -> list[dict]:
        """Exports of the session tree, cached (see the class description)."""
        raise NotImplementedError('dashboard step 5.3: SessionCache.fetch')


def task_sessions(cache: SessionCache, root: Path, events: list[dict], now: float) -> dict:
    """Everything the task page shows about sessions.

    The root session is events[0]["session"]; without it -> {"available": False,
    "reason": "the task was started without --session"}.
    Otherwise exports = cache.fetch(root, session); usage =
    TaskMetrics(root).parse_exports(exports, session, start at, finish "ended" or now).
    Returns {"available": True, "groups": group_totals(usage), "models": usage["models"],
    "warnings": usage["warnings"], "feed": activity.merge_feeds([...feed_items per export
    with its role...]), "now": {session id: activity.current_step(export)} for busy sessions}.
    A ValueError from the CLI or the parser -> {"available": False, "reason": str(error)}.
    """
    raise NotImplementedError('dashboard step 5.4: task_sessions')
