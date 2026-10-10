"""Read a task journal (.metrics/<task>/events.jsonl) and turn it into dashboard views.

The journal is written by kit/task_metrics.py while a task runs, so every reader here must
tolerate a writer that is still appending. Pure functions take the list of events; only
read_events and JournalTail touch the disk.

Event kinds (see task_metrics.EVENT_KINDS): start, delegation, inspection, review, test,
halt, resume, finish. Every event has "kind", "at" (Unix seconds) and "event_id".
inspection/review link to their delegation through "delegation_id".

Status: SKELETON. Every function raises NotImplementedError until it is implemented.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..task_metrics import (CATEGORY_FAILED, CATEGORY_INCOMPLETE, CATEGORY_NO_RESULT, CATEGORY_TIMEOUT,
                            DEFAULT_LIMITS, is_halted, since_last_resume, task_limits, trailing)

RUNNING, HALTED, FINISHED = 'running', 'halted', 'finished'

# Piece states shown on the timeline.
AT_EXECUTOR = 'executor'   # delegated, the executor has not returned (no inspection yet)
IN_REVIEW = 'review'       # inspected, no review recorded yet
ACCEPTED = 'accepted'      # the latest attempt was accepted
REWORK = 'rework'          # the latest attempt was sent back and no new attempt started yet

NOT_GREEN = {CATEGORY_FAILED, CATEGORY_INCOMPLETE, CATEGORY_NO_RESULT, CATEGORY_TIMEOUT}


def parse_event(line: str, number: int) -> dict:
    """Parse one journal line into an event.

    Returns the decoded dict. It must be a dict with a str "kind" and an int/float "at"
    (bool is not a number).
    Raises:
        ValueError: invalid JSON or wrong shape; the message contains "line <number>".
    """
    raise NotImplementedError('dashboard step 1.1: parse_event')


def read_events(path: Path) -> list[dict]:
    """All events of one journal file, in file order.

    - Missing file -> [] (the task folder may exist before the first event).
    - Blank lines are skipped.
    - The LAST non-blank line may be cut in half by a writer that is still appending:
      if it is not valid JSON, it is ignored. Any earlier bad line raises ValueError
      (through parse_event, with its 1-based line number).
    - Read as UTF-8 text; a BOM at the start is accepted.
    """
    raise NotImplementedError('dashboard step 1.2: read_events')


class JournalTail:
    """Incremental reader for the live view: each call returns only the new events.

    Keeps the byte offset of the first unread byte. A trailing line without "\\n" is not
    consumed yet: the writer may still be appending it, so the offset stays before it.
    If the file is now shorter than the offset (recreated), reading restarts from 0 and
    self.reset becomes True for that call (False otherwise). A missing file returns [].
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self.offset = 0
        self.reset = False

    def new_events(self) -> list[dict]:
        """Events appended since the previous call (see the class description)."""
        raise NotImplementedError('dashboard step 1.3: JournalTail.new_events')


def task_status(events: list[dict]) -> str:
    """FINISHED if any finish event exists; otherwise HALTED if task_metrics.is_halted(events)
    returns an event; otherwise RUNNING.
    Raises:
        ValueError: events is empty.
    """
    raise NotImplementedError('dashboard step 1.4: task_status')


def pieces(events: list[dict]) -> list[dict]:
    """One row per delegated piece, in the order of its first delegation.

    Row fields:
        piece        piece name
        files        files of the latest delegation of this piece
        scope        scope of the latest delegation (piece name if missing)
        attempts     number of delegation events for this piece
        reworks      number of reviews with result "rework" for this piece
        state        AT_EXECUTOR | IN_REVIEW | ACCEPTED | REWORK, from the latest attempt:
                     no inspection -> AT_EXECUTOR; inspection but no review -> IN_REVIEW;
                     review accepted -> ACCEPTED; review rework -> REWORK
        started_at   "at" of the first delegation
        accepted_at  "at" of the accepting review of the latest attempt, else None
        unexpected   sorted unique files listed in "unexpected" of its inspections and reviews

    An inspection/review belongs to the delegation whose event_id equals its delegation_id.
    Without delegation_id (old journals) it belongs to the latest earlier delegation of the
    same piece. Inspections/reviews of an unknown piece are ignored.
    """
    raise NotImplementedError('dashboard step 1.5: pieces')


def test_runs(events: list[dict]) -> list[dict]:
    """Every test event as a uniform row, in journal order.

    Row: at, scope (default "full"), phase (default "work"), status, category,
    tests, failures, errors, skipped, duration (from "duration_seconds").
    A counter missing from the event stays None: unknown is not zero.
    """
    raise NotImplementedError('dashboard step 1.6: test_runs')


def guard_status(events: list[dict]) -> list[dict]:
    """Current value of every loop guard, computed exactly like task_metrics.limit_breach.

    One row per name in DEFAULT_LIMITS order: {name, value, limit, detail}.
    Only events after the last resume count (since_last_resume).
        max_reworks      largest number of rework reviews of one piece; detail = that piece
                         (the first one in journal order on a tie), or None when 0
        max_no_result    trailing(tests, {no_result, timeout}); detail None
        max_failed_runs  largest trailing(scoped, NOT_GREEN) over scopes, where "scoped" is
                         built as in limit_breach (baseline excluded, green full runs reset
                         every scope); detail = that scope (the first in sorted order on a
                         tie, as limit_breach checks them), or None when 0
        max_runs         number of test runs; detail None
    limit comes from task_limits(events).
    """
    raise NotImplementedError('dashboard step 1.7: guard_status')


def summary(events: list[dict]) -> dict:
    """Header of the task page.

    Keys: title (start.title), session (start.session), status (task_status),
    started_at (start.at), ended_at (finish "ended" if finished, else None),
    last_event_at (at of the last event), pieces (len of pieces()), reworks (total
    rework reviews), work_runs and green_work_runs (non-baseline tests; green = status
    "passed"), last_full (the last non-baseline test row with scope "full", or None),
    halt_reason (reason of the active halt, or None).
    """
    raise NotImplementedError('dashboard step 1.8: summary')
