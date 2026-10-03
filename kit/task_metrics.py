"""Local task journal, test runner and OpenCode usage report. See METRICS.ru.md."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET

TOKEN_FIELDS = ('input', 'output', 'reasoning', 'cache_read', 'cache_write')


def valid_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def session_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,159}', value):
        raise ValueError('Invalid session ID')
    return value


def message_info(message):
    """V2 messages are direct objects; legacy messages wrap data in info/parts."""
    if not isinstance(message, dict):
        raise ValueError('Unsupported message structure')
    info = message.get('info', message)
    if not isinstance(info, dict):
        raise ValueError('Unsupported message info')
    return info


def child_references(export):
    """Fallback discovery from tool metadata, never from model-written text."""
    found = set()
    for message in export['messages']:
        message_info(message)
        for part in message.get('parts', message.get('content', [])):
            if not isinstance(part, dict) or part.get('type') != 'tool':
                continue
            metadata = part.get('state', {}).get('metadata', {})
            if isinstance(metadata, dict):
                for key in ('sessionID', 'sessionId'):
                    if metadata.get(key):
                        found.add(session_id(metadata[key]))
    return found


class TaskMetrics:
    """One writer per task. Data is stored in project/.metrics/task/."""

    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    def task_dir(self, task: str) -> Path:
        reserved = {'CON', 'PRN', 'AUX', 'NUL', *('COM'+str(n) for n in range(1, 10)),
                    *('LPT'+str(n) for n in range(1, 10))}
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', task) or task.upper() in reserved:
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
                        e.get('kind') not in {'start', 'review', 'test', 'finish'} for e in events)):
                raise ValueError('Invalid journal events')
            return events
        except (OSError, ValueError, AttributeError) as error:
            raise ValueError(f'Cannot read task {task}; start it first or inspect events.jsonl: {error}') from error

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

    def start(self, task: str, session: str | None = None, title: str | None = None) -> dict:
        if session is not None:
            session_id(session)
        self.task_dir(task).mkdir(parents=True, exist_ok=False)
        with self.lock(task):
            return self.append(task, 'start', session=session, title=title or task)

    def active(self, task):
        events = self.read(task)
        if any(e['kind'] == 'finish' for e in events):
            raise ValueError('Task is finished; start a new task ID')
        return events

    def review(self, task: str, piece: str, result: str) -> dict:
        if not piece.strip() or result not in {'accepted', 'rework'}:
            raise ValueError('Review requires a piece and accepted/rework result')
        with self.lock(task):
            self.active(task)
            return self.append(task, 'review', piece=piece, result=result)

    def parse_tests(self, output: str, returncode: int, junit: Path | None = None) -> dict:
        result = dict(status='unknown', tests=None, failures=None, errors=None, skipped=None)
        if junit is not None:
            try:
                tree = ET.parse(junit)
                cases = [e for e in tree.iter() if e.tag.rsplit('}', 1)[-1] == 'testcase']
                result.update(tests=len(cases), failures=0, errors=0, skipped=0)
                for case in cases:
                    tags = {e.tag.rsplit('}', 1)[-1] for e in case}
                    for tag, key in [('failure', 'failures'), ('error', 'errors'), ('skipped', 'skipped')]:
                        result[key] += int(tag in tags)
            except (OSError, ET.ParseError) as error:
                result['diagnostic'] = f'JUnit report unavailable: {error}'
        else:
            matches = list(re.finditer(r'^Ran (\d+) tests? in [^\r\n]+\r?\n', output, re.M))
            # Multiple summaries could conceal earlier failures; require one run per command.
            if len(matches) == 1:
                summary = output[matches[0].end():].strip()
                end = re.fullmatch(r'(OK|FAILED)(?: \(([^\r\n]*)\))?', summary)
                if end:
                    result.update(tests=int(matches[0][1]), failures=0, errors=0, skipped=0)
                    counts = dict(re.findall(r'([a-z ]+)=(\d+)', end[2] or ''))
                    for key, value in counts.items():
                        key = key.strip()
                        if key in result:
                            result[key] = int(value)
                        elif key in {'expected failures', 'unexpected successes'}:
                            result['skipped'] += int(value)
                        else:
                            result['diagnostic'] = 'Unrecognized unittest outcome'
                    if end[1] == 'FAILED' and not result['failures'] and not result['errors']:
                        result['errors'] = 1
        if returncode != 0:
            result['status'] = 'failed'
        elif result.get('diagnostic') or result['tests'] is None:
            result['status'] = 'unknown'
        elif result['failures'] or result['errors']:
            result['status'] = 'failed'
        elif result['tests'] == 0:
            result['status'] = 'empty'
        elif result['skipped']:
            result['status'] = 'skipped'
        else:
            result['status'] = 'passed'
        return result

    def test(self, task: str, command: list[str], timeout: float = 300, junit: str | None = None) -> dict:
        if not command or not valid_number(timeout) or timeout == 0:
            raise ValueError('Provide a command and a finite positive timeout')
        xml = (self.root / junit).resolve() if junit else None
        if xml and (not xml.is_relative_to(self.root) or xml.exists()):
            raise ValueError('JUnit path must be inside project and must not exist before the run')
        with self.lock(task):
            self.active(task)
            started = time.monotonic()
            env = dict(os.environ, PYTHONIOENCODING='utf-8')
            process = None
            timed_out = False
            try:
                process = subprocess.Popen(command, cwd=self.root, env=env, stdin=subprocess.DEVNULL,
                                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                           text=True, encoding='utf-8', errors='replace',
                                           start_new_session=os.name != 'nt')
                try:
                    output, _ = process.communicate(timeout=timeout)
                    code = process.returncode
                except subprocess.TimeoutExpired:
                    timed_out = True
                    if os.name == 'nt':
                        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
                    else:
                        os.killpg(process.pid, signal.SIGKILL)
                    if process.poll() is None:
                        process.kill()
                    output, _ = process.communicate(timeout=10)
                    code = 124
            except OSError as error:
                output, code = str(error), 127
            finally:
                if process is not None and process.poll() is None:
                    process.kill()
                    process.wait(timeout=10)
            log = 'test-' + uuid.uuid4().hex + '.log'
            (self.task_dir(task) / log).write_text(output, encoding='utf-8')
            parsed = self.parse_tests(output, code, xml)
            if timed_out:
                parsed['status'] = 'timeout'
            return self.append(task, 'test', command=command, returncode=code, log=log,
                               duration_seconds=time.monotonic()-started, **parsed)

    def parse_exports(self, exports: list[dict], session: str, since: float, until: float) -> dict:
        sessions = {}
        for export in exports:
            if (not isinstance(export, dict) or not isinstance(export.get('info'), dict) or
                    not isinstance(export.get('messages'), list)):
                raise ValueError('Unsupported OpenCode export: expected info and messages')
            sid = session_id(export['info'].get('id'))
            sessions.setdefault(sid, []).append(export)
        if session not in sessions:
            raise ValueError('Root session export is missing')
        allowed = {session}
        while True:
            more = {sid for sid, items in sessions.items() if items[0]['info'].get('parentID') in allowed}
            if more <= allowed:
                break
            allowed |= more
        warnings = []
        for sid in sessions.keys() - allowed:
            warnings.append(f'Посторонняя сессия исключена: {sid}')
        rows, seen = {}, {}
        for sid in sorted(allowed):
            for export in sessions[sid]:
                warnings.extend(export.get('_metrics_warnings', []))
                for child in child_references(export) - allowed:
                    warnings.append(f'Нет выгрузки дочерней сессии: {child}')
                for message in export['messages']:
                    info = message_info(message)
                    if info.get('role', info.get('type')) != 'assistant':
                        continue
                    mid = info.get('id')
                    stamp = info.get('time', {})
                    if not isinstance(stamp, dict) or not isinstance(mid, str) or not valid_number(stamp.get('created')):
                        warnings.append(f'Пропущено сообщение без ID/времени: {sid}')
                        continue
                    if not since <= stamp['created']/1000 <= until:
                        continue
                    if not valid_number(stamp.get('completed')) or stamp['completed']/1000 > until:
                        warnings.append('Незавершённые на момент отчёта сообщения не включены.')
                        continue
                    key = (sid, mid)
                    if key in seen:
                        if seen[key] != info:
                            raise ValueError(f'Conflicting duplicate message: {sid}/{mid}')
                        continue
                    seen[key] = info
                    model_ref = info.get('model') if isinstance(info.get('model'), dict) else {}
                    provider = info.get('providerID', model_ref.get('providerID'))
                    model = info.get('modelID', model_ref.get('id'))
                    provider = provider if isinstance(provider, str) and provider else 'unknown'
                    model = model if isinstance(model, str) and model else 'unknown'
                    group = 'local' if provider == 'lmstudio' else ('unknown' if provider == 'unknown' else 'paid')
                    row = rows.setdefault((provider, model), dict(provider=provider, model=model, group=group,
                                          messages=0, missing_usage=0, **dict.fromkeys(TOKEN_FIELDS, 0)))
                    tokens = info.get('tokens') if isinstance(info.get('tokens'), dict) else {}
                    cache = tokens.get('cache') if isinstance(tokens.get('cache'), dict) else {}
                    values = dict(input=tokens.get('input'), output=tokens.get('output'), reasoning=tokens.get('reasoning'),
                                  cache_read=cache.get('read'), cache_write=cache.get('write'))
                    values = {k: v if type(v) is int and v >= 0 else None for k, v in values.items()}
                    row['messages'] += 1
                    row['missing_usage'] += int(values['input'] is None or values['output'] is None)
                    for field, value in values.items():
                        row[field] = None if value is None or row[field] is None else row[field]+value
        warnings.append('Учтены сообщения в интервале задачи; служебные вызовы вне экспорта могут отсутствовать.')
        if any(r['missing_usage'] for r in rows.values()):
            warnings.append('В части сообщений нет корректного расхода токенов; соответствующие суммы неизвестны.')
        return dict(models=list(rows.values()), warnings=list(dict.fromkeys(warnings)), sessions=sorted(allowed))

    def cli_json(self, executable: str, args: list[str]):
        result = subprocess.run([executable, *args], cwd=self.root, stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
        if result.returncode:
            raise ValueError(f'OpenCode {args[0]} failed (exit {result.returncode})')
        try:
            return json.loads(result.stdout.lstrip('\ufeff'))
        except ValueError as error:
            raise ValueError('OpenCode returned non-JSON output; check CLI version/server') from error

    def collect_exports(self, session: str, executable: str = 'opencode') -> list[dict]:
        session_id(session)
        if executable == 'opencode':
            desktop = Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs/@opencodedesktop/resources/opencode-cli.exe'
            try:
                native_available = desktop.is_file()
            except OSError:
                native_available = False
            executable = str(desktop) if native_available else (shutil.which('opencode') or executable)
        queue, seen, exports = [session], set(), []
        while queue:
            sid = session_id(queue.pop(0))
            if sid in seen:
                continue
            if len(seen) >= 100:
                raise ValueError('More than 100 sessions; narrow task scope')
            seen.add(sid)
            try:
                try:
                    export = self.cli_json(executable, ['session', 'export', sid])
                except ValueError:
                    export = self.cli_json(executable, ['export', sid])
                if not isinstance(export, dict) or export.get('info', {}).get('id') != sid:
                    raise ValueError('Export session ID mismatch')
                if not isinstance(export.get('messages'), list):
                    raise ValueError('Export messages missing')
                children = child_references(export)
                try:
                    cursor, cursors = None, set()
                    for _ in range(100):
                        args = ['api', 'session.list', '--param', f'parentID={sid}', '--param', 'limit=100']
                        if cursor:
                            args += ['--param', f'cursor={cursor}']
                        page = self.cli_json(executable, args)
                        if not isinstance(page, dict) or not isinstance(page.get('data'), list):
                            raise ValueError('Unsupported session.list response')
                        for item in page['data']:
                            if not isinstance(item, dict) or item.get('parentID') != sid:
                                raise ValueError('Child session parent mismatch')
                            children.add(session_id(item.get('id')))
                        cursor = page.get('cursor', {}).get('next')
                        if not cursor:
                            break
                        if cursor in cursors:
                            raise ValueError('Repeated pagination cursor')
                        cursors.add(cursor)
                    else:
                        raise ValueError('Too many session pages')
                except (ValueError, OSError, subprocess.TimeoutExpired) as error:
                    export['_metrics_warnings'] = [f'Поиск дочерних сессий неполон: {error}']
                queue.extend(sorted(children - seen))
                exports.append(export)
            except (OSError, subprocess.TimeoutExpired) as error:
                raise ValueError(f'Cannot collect OpenCode session {sid}: {error}') from error
        return exports

    def render(self, task: str, events: list[dict], usage: dict, ended: float) -> str:
        def label(value):
            return str(value).replace('|', '\\|').replace('\r', ' ').replace('\n', ' ').replace('<', '&lt;').replace('>', '&gt;')
        def count(value):
            return 'нет данных' if value is None else f'{value:,}'.replace(',', ' ')
        duration = max(0, int(ended-events[0]['at']))
        reviews = [e for e in events if e['kind'] == 'review']
        tests = [e for e in events if e['kind'] == 'test']
        lines = [f'## 📊 Итоги задачи · {label(events[0]["title"])}', '',
                 f'⏱ Время: **{duration//60} мин {duration%60} сек**', '']
        for group, heading in [('paid', 'Платные модели'), ('local', 'Бесплатные / локальные · LM Studio'),
                               ('unknown', 'Неизвестный провайдер')]:
            rows = [r for r in usage['models'] if r['group'] == group]
            if group == 'unknown' and not rows:
                continue
            lines += [f'### {heading}', '']
            if not rows:
                lines += ['Нет данных о вызовах этой группы в выбранном интервале.', '']
                continue
            lines += ['| Модель | Вход | Выход | Рассуждения | Кэш: чтение | Кэш: запись |',
                      '|---|---:|---:|---:|---:|---:|']
            for row in rows:
                lines.append('| ' + label(row['provider']+'/'+row['model']) + ' | ' +
                             ' | '.join(count(row[f]) for f in TOKEN_FIELDS) + ' |')
            lines.append('')
        lines += [f'🔁 Возвраты на переделку: **{sum(e["result"] == "rework" for e in reviews)}** '
                  f'· Всего ревью: **{len(reviews)}**', '',
                  f'🧪 Полностью успешные прогоны: **{sum(e["status"] == "passed" for e in tests)} из {len(tests)}**', '']
        if tests:
            last = tests[-1]
            lines += [f'Последний прогон: **{label(last["status"])}** · тестов: {count(last["tests"])} · '
                      f'падений: {count(last["failures"])} · ошибок: {count(last["errors"])} · '
                      f'пропусков: {count(last["skipped"])}.', '']
        else:
            lines += ['Тесты через утилиту не запускались; успешность не подтверждена.', '']
        lines += ['Все `lmstudio` — локальные без платы за API; остальные провайдеры считаются платными по умолчанию.',
                  'Токены рассуждений и кэша показаны отдельно, без сложения пересекающихся счётчиков.',
                  'Срез сделан перед итоговым ответом: его токены не включены. Стоимость и экономия не оценивались.', '']
        if usage['warnings']:
            lines += ['Примечания:', ''] + ['- '+label(w) for w in usage['warnings']] + ['']
        return '\n'.join(lines)

    def finish(self, task: str, export_paths: list[str] | None = None, executable: str = 'opencode') -> str:
        with self.lock(task):
            events = self.read(task)
            finished = next((e for e in events if e['kind'] == 'finish'), None)
            if finished:
                report = self.render(task, events, finished['usage'], finished['ended'])
            else:
                ended = time.time()
                usage = dict(models=[], warnings=[], sessions=[])
                try:
                    session = events[0]['session']
                    if not session:
                        raise ValueError('Нет ID сессии OpenCode: токены — нет данных.')
                    exports = ([json.loads((self.root / p).read_text(encoding='utf-8-sig')) for p in export_paths]
                               if export_paths else self.collect_exports(session, executable))
                    usage = self.parse_exports(exports, session, events[0]['at'], ended)
                except (OSError, ValueError, TypeError, AttributeError, subprocess.TimeoutExpired) as error:
                    usage['warnings'].append(f'Токены — нет данных: {error}')
                # Journal first: report-write failure can be retried without recounting.
                self.append(task, 'finish', ended=ended, usage=usage)
                report = self.render(task, events, usage, ended)
            folder = self.task_dir(task)
            tmp = folder / ('report-'+uuid.uuid4().hex+'.tmp')
            tmp.write_text(report, encoding='utf-8')
            tmp.replace(folder/'report.md')
            return report

    @staticmethod
    def main(argv=None) -> int:
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, 'reconfigure'):
                stream.reconfigure(encoding='utf-8', errors='replace')
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--root', type=Path, default=Path.cwd())
        sub = parser.add_subparsers(dest='action', required=True)
        start = sub.add_parser('start')
        start.add_argument('--session')
        start.add_argument('--title')
        review = sub.add_parser('review')
        review.add_argument('--piece', required=True)
        review.add_argument('--result', choices=['accepted', 'rework'], required=True)
        test = sub.add_parser('test')
        test.add_argument('--timeout', type=float, default=300)
        test.add_argument('--junit')
        test.add_argument('command', nargs=argparse.REMAINDER)
        finish = sub.add_parser('finish')
        finish.add_argument('--export', action='append', dest='exports')
        finish.add_argument('--opencode', default='opencode')
        for command in (start, review, test, finish):
            command.add_argument('--task', required=True)
        args = parser.parse_args(argv)
        metrics = TaskMetrics(args.root)
        try:
            if args.action == 'start':
                event = metrics.start(args.task, args.session, args.title)
            elif args.action == 'review':
                event = metrics.review(args.task, args.piece, args.result)
            elif args.action == 'finish':
                print(metrics.finish(args.task, args.exports, args.opencode))
                return 0
            else:
                command = args.command[1:] if args.command[:1] == ['--'] else args.command
                event = metrics.test(args.task, command, args.timeout, args.junit)
                print((metrics.task_dir(args.task)/event['log']).read_text(encoding='utf-8'))
                print(json.dumps(event, ensure_ascii=False))
                return max(1, event['returncode']) if event['status'] != 'passed' else 0
            print(json.dumps(event, ensure_ascii=False))
            return 0
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            print(f'Metrics error: {error}', file=sys.stderr)
            return 2


if __name__ == '__main__':
    sys.exit(TaskMetrics.main())
