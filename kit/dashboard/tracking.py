"""Explicit architecture/function tracking; independent of the metrics journal schema.

The Master Chief publishes a plan with this CLI. An executor may update only its
assigned .metrics/<task>/progress/<delegation_id>.json using its file tool.
Function completion is reported progress; accepted reviews are shown separately.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import time
import uuid

from ..task_metrics import TaskMetrics, valid_number
from .launcher import launch_lock

MAX_DOCUMENT = 1024 * 1024


def project_file(root: Path, name: str, *, must_exist: bool = True) -> Path:
    """Resolve a relative project file without traversal, links or secret/config paths."""
    path = Path(name)
    if not name or path.anchor or '..' in path.parts or (os.name != 'nt' and '\\' in name):
        raise ValueError('A project-relative file is required')
    if any(part.startswith('.') or part in ('node_modules', 'target', 'dist', 'build') for part in path.parts):
        raise ValueError('Hidden/config/generated files cannot be published')
    target = root / path
    if target.resolve() != target.absolute() or not target.resolve().is_relative_to(root.resolve()):
        raise ValueError('File must stay inside the project without links')
    if must_exist and not target.is_file():
        raise FileNotFoundError(name)
    return target


def progress_folder(root: Path, task: str) -> Path:
    folder = TaskMetrics(root).task_dir(task) / 'progress'
    if folder.resolve() != folder.absolute():
        raise ValueError('Progress directory must not be a link')
    return folder


def read_json(path: Path, default=None):
    if path.resolve() != path.absolute():
        raise ValueError('Progress files must not be links')
    if not path.exists():
        return default
    if path.stat().st_size > MAX_DOCUMENT:
        raise ValueError('Progress document exceeds 1 MiB')
    return json.loads(path.read_text(encoding='utf-8-sig'))


def atomic_json(path: Path, data):
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def validate_functions(root: Path, rows) -> list[dict]:
    if not isinstance(rows, list) or not rows or len(rows) > 2000:
        raise ValueError('Plan needs 1-2000 named functions')
    result, seen = [], set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('Each function needs id, name, file and work_item')
        fields = {key: row.get(key) for key in ('id', 'name', 'file', 'work_item')}
        if any(not isinstance(value, str) or not value.strip() or len(value) > 250 for value in fields.values()):
            raise ValueError('Function fields must be nonempty strings, at most 250 characters')
        if fields['id'] in seen:
            raise ValueError('Duplicate function ID: ' + fields['id'])
        project_file(root, fields['file'], must_exist=False)
        seen.add(fields['id'])
        result.append(fields)
    return result


def publish_plan(root: Path, task: str, document: str, functions: list[dict]) -> dict:
    root = root.resolve()
    source = project_file(root, document)
    if source.suffix.lower() not in ('.md', '.txt') or source.stat().st_size > MAX_DOCUMENT:
        raise ValueError('Architecture must be an UTF-8 .md/.txt file up to 1 MiB')
    text = source.read_text(encoding='utf-8-sig')
    rows = validate_functions(root, functions)
    metrics = TaskMetrics(root)
    with launch_lock(root, 5), metrics.lock(task):
        events = metrics.running(task)
        closed = {event.get('delegation_id') for event in events if event['kind'] == 'review'}
        if any(event['kind'] == 'delegation' and event['event_id'] not in closed for event in events):
            raise ValueError('Do not change the plan during an executor attempt')
        folder = progress_folder(root, task)
        folder.mkdir(exist_ok=True)
        previous = read_json(folder / 'plan.json', {})
        if not isinstance(previous, dict) or type(previous.get('revision', 0)) is not int:
            raise ValueError('Invalid previous plan')
        prior = {row['id']: row for row in previous.get('functions', [])}
        now = time.time()
        for row in rows:
            old = prior.get(row['id'])
            if old and any(row[key] != old[key] for key in ('name', 'file', 'work_item')):
                raise ValueError('Use a new function ID when its identity changes')
            row['registered_at'] = old['registered_at'] if old else now
        # Store the document in the same atomic record as its manifest.
        data = {'at': now, 'revision': previous.get('revision', 0) + 1,
                'document': document, 'text': text, 'functions': rows}
        atomic_json(folder / 'plan.json', data)
        return data


def architecture(root: Path, task: str) -> dict | None:
    plan = read_json(progress_folder(root, task) / 'plan.json')
    if plan is not None:
        if not isinstance(plan, dict) or not isinstance(plan.get('text'), str):
            raise ValueError('Invalid architecture record')
        return {'document': plan.get('document', ''), 'text': plan['text'],
                'at': plan.get('at'), 'registered': True}
    # Older tasks did not publish an architecture event. Never invent its date.
    for name in ('ARCHITECTURE.md', 'currentsteps.md'):
        try:
            target = project_file(root, name)
            if target.stat().st_size <= MAX_DOCUMENT:
                return {'document': name, 'text': target.read_text(encoding='utf-8-sig'),
                        'at': None, 'registered': False}
        except FileNotFoundError:
            continue
    return None


def work_items(events: list[dict]) -> list[dict]:
    rows, attempts = {}, {}
    for event in events:
        kind = event['kind']
        if kind == 'delegation':
            item = rows.setdefault(event['work_item'], {'id': event['work_item'], 'attempts': []})
            attempt = {key: event.get(key) for key in ('event_id', 'at', 'files', 'scope')}
            attempt.update(state='executor', tests=[])
            item['attempts'].append(attempt)
            attempts[event['event_id']] = attempt
        elif kind in ('inspection', 'review'):
            attempt = attempts.get(event.get('delegation_id'))
            if attempt:
                attempt['state'] = 'review' if kind == 'inspection' else event['result']
                attempt[kind + '_at'] = event['at']
                if kind == 'inspection':
                    attempt['changed'] = event.get('changed', [])
        elif kind == 'test' and event.get('phase') != 'baseline':
            for item in rows.values():
                latest = item['attempts'][-1]
                if latest['state'] in ('executor', 'review') and event.get('scope', 'full') in (latest['scope'], 'full'):
                    latest['tests'].append({key: event.get(key) for key in ('at', 'scope', 'status', 'tests', 'failures', 'errors')})
    for item in rows.values():
        item['state'] = item['attempts'][-1]['state']
        item['files'] = item['attempts'][-1].get('files') or []
    return list(rows.values())


def function_progress(root: Path, task: str, events: list[dict], now: float | None = None) -> dict:
    plan = read_json(progress_folder(root, task) / 'plan.json')
    if plan is None:
        return {'available': False, 'reason': 'Список функций для этой задачи ещё не опубликован',
                'total': None, 'implemented': None, 'accepted': None, 'functions': [], 'current': None}
    if not isinstance(plan, dict):
        raise ValueError('Invalid function plan')
    functions = validate_functions(root, plan.get('functions'))
    original = {row['id']: row for row in plan['functions']}
    items = {item['id']: item for item in work_items(events)}
    timestamp = time.time() if now is None else now
    finished = any(event['kind'] == 'finish' for event in events)
    current = None
    implemented = accepted = 0
    for function in functions:
        function['state'] = 'planned'
        registered = original[function['id']].get('registered_at')
        if not valid_number(registered):
            raise ValueError('Function registration time is missing')
        item = items.get(function['work_item'])
        if item:
            attempt = item['attempts'][-1]
            if attempt['state'] == 'accepted' and attempt.get('review_at', 0) >= registered:
                function['state'] = 'accepted'
                implemented += 1
                accepted += 1
            elif attempt['at'] >= registered and attempt['state'] in ('executor', 'review'):
                if not isinstance(attempt['event_id'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,160}', attempt['event_id']):
                    continue
                try:
                    report = read_json(progress_folder(root, task) / (attempt['event_id'] + '.json'), {})
                except (OSError, ValueError):
                    continue  # A file-tool writer may be replacing an incomplete record.
                if (not isinstance(report, dict) or report.get('delegation_id') != attempt['event_id']
                        or not isinstance(report.get('implemented_ids', []), list)):
                    continue
                allowed = {row['id'] for row in functions if row['work_item'] == function['work_item']}
                done = report.get('implemented_ids', [])
                if any(not isinstance(key, str) or key not in allowed for key in done):
                    continue
                if function['id'] in done:
                    function['state'] = 'implemented'
                    implemented += 1
                updated = report.get('updated_at')
                if (not finished and attempt['state'] == 'executor' and function['id'] not in done
                        and report.get('current_id') == function['id']
                        and valid_number(updated) and 0 <= timestamp - updated <= 90):
                    function['state'] = 'working'
                    current = dict(function, updated_at=updated)
    return {'available': True, 'revision': plan.get('revision'), 'total': len(functions),
            'implemented': implemented, 'accepted': accepted, 'functions': functions, 'current': current}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--task', required=True)
    parser.add_argument('--architecture', required=True, help='project-relative .md or .txt document')
    parser.add_argument('--functions', type=Path, required=True, help='JSON array of id/name/file/work_item')
    args = parser.parse_args(argv)
    try:
        rows = json.loads(args.functions.read_text(encoding='utf-8-sig'))
        data = publish_plan(args.root, args.task, args.architecture, rows)
        print(json.dumps({'revision': data['revision'], 'functions': len(data['functions'])}))
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
