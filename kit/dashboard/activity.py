"""Live activity feed from OpenCode session exports: what the Master Chief and executors do now.

Pure functions over the JSON of `opencode session export <id>` (OpenCode 2.0.26 format):
    export = {"info": {"id", "title", "time", ...}, "messages": [message, ...]}
    message = {"id", "type": "assistant" | "user" | "system" | "idle", "agent",
               "model": {"providerID", "id"}, "time": {"created", "completed"} (ms),
               "content": [part, ...], "tokens": {...}}
    part = {"type": "text" | "reasoning" | "tool", ...}
    tool part = {"type": "tool", "name", "state": {"status", "input": {...}},
                 "time": {"created", "ran", "completed"}}
Reasoning text is never shown: it may be long and is not meant for the user.

Status: SKELETON. Every function raises NotImplementedError until it is implemented.
Later iteration: real OpenCode exports. Start with README.ru.md.
"""
from __future__ import annotations

# Longest text shown for one feed item; longer text ends with "…".
MAX_TEXT = 160
# Tool input keys shown as the target of a call, in priority order.
TARGET_KEYS = ('path', 'filePath', 'command', 'pattern', 'description', 'url')


def shorten(text: str, limit: int = MAX_TEXT) -> str:
    """Collapse all whitespace runs to one space and strip; if longer than limit characters,
    cut to limit-1 characters and append "…" (so the result has exactly limit characters)."""
    raise NotImplementedError('dashboard step 2.1: shorten')


def tool_target(part: dict) -> str:
    """Short human target of a tool call: the first present non-empty str value among
    TARGET_KEYS in part["state"]["input"], passed through shorten(). "" when none.
    Must not fail on a missing or non-dict state/input."""
    raise NotImplementedError('dashboard step 2.2: tool_target')


def feed_items(export: dict, session_role: str) -> list[dict]:
    """Feed rows of one session, oldest first.

    Only assistant messages count. For each part in message["content"]:
      - "text" with non-blank text -> kind "text", text = shorten(text)
      - "tool"                     -> kind "tool", tool = part["name"], target = tool_target(part),
                                      status = part["state"]["status"] (None if absent)
      - anything else (reasoning, unknown) is skipped
    Every row also has: session (export info id), role (session_role, e.g. "master_chief" or
    "executor"), agent (message "agent"), model ("providerID/id" or "unknown"), and at
    (seconds: part time "created" if present, else message time "created", divided by 1000).
    """
    raise NotImplementedError('dashboard step 2.3: feed_items')


def merge_feeds(feeds: list[list[dict]], limit: int = 50) -> list[dict]:
    """Merge several feeds into one, sorted by "at" ascending (stable for equal "at"),
    and keep only the newest `limit` rows."""
    raise NotImplementedError('dashboard step 2.4: merge_feeds')


def current_step(export: dict) -> dict | None:
    """What the session is doing right now, or None if it is idle.

    Look at the last assistant message. If it has no time.completed, the session is busy:
    return its last tool part with status "running" or "pending" as
    {"tool", "target", "since"}, or, if there is none, {"tool": None, "target": "", "since":
    message created / 1000}. "since" for a tool is its time.created / 1000.
    A completed last message (or no assistant message) means idle -> None.
    """
    raise NotImplementedError('dashboard step 2.5: current_step')
