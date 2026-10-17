"""Task journal: the append-only event log in .metrics/<ID>/events.jsonl.

Every other part of the kit reads the state of a task from this journal.
One JSON event per line; events are never edited or removed. A later event can
only add facts (for example an audited timeout correction, see corrected_events).
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

EVENT_KINDS = {'start', 'delegation', 'inspection', 'review', 'test', 'halt', 'resume', 'finish',
               'attempt_session', 'attempt_admission', 'attempt_end', 'integration', 'attempt_reclassification',
               'ux_review'}
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

        if base.resolve() != base or result.resolve() != result:
            raise ValueError('Metrics directories must not be symlinks or junctions')
        return result

    def read(self, task: str) -> list[dict]:
        try:
            lines = (self.task_dir(task) / 'events.jsonl').read_text(encoding='utf-8').splitlines()
            events = [json.loads(line) for line in lines]

            if (not events or events[0].get('kind') != 'start' or
                    any(not isinstance(e, dict) or not valid_number(e.get('at')) or
                        e.get('kind') not in EVENT_KINDS for e in events)):
                raise ValueError('Invalid journal events')

            return corrected_events(events)
        except (OSError, ValueError, AttributeError) as error:
            raise ValueError(f'Cannot read task {task}; start it first or inspect events.jsonl: {error}') from error

    # to use with statement for locking a task directory to prevent concurrent writes
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
