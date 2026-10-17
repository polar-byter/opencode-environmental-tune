"""Task journal: event log in .metrics/<ID>/events.jsonl.
It is the append-only record of what happened to a task,
including cycle steps: delegation, inspection, review and test events.

The state of a task (running, halted, finished, who is waiting for review) is computed
from these events by other parts of the kit; the journal itself is a simple append-only log.
Every other part of the kit reads the state of a task from this journal.

It is JSON Lines: one JSON event per line.
Events are never edited or removed; a later event can only add facts.
Why: to make sure that the journal is a faithful record of what happened,
even if the Master Chief makes a mistake. Event types are listed in KNOWN_EVENT_TYPES.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import re
import time
import uuid

# Every allowed value of the "kind" field of a journal event; read() rejects any other.
# These are types of facts, not states: events repeat (one test event per run) and the
# order is checked by the commands themselves, not by this set.
KNOWN_EVENT_TYPES = {
    # 1. Main task cycle, written by task_metrics.py.
    'start',        # the task is opened: title, OpenCode session ID, loop guard limits; always the first event
    'delegation',   # work is given to the executor: the one allowed file, frozen requirements, "before" snapshot
    'inspection',   # right after the executor returns, before any reviewer edits: changed and unexpected files
    'test',         # one run of the test command: counts, category (passed/tests_failed/no_result/timeout), scope, log
    'review',       # the Master Chief's decision: accepted (with evidence), rework, failed (no work done) or blocked
    'ux_review',    # final interface pass before finish: scenarios really checked, or why it was skipped/not needed
    'finish',       # the task is closed: end time and frozen token usage; no events are allowed after it

    # 2. Protective stop.
    'halt',         # a loop guard fired (task_metrics.py writes it itself): work stops until the user decides
    'resume',       # the user decided how to continue: lifts the halt, loop guard counters start from zero

    # 3. Isolated worker, parallel mode only; written by execution_controller.py.
    #    Each worker edits its own copy of the project in its own OpenCode child session.
    'attempt_session',           # a child session is created for the attempt: session ID, role, worker, previous attempt
    'attempt_admission',         # the task text is confirmed delivered to that session: the model has really started
    'attempt_end',               # the attempt is over: reason (setup_error, api_error, deadline, pause ...) and
                                 # whether the session is confirmed stopped; inspection requires stopped=True
    'integration',               # the accepted file is copied from the worker's copy into the main project
    'attempt_reclassification',  # an audited correction added later: an api_error/blocked attempt was really a
                                 # timeout, so corrected_events() reads it as deadline/rework; old rows stay as written
}
WINDOWS_RESERVED = frozenset({'CON', 'PRN', 'AUX', 'NUL',
                              *(f'COM{n}' for n in range(1, 10)), *(f'LPT{n}' for n in range(1, 10))})


def valid_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def pending_attempts(events, work_item=None):
    """Select open attempts by identity rather than a global last delegation."""
    closed = {e.get('delegation_id') for e in events if e['kind'] == 'review'}
    return [e for e in events if e['kind'] == 'delegation' and e['event_id'] not in closed
            and (work_item is None or e['work_item'] == work_item)]


def normalize_work_item(event: dict) -> dict:
    """Read the legacy journal field without changing the original event.

    Events without 'piece' are returned unchanged. Otherwise a shallow copy
    replaces 'piece' with 'work_item'. Equal old/new names are accepted;
    conflicting names raise ValueError rather than attaching work to the wrong item.
    """
    if 'piece' not in event:
        return event
    if 'work_item' in event and event['work_item'] != event['piece']:
        raise ValueError('Conflicting work_item and legacy piece fields')
    normalized = dict(event)
    normalized['work_item'] = normalized.pop('piece')
    return normalized


def session_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,159}', value):
        raise ValueError('Invalid session ID')
    return value


def corrected_events(events):
    """Project an audited timeout correction without rewriting original journal rows.

    Only an api_error/blocked pair can become deadline/rework. Acceptance, file
    evidence and timestamps are never changed. References must precede the correction.
    """
    result, positions = [], {}
    for source in events:
        event = dict(normalize_work_item(source))
        if event['kind'] == 'attempt_reclassification':
            if any(not isinstance(event.get(key), str) or not event[key].strip()
                   for key in ('end_event', 'review_event', 'delegation_id', 'explanation')):
                raise ValueError('Timeout correction requires exact references and an explanation')
            end_index = positions.get(event.get('end_event'))
            review_index = positions.get(event.get('review_event'))
            if end_index is None or review_index is None or event.get('reason') != 'deadline':
                raise ValueError('Invalid timeout correction references')
            end, review = result[end_index], result[review_index]
            identifier = event.get('delegation_id')
            if (end['kind'] != 'attempt_end' or review['kind'] != 'review'
                    or end.get('delegation_id') != identifier or review.get('delegation_id') != identifier
                    or end.get('original_reason', end.get('reason')) != 'api_error'
                    or review.get('original_result', review.get('result')) != 'blocked'
                    or not end.get('stopped') or event['at'] < max(end['at'], review['at'])
                    or end.get('classification_event') not in (None, event['event_id'])):
                raise ValueError('Only a stopped API/blocked attempt can be corrected')
            result[end_index] = dict(end, reason='deadline', original_reason='api_error', classification_event=event['event_id'])
            result[review_index] = dict(review, result='rework', reason='deadline', original_result='blocked', classification_event=event['event_id'])
        positions[event.get('event_id')] = len(result)
        result.append(event)
    return result


class TaskJournal:
    """Reads and writes the journal of the tasks of one project.

    Data is stored in <root>/.metrics/<task>/. One writer per task: lock() prevents
    concurrent writes. TaskMetrics builds the task commands on top of this class.
    """

    # root is the project root; metrics are stored in root/.metrics/
    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    # get the directory for a specific task, validating the task name and ensuring no symlinks
    def task_dir(self, task: str) -> Path:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', task) or task.upper() in WINDOWS_RESERVED:
            raise ValueError('Task ID: 1-80 ASCII letters/digits/_/-, not a reserved Windows name')

        base = self.root / '.metrics'
        result = base / task
        # this condition uses resolve() to prevent symlinks or junctions in the path
        # junction means a Windows NTFS directory link, which is not a symlink but behaves like one.
        if base.resolve() != base or result.resolve() != result:
            raise ValueError('Metrics directories must not be symlinks or junctions')
        return result

    def read(self, task: str) -> list[dict]:
        """We check the journal for basic validity;
        we do not check that the events are consistent with each other.
        but integrity checks are done by TaskMetrics, which reads the journal and computes the task state.
        
        """
        try:
            journal_jsonl_lines = (self.task_dir(task) / 'events.jsonl').read_text(encoding='utf-8').splitlines()
            events = []
            for number, line in enumerate(journal_jsonl_lines, start=1):
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError as error:
                    raise ValueError(f'line {number}: invalid JSON ({error.msg})') from error
            #checking sequence: first event must be start, all events must have a valid number "at" and a known kind
            if not events:
                raise ValueError('the journal is empty')
            for number, event in enumerate(events, start=1):
                if not isinstance(event, dict):
                    raise ValueError(f'line {number}: not a JSON object')
                if not valid_number(event.get('at')):
                    raise ValueError(f'line {number}: missing or invalid "at" time')
                if event.get('kind') not in KNOWN_EVENT_TYPES:
                    raise ValueError(f'line {number}: unknown event type {event.get("kind")!r}')
            if events[0]['kind'] != 'start':
                raise ValueError(f'line 1: the first event must be "start", not {events[0]["kind"]!r}')

            return corrected_events(events)
        except (OSError, ValueError, AttributeError) as error:
            raise ValueError(f'Cannot read task {task}; start it first or inspect events.jsonl: {error}') from error

    # to use with statement for locking a task directory to prevent concurrent writes
    # @contextmanager: the caller must use "with journal.lock(task):" to hold the lock while writing
    @contextmanager
    def lock(self, task: str):
        path = self.task_dir(task) / '.lock'
        try:
            handle = path.open('x', encoding='ascii')
        except FileExistsError as error:
            raise ValueError(f'Task {task} is locked; inspect its process before removing .lock') from error
        try:
            handle.write(str(os.getpid()))
            handle.close()
            yield
        finally:
            handle.close()
            path.unlink()

    def append(self, task: str, kind: str, **data) -> dict:
        """Write one event to the end of the task journal and return it.

        It is called by the task_metrics.py commands (main cycle, halt/resume, finish) and by
        execution_controller.py, which writes the isolated worker events in parallel mode.
        All of them write to the same journal of the task. The caller must hold lock(task).

        The journal sets "at" and "event_id" itself, overriding any values in data.
        After return the line is on disk (flush + fsync).
        Raises ValueError for a kind outside KNOWN_EVENT_TYPES: read() would reject it later.
        """
        if kind not in KNOWN_EVENT_TYPES:
            raise ValueError(f'Unknown journal event type: {kind!r}')
        event = dict(data, kind=kind, at=time.time(), event_id=uuid.uuid4().hex)
        with (self.task_dir(task) / 'events.jsonl').open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + '\n')
            handle.flush()
            os.fsync(handle.fileno())
        return event

    # check if the task is active (not finished) and return its events
    def active(self, task):
        events = self.read(task)
        if any(e['kind'] == 'finish' for e in events):
            raise ValueError('Task is finished; start a new task ID')
        return events
