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
if __package__:
    from .delegation_guard import compare, read_requirements, review_checks, snapshot, source_path
    from .opencode_cli import locate_opencode
    from .task_control_state import blocking_reason
else:
    from delegation_guard import compare, read_requirements, review_checks, snapshot, source_path
    from opencode_cli import locate_opencode
    from task_control_state import blocking_reason

TOKEN_FIELDS = ('input', 'output', 'reasoning', 'cache_read', 'cache_write')
EVENT_KINDS = {'start', 'delegation', 'inspection', 'review', 'test', 'halt', 'resume', 'finish',
               'attempt_session', 'attempt_admission', 'attempt_end', 'integration'}
# failed: the executor returned no work (error, rate limit, unavailable model) and changed no files.
REVIEW_RESULTS = {'accepted', 'rework', 'failed'}
WINDOWS_RESERVED = frozenset({'CON', 'PRN', 'AUX', 'NUL',
                              *(f'COM{n}' for n in range(1, 10)), *(f'LPT{n}' for n in range(1, 10))})

# Loop guards. Any of them stops the task until the user decides how to continue.
DEFAULT_LIMITS = dict(
    max_reworks=3,      # returns of one work item to the executor
    max_no_result=3,    # test runs in a row without readable test results (setup or build problem)
    max_failed_runs=12, # test runs in a row that are not fully green (a module of several
                        # functions stays red until its last function is done, so this is generous)
    max_runs=60,        # test runs in total; raise it with --max-runs for a large project
)

# What a test run means for the build loop.
CATEGORY_PASSED = 'passed'          # tests ran, all green
CATEGORY_FAILED = 'tests_failed'    # tests ran, some failed: a code or test problem
CATEGORY_INCOMPLETE = 'incomplete'  # tests ran without failures, but some were skipped
CATEGORY_NO_RESULT = 'no_result'    # no readable test results: setup, build or tool problem
CATEGORY_TIMEOUT = 'timeout'        # the command did not finish in time

# Exit codes of the command line, so the Master Chief can react without parsing text.
EXIT_OK = 0
EXIT_TESTS_FAILED = 1
EXIT_USAGE = 2
EXIT_STOP = 3
EXIT_NO_RESULT = 4


class TaskHalted(Exception):
    """The task reached a loop guard. The Master Chief must stop and ask the user."""


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


def message_info(message):
    """V2 messages are direct objects; legacy messages wrap data in info/parts."""
    if not isinstance(message, dict):
        raise ValueError('Unsupported message structure')
    info = message.get('info', message)
    if not isinstance(info, dict):
        raise ValueError('Unsupported message info')
    return info


def master_chief_tool_child_references(export):
    """Find child sessions that the Master Chief started through its tools.

    When the Master Chief calls an executor, OpenCode runs the executor in a separate
    child session. Its messages and tokens are not part of the Master Chief's export,
    so the report must find every child to count all usage.

    The main source of children is the OpenCode API (session.list, see
    collect_exports). This function is the fallback: it scans tool parts of the
    export for state.metadata.sessionID (or sessionId). Session IDs are taken
    only from tool metadata, never from text written by a model.

    Returns a set of session IDs.
    """
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


def run_command(command: list[str], cwd: Path, timeout: float) -> tuple[str, int, bool]:
    """
    Runs a command and returns (combined output, exit code, timed_out).

    Exit code 124 means the timeout was reached, 127 means the program was not found.
    On timeout the whole process tree is killed, not only the parent process:
    Maven, Gradle and dotnet start child processes that would otherwise keep running.
    """
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    try:
        process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, encoding='utf-8', errors='replace',
                                   start_new_session=os.name != 'nt')
    except OSError as error:
        return str(error), 127, False
    try:
        output, _ = process.communicate(timeout=timeout)
        return output, process.returncode, False
    except subprocess.TimeoutExpired:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        else:
            os.killpg(process.pid, signal.SIGKILL)
        if process.poll() is None:
            process.kill()
        output, _ = process.communicate(timeout=10)
        return output, 124, True
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)


def resolve_command(command: list[str], windows: bool = os.name == 'nt') -> list[str]:
    """
    On Windows, replace the program name with its full path found through PATH and PATHEXT.

    Programs such as npx, npm, mvn and gradlew are .cmd or .bat files on Windows. Without a
    shell, Windows does not find them by the bare name, so 'mvn test' would fail with
    "program not found". shutil.which knows PATHEXT and returns e.g. C:\\...\\mvn.cmd.
    On other systems, or when nothing is found, the command is returned unchanged.
    """
    if not windows or not command:
        return list(command)
    found = shutil.which(command[0])
    return [found, *command[1:]] if found else list(command)


def resolve_opencode(executable: str) -> str:
    """Find the OpenCode CLI (order in kit/opencode_cli.py).

    Reading exports only needs plain arguments, so a .cmd wrapper on PATH is still accepted
    as the last resort. Unknown names are returned as is.
    """
    return locate_opencode(executable) or shutil.which(executable) or executable


def local_tag(element) -> str:
    """Tag name without an XML namespace: '{ns}testcase' -> 'testcase'."""
    return element.tag.rsplit('}', 1)[-1]


def parse_junit_files(paths: list[Path]) -> dict:
    """
    Counts test cases and their outcomes in one or more JUnit XML reports.

    Maven and Gradle write one file per test class, so several files are summed.
    A file that cannot be read makes the whole result unknown (diagnostic), because
    a partial sum would look like a smaller but complete test suite.
    """
    if not paths:
        return dict(diagnostic='No JUnit XML report was written by the test command')
    result = dict(tests=0, failures=0, errors=0, skipped=0)
    for path in paths:
        try:
            tree = ET.parse(path)
        except (OSError, ET.ParseError) as error:
            return dict(diagnostic=f'JUnit report unavailable: {path.name}: {error}')
        for case in (e for e in tree.iter() if local_tag(e) == 'testcase'):
            tags = {local_tag(e) for e in case}
            result['tests'] += 1
            for tag, key in [('failure', 'failures'), ('error', 'errors'), ('skipped', 'skipped')]:
                result[key] += int(tag in tags)
    return result


def parse_unittest(output: str) -> dict:
    """Reads the final 'Ran N tests ... OK/FAILED (...)' summary of Python unittest."""
    matches = list(re.finditer(r'^Ran (\d+) tests? in [^\r\n]+\r?\n', output, re.M))
    # Multiple summaries could conceal earlier failures; require one run per command.
    if len(matches) != 1:
        return {}
    summary = output[matches[0].end():].strip()
    end = re.fullmatch(r'(OK|FAILED)(?: \(([^\r\n]*)\))?', summary)
    if not end:
        return {}
    result = dict(tests=int(matches[0][1]), failures=0, errors=0, skipped=0)
    for key, value in re.findall(r'([a-z ]+)=(\d+)', end[2] or ''):
        key = key.strip()
        if key in result:
            result[key] = int(value)
        elif key in {'expected failures', 'unexpected successes'}:
            result['skipped'] += int(value)
        else:
            result['diagnostic'] = 'Unrecognized unittest outcome'
    if end[1] == 'FAILED' and not result['failures'] and not result['errors']:
        result['errors'] = 1
    return result


def final_status(result: dict, returncode: int) -> str:
    """Final status of one test run. The order of checks matters: the first match wins."""
    if returncode != 0:
        return 'failed'
    if result.get('diagnostic') or result['tests'] is None:
        return 'unknown'
    if result['failures'] or result['errors']:
        return 'failed'
    if result['tests'] == 0:
        return 'empty'
    if result['skipped']:
        return 'skipped'
    return 'passed'


def descendants(sessions: dict, root: str) -> set[str]:
    """Returns root and every session below it (children, grandchildren, ...)."""
    allowed = {root}
    while True:
        more = {sid for sid, items in sessions.items() if items[0]['info'].get('parentID') in allowed}
        if more <= allowed:
            return allowed
        allowed |= more


def text_or_unknown(value) -> str:
    """Returns a non-empty string as is, anything else as 'unknown'."""
    return value if isinstance(value, str) and value else 'unknown'


def message_model(info: dict) -> tuple[str, str]:
    """Provider and model of one assistant message, in the legacy or the V2 format."""
    model_ref = info.get('model') if isinstance(info.get('model'), dict) else {}
    provider = info.get('providerID', model_ref.get('providerID'))
    model = info.get('modelID', model_ref.get('id'))
    return text_or_unknown(provider), text_or_unknown(model)


def new_usage_row(provider: str, model: str) -> dict:
    """An empty report row for one provider/model pair."""
    if provider == 'lmstudio':
        group = 'local'
    elif (provider == 'openrouter' and model.endswith(':free')) or (provider == 'opencode' and model.endswith('-free')):
        # OpenRouter marks its zero-price variants with ":free" (rate limited, no API fee).
        group = 'free'
    elif provider == 'unknown':
        group = 'unknown'
    else:
        group = 'paid'
    return dict(provider=provider, model=model, group=group, messages=0, missing_usage=0,
                **dict.fromkeys(TOKEN_FIELDS, 0))


def message_tokens(info: dict) -> dict:
    """Five token counters of one message; a missing or invalid counter becomes None."""
    tokens = info.get('tokens') if isinstance(info.get('tokens'), dict) else {}
    cache = tokens.get('cache') if isinstance(tokens.get('cache'), dict) else {}
    values = dict(input=tokens.get('input'), output=tokens.get('output'), reasoning=tokens.get('reasoning'),
                  cache_read=cache.get('read'), cache_write=cache.get('write'))
    return {k: v if type(v) is int and v >= 0 else None for k, v in values.items()}


def add_usage(row: dict, values: dict) -> None:
    """Adds one message to a row. One unknown value makes that column's sum unknown for good."""
    row['messages'] += 1
    row['missing_usage'] += int(values['input'] is None or values['output'] is None)
    for field, value in values.items():
        row[field] = None if value is None or row[field] is None else row[field] + value


def fresh_xml_files(folder: Path, since: float) -> list[Path]:
    """
    XML files under folder (recursively) written at or after `since` (Unix time).

    Older files are left from previous runs and must not be counted again.
    Two seconds of tolerance cover file systems that store time with low precision.
    """
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.rglob('*.xml') if p.is_file() and p.stat().st_mtime >= since - 2)


def run_category(parsed: dict, returncode: int) -> str:
    """
    What a test run means for the build loop.

    The key question is whether the tests actually ran. Failing tests are a code or
    test problem and can be sent back to the executor. No readable result means the
    project could not be built or the test tool is not set up; the executor cannot fix that
    unless the log shows a compile error in its own code.
    """
    if parsed['status'] == 'timeout':
        return CATEGORY_TIMEOUT
    if parsed['status'] == 'passed':
        return CATEGORY_PASSED
    ran = parsed.get('tests') and not parsed.get('diagnostic')
    if ran and (parsed.get('failures') or parsed.get('errors')):
        return CATEGORY_FAILED
    if ran and returncode == 0 and parsed.get('skipped'):
        return CATEGORY_INCOMPLETE
    return CATEGORY_NO_RESULT


def since_last_resume(events: list[dict]) -> list[dict]:
    """Events after the last 'resume'; all events if the task was never resumed."""
    for index in range(len(events) - 1, -1, -1):
        if events[index]['kind'] == 'resume':
            return events[index + 1:]
    return events


def is_halted(events: list[dict]) -> dict | None:
    """The active 'halt' event, or None. A later 'resume' cancels a halt."""
    for event in reversed(events):
        if event['kind'] == 'resume':
            return None
        if event['kind'] == 'halt':
            return event
    return None


def trailing(tests: list[dict], categories: set[str]) -> int:
    """How many of the last test runs in a row fall into the given categories."""
    count = 0
    for event in reversed(tests):
        if event.get('category') not in categories:
            break
        count += 1
    return count


def limit_breach(events: list[dict], limits: dict) -> str | None:
    """
    Checks the loop guards against the journal. Returns a human-readable reason or None.

    Only events after the last 'resume' count: after the user's decision every guard
    starts from zero.
    """
    recent = [normalize_work_item(event) for event in since_last_resume(events)]
    tests = [e for e in recent if e['kind'] == 'test']
    reworks, failures = {}, {}
    for event in recent:
        if event['kind'] == 'review' and event['result'] == 'rework':
            reworks[event['work_item']] = reworks.get(event['work_item'], 0) + 1
        elif event['kind'] == 'review' and event['result'] == 'failed':
            failures[event['work_item']] = failures.get(event['work_item'], 0) + 1
    for work_item, count in reworks.items():
        if count >= limits['max_reworks']:
            return (f'{work_item} was sent back {count} times (limit {limits["max_reworks"]}). '
                    f'The spec or the tests may be wrong.')
    # A failed attempt is not a rework, but endless retries of a broken executor must stop too.
    for work_item, count in failures.items():
        if count >= limits['max_reworks']:
            return (f'The executor failed {count} times on {work_item} without changing files '
                    f'(limit {limits["max_reworks"]}). Check that the executor model is available.')
    no_result = trailing(tests, {CATEGORY_NO_RESULT, CATEGORY_TIMEOUT})
    if no_result >= limits['max_no_result']:
        return (f'{no_result} test runs in a row gave no readable result (limit {limits["max_no_result"]}). '
                f'The project does not build or the test tool is not set up.')
    # A module's red tests must not accumulate with unrelated modules or the initial baseline.
    for scope in sorted({e.get('scope', 'full') for e in tests}):
        scoped = [e for e in tests if e.get('phase') != 'baseline' and
                  (e.get('scope', 'full') == scope or
                   (e.get('scope', 'full') == 'full' and e['status'] == 'passed'))]
        failed = trailing(scoped, {CATEGORY_FAILED, CATEGORY_INCOMPLETE, CATEGORY_NO_RESULT, CATEGORY_TIMEOUT})
        if failed >= limits['max_failed_runs']:
            return (f'{failed} test runs in a row were not green in {scope} '
                    f'(limit {limits["max_failed_runs"]}).')
    if len(tests) >= limits['max_runs']:
        return f'{len(tests)} test runs in this task (limit {limits["max_runs"]}).'
    return None


def task_limits(events: list[dict]) -> dict:
    """Limits stored in the start event; defaults for journals written before limits existed."""
    stored = events[0].get('limits')
    return dict(DEFAULT_LIMITS, **(stored if isinstance(stored, dict) else {}))


def diagnose(output: str, returncode: int, parsed: dict, category: str, junit_given: bool) -> list[str]:
    """Plain hints for a test run that gave no readable result. Used by `check` and `test`."""
    if category not in {CATEGORY_NO_RESULT, CATEGORY_TIMEOUT} and parsed['status'] != 'empty':
        return []
    text = output.lower()
    hints = []
    if returncode == 127:
        hints.append('The test program was not found. Check that it is installed and on PATH.')
    if category == CATEGORY_TIMEOUT:
        hints.append('The command did not finish. Test tools in watch mode never exit: '
                     'use "vitest run", "jest --ci" or "--watchAll=false"; or raise --timeout.')
    if 'could not find a test logger' in text:
        hints.append('dotnet test cannot find the JUnit logger: '
                     'run "dotnet add <TestProject> package JunitXml.TestLogger".')
    if any(marker in text for marker in ('build failed', 'build error', 'compilation error', 'compilation failed')) \
            or re.search(r'error (cs|ts)\d+', text):
        hints.append('The project does not compile. If the error is in code the executor just wrote, '
                     'send that work_item back; otherwise fix the project or ask the user.')
    if parsed['status'] == 'empty':
        hints.append('No tests were found. Check the test folder, file names and test filters.')
    if parsed.get('diagnostic', '').startswith('No JUnit XML'):
        hints.append('The command did not write a JUnit XML report. Check the report flag and path '
                     'in the test command (Project stack in AGENTS.md).')
    elif not junit_given and parsed['tests'] is None:
        hints.append('The output format is not recognized. Use --junit <file> or --junit-dir <folder> '
                     'so the runner can read a JUnit XML report.')
    return hints or ['Read the test log to find the cause.']

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest='action', required=True)
    start = sub.add_parser('start')
    start.add_argument('--session')
    start.add_argument('--title')
    start.add_argument('--track-delegations', action='store_true', help='require registered executor attempts for reviews')
    start.add_argument('--no-dashboard', action='store_true', help='disable the automatic dashboard for this start')
    start.add_argument('--no-browser', action='store_true', help='start/reuse the dashboard without opening a browser')
    for name in DEFAULT_LIMITS:
        start.add_argument('--' + name.replace('_', '-'), type=int, dest=name,
                            help=f'loop guard, default {DEFAULT_LIMITS[name]}')
    review = sub.add_parser('review')
    review.add_argument('--work-item', '--piece', dest='work_item', required=True)
    review.add_argument('--result', choices=sorted(REVIEW_RESULTS), required=True,
                        help='failed = the executor returned no work and changed no files; not a rework')
    review.add_argument('--checks', type=Path, help='JSON requirement/code/test checklist for acceptance')
    delegation = sub.add_parser('delegate')
    delegation.add_argument('--work-item', '--piece', dest='work_item', required=True)
    delegation.add_argument('--files', nargs='+', required=True)
    delegation.add_argument('--scope', help='test scope; defaults to the work item name')
    delegation.add_argument('--requirements', type=Path, required=True, help='JSON list frozen before the executor call')
    inspect = sub.add_parser('inspect')
    inspect.add_argument('--work-item', '--piece', dest='work_item', required=True)
    resume = sub.add_parser('resume')
    resume.add_argument('--reason', required=True)
    test = sub.add_parser('test')
    test.add_argument('--scope', default='full', help='work-item/module name or full for the complete suite')
    test.add_argument('--phase', choices=['work', 'baseline'], default='work')
    test.add_argument('--attempt', help='exact isolated delegation ID for this test result')
    check = sub.add_parser('check')
    for command in (test, check):
        command.add_argument('--timeout', type=float, default=300)
        command.add_argument('--junit')
        command.add_argument('--junit-dir')
        command.add_argument('command', nargs=argparse.REMAINDER)
    finish = sub.add_parser('finish')
    finish.add_argument('--language', choices=('en', 'ru'), help='report language; otherwise saved UI preference or system language')
    finish.add_argument('--export', action='append', dest='exports')
    finish.add_argument('--opencode', default='opencode')
    for command in (start, delegation, inspect, review, resume, test, finish):
        command.add_argument('--task', required=True)
    return parser


class TaskMetrics:
    """One writer per task. Data is stored in project/.metrics/task/.

    The class provides methods to start a task, record reviews and test runs,
    and finish the task with a usage report.
    It handles file locking to prevent concurrent writes
    and validates input data for correctness.

    Calling finish again for a finished task returns the same report without
    recounting; the report is written to report.md in the task directory.
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

            return [normalize_work_item(event) for event in events]
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

    def start(self, task: str, session: str | None = None, title: str | None = None,
              limits: dict | None = None, track_delegations: bool = False) -> dict:
        if session is not None:
            session_id(session)
        limits = dict(DEFAULT_LIMITS, **{k: v for k, v in (limits or {}).items() if v is not None})
        if set(limits) != set(DEFAULT_LIMITS) or any(type(v) is not int or v < 1 for v in limits.values()):
            raise ValueError('Limits must be positive integers: ' + ', '.join(DEFAULT_LIMITS))
        self.task_dir(task).mkdir(parents=True, exist_ok=False)
        with self.lock(task):
            # session=session puts the value into append's **data as the "session" key;
            # session_id(session) above has already validated it.
            server = {}
            if os.environ.get('OPENCODE_KIT_ROOT') and Path(os.environ['OPENCODE_KIT_ROOT']).resolve() == self.root:
                server['server_mode'] = os.environ.get('OPENCODE_KIT_SERVER_MODE', 'unknown')
            return self.append(task, 'start', session=session, title=title or task, limits=limits,
                               track_delegations=track_delegations, **server)

    # check if the task is active (not finished) and return its events
    def active(self, task):
        events = self.read(task)
        if any(e['kind'] == 'finish' for e in events):
            raise ValueError('Task is finished; start a new task ID')
        return events

    def running(self, task):
        """Events of an active task that is not stopped by a loop guard; raises TaskHalted otherwise."""
        events = self.active(task)
        reason = blocking_reason(self.root, task)
        if reason:
            raise TaskHalted(reason)
        halt = is_halted(events)
        if halt:
            raise TaskHalted(halt['reason'])
        return events

    def guard(self, task: str, events: list[dict]) -> dict | None:
        """Appends a 'halt' event if a loop guard is reached. Returns that event or None."""
        reason = limit_breach(events, task_limits(events))
        return self.append(task, 'halt', reason=reason) if reason else None

    def attempt_root(self, task: str, attempt: dict) -> Path:
        """Only controller-owned plain directories may hold isolated edits."""
        if not attempt.get('workspace'):
            return self.root
        path = self.root / attempt['workspace']
        base = self.task_dir(task) / 'workspaces'
        if path.resolve() != path.absolute() or not path.resolve().is_relative_to(base.resolve()) or not path.is_dir():
            raise ValueError('Invalid isolated workspace')
        return path

    def delegate(self, task: str, work_item: str, files: list[str], scope: str | None = None,
                 requirements: Path | None = None, *, workspace: str | None = None,
                 worker_id: str | None = None, role: str = 'executor', contracts: list[str] | None = None) -> dict:

        """Log one executor attempt and save pre-execution file hashes.

        work item names the task; files must identify one unique allowed file.
        scope names the test scope and defaults to work_item.
        Each retry after review is a new attempt.
        """
        # Require a work item name, file list and non-blank effective test scope.
        if not work_item.strip() or not files or not (scope or work_item).strip():
            raise ValueError('Delegation needs a work item, files and a non-empty test scope')

        # Validate paths and remove duplicate file names.
        target = self.attempt_root(task, {'workspace': workspace})
        allowed = sorted({source_path(target, name) for name in files})

        # Allow exactly one unique file per attempt.
        if len(allowed) != 1:
            raise ValueError('Delegate exactly one source file per executor attempt')
        frozen = read_requirements(self.root / requirements) if requirements else []
        with self.lock(task):
            events = self.running(task)
            if events[0].get('track_delegations') and not frozen:
                raise ValueError('Tracked delegation requires a requirements file')
            # Any review (accepted, rework or failed) closes an attempt.
            closed = {e.get('delegation_id') for e in events if e['kind'] == 'review'}
            pending = pending_attempts(events)
            details = {}
            if workspace:
                from .execution_policy import normalize_policy
                from .run_opencode import load_choices
                settings = self.task_dir(task) / 'execution-settings.json'
                choices = json.loads(settings.read_text(encoding='utf-8')) if settings.exists() else load_choices(self.root)
                policy = normalize_policy(choices.get('execution'))
                if role not in ('executor', 'bug_fixer') or not worker_id:
                    raise ValueError('Isolated attempts need a worker identity and role')
                if (any(not e.get('workspace') or e['work_item'] == work_item or e.get('worker_id') == worker_id for e in pending)
                        or len(pending) >= policy['maxExecutors']
                        or any(e.get('workspace') == workspace for e in events if e['kind'] == 'delegation')):
                    raise ValueError('Worker slot, work item or workspace is already in use')
                accepted = {e.get('delegation_id') for e in events if e['kind'] == 'review' and e['result'] == 'accepted'}
                integrated = {e.get('delegation_id') for e in events if e['kind'] == 'integration'}
                reserved = pending + [e for e in events if e['kind'] == 'delegation' and e['event_id'] in accepted - integrated]
                if any(set(e['files']) & set(allowed) for e in reserved):
                    raise ValueError('Source file is already assigned or awaiting integration')
                contract_paths = sorted({source_path(self.root, p) for p in (contracts or [])})
                if policy['maxExecutors'] > 1 and not contract_paths:
                    raise ValueError('Parallel work requires explicit shared contracts')
                base = snapshot(self.root)
                details = dict(workspace=workspace, worker_id=worker_id, role=role,
                               base_hashes={p: base.get(p) for p in allowed + contract_paths},
                               contracts=contract_paths)
            elif pending:
                raise ValueError('Review the pending delegation before starting another')
            before = snapshot(target)
            filename = 'before-' + uuid.uuid4().hex + '.json'
            (self.task_dir(task) / filename).write_text(json.dumps(before), encoding='utf-8')
            return self.append(task, 'delegation', work_item=work_item.strip(), files=allowed,
                               scope=(scope or work_item).strip(), snapshot=filename, requirements=frozen, **details)

    def inspect(self, task: str, work_item: str) -> dict:
        """Save file changes for the pending attempt; refuse a second inspection.

        The Master Chief must call this after the executor returns, before its own edits.
        """
        with self.lock(task):
            events = self.running(task)
            closed = {e.get('delegation_id') for e in events if e['kind'] == 'review'}
            attempts = pending_attempts(events, work_item)
            if len(attempts) != 1:
                raise ValueError('Inspect must match the pending delegated work item')
            attempt = attempts[-1]
            if attempt.get('workspace') and not any(e['kind'] == 'attempt_end' and e['delegation_id'] == attempt['event_id']
                                                   and e.get('stopped') is True for e in events):
                raise ValueError('Confirm that this isolated worker stopped before inspection')
            if any(e['kind'] == 'inspection' and e['delegation_id'] == attempt['event_id'] for e in events):
                raise ValueError('Executor edits already inspected; do not overwrite the evidence')
            before = json.loads((self.task_dir(task) / attempt['snapshot']).read_text(encoding='utf-8'))
            after = snapshot(self.attempt_root(task, attempt))
            changes = compare(before, after, attempt['files'])
            filename = 'after-' + uuid.uuid4().hex + '.json'
            (self.task_dir(task) / filename).write_text(json.dumps(after), encoding='utf-8')
            return self.append(task, 'inspection', delegation_id=attempt['event_id'], work_item=work_item,
                               snapshot=filename, **changes)

    def review(self, task: str, work_item: str, result: str, checks: Path | None = None) -> dict:
        """Record the Master Chief's accepted/rework/failed decision and check acceptance evidence.

        Acceptance requires allowed edits, matching requirement checks and a green
        scoped/full run on unchanged files. "failed" means the executor returned no work
        (error, rate limit, unavailable model): it is allowed only when the attempt changed
        no files and it is not counted as a rework. This method does not call the Master
        Chief, review source code or run tests. Legacy tasks may have no delegation.
        """

        work_item = work_item.strip()
        if not work_item or result not in REVIEW_RESULTS:
            raise ValueError('Review requires a work item and accepted/rework/failed result')
        
        with self.lock(task):
            events = self.running(task)
            closed = {e.get('delegation_id') for e in events if e['kind'] == 'review'}
            # pending delegations are those that have not been reviewed yet; we need to find the last one for this work item
            pending = pending_attempts(events, work_item)
            evidence = {}
            if pending_attempts(events) and not pending:
                raise ValueError('Review must match the pending delegated work item')
            # if the task is tracking delegations, we must have a pending delegation to review; otherwise, raise an error
            if events[0].get('track_delegations') and not pending:
                raise ValueError('Register the executor attempt with delegate before reviewing')
            
            if pending:
                attempt = pending[-1]
                if attempt['work_item'] != work_item:
                    raise ValueError('Review must match the pending delegated work item')
                
                before = json.loads((self.task_dir(task) / attempt['snapshot']).read_text(encoding='utf-8'))
                after = snapshot(self.attempt_root(task, attempt))
                inspections = [e for e in events if e['kind'] == 'inspection' and
                               e['delegation_id'] == attempt['event_id']]
                # compare function may create unexpected changes if the executor changed files that were not allowed; we need to check for that
                changes = compare(before, after, attempt['files'])

                if inspections:
                    inspected = inspections[-1]
                    changes = {k: inspected[k] for k in ('changed', 'unexpected')}
                    frozen = json.loads((self.task_dir(task) / inspected['snapshot']).read_text(encoding='utf-8'))
                    subsequent = compare(frozen, after, [])['changed']
                    changes['reviewer_changes'] = subsequent
                    if result == 'accepted' and any(p in attempt['files'] for p in subsequent):
                        raise ValueError('Delegated source changed after inspection; register a fresh attempt')
                    
                elif result == 'accepted' and events[0].get('track_delegations'):
                    raise ValueError('Run inspect immediately after the executor returns, before reviewer edits')
                
                evidence = dict(delegation_id=attempt['event_id'], **changes)

                if result == 'failed' and changes['changed']:
                    raise ValueError('The executor changed files: review the attempt as accepted or rework, '
                                     'not failed: ' + ', '.join(changes['changed']))

                if result == 'accepted':
                    if changes['unexpected']:
                        raise ValueError('Executor changed unexpected files: ' + ', '.join(changes['unexpected']))
                    # check that the review checks cover every frozen requirement exactly once
                    if checks is None:
                        raise ValueError('Acceptance needs --checks with requirement/code/test evidence')
                    evidence['checks'] = review_checks(self.root / checks)
                    # validate that the review checks cover every frozen requirement exactly once
                    if attempt.get('requirements') and (
                            len(evidence['checks']) != len(attempt['requirements']) or
                            {c['requirement'] for c in evidence['checks']} != set(attempt['requirements'])):
                        raise ValueError('Review checks must cover every frozen requirement exactly once')
                    anchor = inspections[-1] if inspections else attempt

                    # find all test runs after the delegation (or inspection) for this scope, ignoring baseline runs
                    runs = [e for e in events[events.index(anchor) + 1:] if e['kind'] == 'test'
                            and e.get('phase') != 'baseline'
                            and e.get('scope', 'full') in {attempt['scope'], 'full'}
                            and (e.get('delegation_id') == attempt['event_id'] if attempt.get('workspace')
                                 else not e.get('delegation_id'))]
                    # check that the last test run after delegation was green; if not, the tests must be rerun before acceptance
                    if not runs or runs[-1]['status'] != 'passed':
                        raise ValueError('Acceptance needs a green test run for this scope after delegation')
                    # check that the project files have not changed since the last green test run; if they have, the tests must be rerun before acceptance
                    tested = json.loads((self.task_dir(task) / runs[-1]['snapshot']).read_text(encoding='utf-8'))
                    if compare(tested, after, [])['changed']:
                        raise ValueError('Project files changed since the green test; rerun tests before acceptance')
                    
            event = self.append(task, 'review', work_item=work_item, result=result, **evidence)
            halt = self.guard(task, events + [event])
            return dict(event, halt=halt['reason']) if halt else event

    def resume(self, task: str, reason: str) -> dict:
        """
        Lifts a stop after the user's decision. The reason is kept in the journal and the report.
        Every loop guard counts from zero again after this event.
        """
        if not reason.strip():
            raise ValueError('Resume requires a reason: what the user decided')
        with self.lock(task):
            events = self.active(task)
            if not is_halted(events):
                raise ValueError('Task is not stopped; nothing to resume')
            return self.append(task, 'resume', reason=reason.strip())

    # parse the output of a test run, optionally using JUnit XML reports to extract test results
    def parse_tests(self, output: str, returncode: int, junit: Path | list[Path] | None = None) -> dict:
        if junit is not None:
            counts = parse_junit_files([junit] if isinstance(junit, Path) else list(junit))
        else:
            counts = parse_unittest(output)
        result = dict(tests=None, failures=None, errors=None, skipped=None)
        result.update(counts)
        result['status'] = final_status(result, returncode)
        return result

    def report_source(self, junit: str | None, junit_dir: str | None):
        """
        Validates where JUnit results come from. Returns (file, folder): at most one is set.

        A single file must not exist before the run, so an old green report is never read
        as a new one. A folder may exist: only files written during the run are read.
        """
        if junit and junit_dir:
            raise ValueError('Use either --junit or --junit-dir, not both')
        target = (self.root / (junit or junit_dir)).resolve() if (junit or junit_dir) else None
        if target and not target.is_relative_to(self.root):
            raise ValueError('JUnit path must be inside the project')
        if junit and target.exists():
            raise ValueError('JUnit file must not exist before the run; use a new name for every run')
        return (target, None) if junit else (None, target)

    def execute(self, command: list[str], timeout: float, xml: Path | None, folder: Path | None):
        """Runs the test command once and reads its results. Returns (output, code, parsed, category)."""
        if not command or not valid_number(timeout) or timeout == 0:
            raise ValueError('Provide a command and a finite positive timeout')
        started_wall = time.time()
        output, code, timed_out = run_command(resolve_command(command), self.root, timeout)
        if folder is not None:
            report = fresh_xml_files(folder, started_wall)
        elif xml is not None:
            report = [xml] if xml.exists() else []
        else:
            report = None
        parsed = self.parse_tests(output, code, report)
        if timed_out:
            parsed['status'] = 'timeout'
        return output, code, parsed, run_category(parsed, code)

    # run a test command for a task, capturing its output and return code, and optionally parsing JUnit XML reports
    def test(self, task: str, command: list[str], timeout: float = 300, junit: str | None = None,
             junit_dir: str | None = None, scope: str = 'full', phase: str = 'work', attempt_id: str | None = None) -> dict:
        if not scope.strip() or phase not in {'work', 'baseline'}:
            raise ValueError('Provide a non-empty scope and work/baseline phase')
        scope = scope.strip()
        with self.lock(task):
            events = self.running(task)
            runner, binding = self, {}
            if attempt_id:
                candidates = [e for e in pending_attempts(events) if e['event_id'] == attempt_id and e.get('workspace')]
                if len(candidates) != 1 or scope != candidates[0]['scope']:
                    raise ValueError('Tests must match one open isolated attempt and its scope')
                runner = TaskMetrics(self.attempt_root(task, candidates[0]))
                binding['delegation_id'] = attempt_id
            elif any(e.get('workspace') for e in pending_attempts(events)):
                raise ValueError('Use --attempt while isolated workers await review')
            xml, folder = runner.report_source(junit, junit_dir)
            if phase == 'baseline' and any(
                    (e['kind'] == 'delegation' and e.get('scope') == scope) or
                    (e['kind'] == 'test' and e.get('scope', 'full') == scope) for e in events):
                raise ValueError('Baseline is allowed only once per scope, before its delegations and tests')
            evidence = {}
            closed = {e.get('delegation_id') for e in events if e['kind'] == 'review'}
            if pending_attempts(events) or any(e['kind'] == 'integration' for e in events):
                filename = 'tested-' + uuid.uuid4().hex + '.json'
                (self.task_dir(task) / filename).write_text(json.dumps(snapshot(runner.root)), encoding='utf-8')
                evidence['snapshot'] = filename
            started = time.monotonic()
            output, code, parsed, category = runner.execute(command, timeout, xml, folder)
            log = 'test-' + uuid.uuid4().hex + '.log'
            (self.task_dir(task) / log).write_text(output, encoding='utf-8')
            hints = diagnose(output, code, parsed, category, bool(xml or folder))
            event = self.append(task, 'test', command=command, returncode=code, log=log, scope=scope, phase=phase,
                                duration_seconds=time.monotonic()-started, category=category,
                                 **({'hints': hints} if hints else {}), **binding, **evidence, **parsed)
            halt = self.guard(task, events + [event])
            return dict(event, halt=halt['reason']) if halt else event

    def check(self, command: list[str], timeout: float = 300, junit: str | None = None,
              junit_dir: str | None = None) -> dict:
        """
        Dry run of the test command without a task: can the runner read its results?

        Used once when the kit is connected to a project and before each implementation task.
        A single JUnit file written by the check is removed, so the same name can be used again.
        """
        xml, folder = self.report_source(junit, junit_dir)
        output, code, parsed, category = self.execute(command, timeout, xml, folder)
        if xml is not None and xml.exists():
            xml.unlink()
        readable = category in {CATEGORY_PASSED, CATEGORY_FAILED, CATEGORY_INCOMPLETE}
        return dict(readable=readable, category=category, returncode=code, output=output,
                    hints=diagnose(output, code, parsed, category, bool(xml or folder)), **parsed)

    # parse OpenCode exports for a task, filtering messages by time and collecting token usage statistics
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
        allowed = descendants(sessions, session)

        warnings_list = []
        for sid in sessions.keys() - allowed:
            warnings_list.append(f'Посторонняя сессия исключена: {sid}')
        rows, seen, session_rows = {}, {}, {}

        for sid in sorted(allowed):
            for export in sessions[sid]:
                warnings_list.extend(export.get('_metrics_warnings', []))
                for child in master_chief_tool_child_references(export) - allowed:
                    warnings_list.append(f'Нет выгрузки дочерней сессии: {child}')
                for message in export['messages']:
                    info = message_info(message)
                    if info.get('role', info.get('type')) != 'assistant':
                        continue
                    mid = info.get('id')
                    stamp = info.get('time', {})
                    if not isinstance(stamp, dict) or not isinstance(mid, str) or not valid_number(stamp.get('created')):
                        warnings_list.append(f'Пропущено сообщение без ID/времени: {sid}')
                        continue
                    if not since <= stamp['created']/1000 <= until:
                        continue
                    if not valid_number(stamp.get('completed')) or stamp['completed']/1000 > until:
                        warnings_list.append('Незавершённые на момент отчёта сообщения не включены.')
                        continue
                    key = (sid, mid)
                    if key in seen:
                        if seen[key] != info:
                            raise ValueError(f'Conflicting duplicate message: {sid}/{mid}')
                        continue
                    seen[key] = info
                    provider, model = message_model(info)
                    row = rows.setdefault((provider, model), new_usage_row(provider, model))
                    add_usage(row, message_tokens(info))
                    per_session = session_rows.setdefault((sid, provider, model), dict(new_usage_row(provider, model), session=sid, cost_usd=0))
                    add_usage(per_session, message_tokens(info))
                    cost = info.get('cost')
                    per_session['cost_usd'] = (per_session['cost_usd'] + cost
                        if per_session['cost_usd'] is not None and valid_number(cost) else None)
        warnings_list.append('Учтены сообщения в интервале задачи; служебные вызовы вне экспорта могут отсутствовать.')
        if any(r['missing_usage'] for r in rows.values()):
            warnings_list.append('В части сообщений нет корректного расхода токенов; соответствующие суммы неизвестны.')
        return dict(models=list(rows.values()), warnings=list(dict.fromkeys(warnings_list)), sessions=sorted(allowed),
                    session_usage=list(session_rows.values()))

    # run an OpenCode CLI command and parse its JSON output, raising an error if the command fails or returns non-JSON output
    # for instance: opencode session export ses_abc123
    # it will execute the command and return the parsed JSON output, or raise a ValueError if the command fails or returns invalid JSON
    # this command is used to collect exports for a session and its children, which are then parsed to generate a usage report
    # opencode runs this command and returns the JSON output, which is then processed by collect_exports to gather all relevant data for the task
    def cli_json(self, executable: str, args: list[str]):
        result = subprocess.run([executable, *args], cwd=self.root, stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
        if result.returncode:
            raise ValueError(f'OpenCode {args[0]} failed (exit {result.returncode})')
        try:
            return json.loads(result.stdout.lstrip('\ufeff'))
        except ValueError as error:
            raise ValueError('OpenCode returned non-JSON output; check CLI version/server') from error

    def export_session(self, executable: str, sid: str) -> dict:
        """Export one session, trying the newer CLI command before the legacy one."""
        try:
            export = self.cli_json(executable, ['session', 'export', sid])
        except ValueError:
            export = self.cli_json(executable, ['export', sid])
        if not isinstance(export, dict) or export.get('info', {}).get('id') != sid:
            raise ValueError('Export session ID mismatch')
        if not isinstance(export.get('messages'), list):
            raise ValueError('Export messages missing')
        return export

    def api_children(self, executable: str, sid: str, children: set[str] | None = None) -> set[str]:
        """Read child sessions, preserving discovered IDs in the supplied set on failure."""
        if children is None:
            children = set()
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
                return children
            if cursor in cursors:
                raise ValueError('Repeated pagination cursor')
            cursors.add(cursor)
        raise ValueError('Too many session pages')

    # collect OpenCode exports for a session and its children, using the CLI to fetch data and handling pagination and errors
    def collect_exports(self, session: str, executable: str = 'opencode') -> list[dict]:
        session_id(session)
        executable = resolve_opencode(executable)
        queue, seen, exports = [session], set(), []
        while queue:
            sid = session_id(queue.pop(0))
            if sid in seen:
                continue
            if len(seen) >= 100:
                raise ValueError('More than 100 sessions; narrow task scope')
            seen.add(sid)
            try:
                export = self.export_session(executable, sid)
                children = master_chief_tool_child_references(export)
                try:
                    self.api_children(executable, sid, children)
                except (ValueError, OSError, subprocess.TimeoutExpired) as error:
                    export['_metrics_warnings'] = [f'Поиск дочерних сессий неполон: {error}']
                queue.extend(sorted(children - seen))
                exports.append(export)
            except (OSError, subprocess.TimeoutExpired) as error:
                raise ValueError(f'Cannot collect OpenCode session {sid}: {error}') from error
        return exports

    # We print a Markdown report for a task, summarizing its events, usage statistics, and test results
    # The report includes sections for paid models, local models, and unknown providers, as well as counts of reviews and test outcomes.
    def render(self, task: str, events: list[dict], usage: dict, ended: float, language: str = 'ru') -> str:
        """Render frozen facts in one language; never translate task or worker text."""
        if __package__:
            from . import localization
        else:
            import localization
        def t(key, **values):
            return localization.text(key, language, **values)
        def label(value):
            return str(value).replace('|', '\\|').replace('\r', ' ').replace('\n', ' ').replace('<', '&lt;').replace('>', '&gt;')
        def count(value):
            return t('no data') if value is None else f'{value:,}'.replace(',', ' ' if language == 'ru' else ',')
        duration = max(0, int(ended - events[0]['at']))
        reviews = [e for e in events if e['kind'] == 'review']
        tests = [e for e in events if e['kind'] == 'test']
        lines = [t('## 📊 Task report · {title}', title=label(events[0]['title'])), '',
                 t('⏱ Time: **{minutes} min {seconds} sec**', minutes=duration // 60, seconds=duration % 60), '']
        for group, heading in [('paid', 'Paid models'), ('local', 'Free / local · LM Studio'),
                               ('free', 'Free cloud · OpenRouter / OpenCode'), ('unknown', 'Unknown provider')]:
            rows = [r for r in usage['models'] if r['group'] == group]
            if group in ('free', 'unknown') and not rows:
                continue
            lines += ['### ' + t(heading), '']
            if not rows:
                lines += [t('No calls recorded for this group in the selected interval.'), '']
                continue
            lines += [t('| Model | Input | Output | Reasoning | Cache: read | Cache: write |'), '|---|---:|---:|---:|---:|---:|']
            for row in rows:
                lines.append('| ' + label(row['provider'] + '/' + row['model']) + ' | ' +
                             ' | '.join(count(row[f]) for f in TOKEN_FIELDS) + ' |')
            lines.append('')
        work_tests = [e for e in tests if e.get('phase') != 'baseline']
        lines += [t('🔁 Rework requests: **{reworks}** · Reviews recorded: **{reviews}**',
                    reworks=sum(e['result'] == 'rework' for e in reviews), reviews=len(reviews)), '']
        failed_attempts = sum(e['result'] == 'failed' for e in reviews)
        if failed_attempts:
            lines += [t('⚠️ Executor failures without a result (error, limit, unavailable model): **{count}**. These are not reworks: no files changed.', count=failed_attempts), '']
        lines += [t('🧪 Fully successful runs: **{passed} of {total}**', passed=sum(e['status'] == 'passed' for e in work_tests), total=len(work_tests)), '']
        if len(work_tests) != len(tests):
            lines += [t('Initial checks before implementation (baseline): **{count}**; excluded from successful work runs.', count=len(tests) - len(work_tests)), '']
        full = [e for e in tests if e.get('scope', 'full') == 'full' and e.get('phase') != 'baseline']
        lines += [t('Full suite: **{passed} of {total}**. Other runs may cover a selected class or module.', passed=sum(e['status'] == 'passed' for e in full), total=len(full)), '']
        attempts = [e for e in events if e['kind'] == 'delegation']
        if attempts or events[0].get('track_delegations'):
            closed = {e.get('delegation_id') for e in reviews}
            pending = [e['work_item'] for e in attempts if e['event_id'] not in closed]
            lines += [t('Executor assignments registered: **{total}** · without a recorded review: **{pending}**.', total=len(attempts), pending=len(pending)), '']
            if pending:
                lines += [t('⚠️ Pending reviews: {items}.', items=', '.join(label(p) for p in pending)), '']
        if not full or full[-1]['status'] != 'passed':
            lines += [t('⚠️ The latest full run failed or is missing; overall readiness is unconfirmed.'), '']
        no_result = [e for e in tests if e.get('category') in {CATEGORY_NO_RESULT, CATEGORY_TIMEOUT}]
        if no_result:
            lines += [t('⚙️ Runs without a readable result (build, environment or timeout): **{count}**. These are not executor errors.', count=len(no_result)), '']
        halts = [e for e in events if e['kind'] == 'halt']
        if halts:
            resumes = [e for e in events if e['kind'] == 'resume']
            lines += [t('⛔ Protective stops: **{stops}** · resumes after user decisions: **{resumes}**', stops=len(halts), resumes=len(resumes)), '']
            lines += [t('- Stop: {reason}', reason=label(e['reason'])) for e in halts]
            lines += [t('- Resume: {reason}', reason=label(e['reason'])) for e in resumes]
            lines.append('')
        if tests:
            last = tests[-1]
            lines += [t('Last run: **{status}** · tests: {tests} · failures: {failures} · errors: {errors} · skipped: {skipped}.',
                        status=label(last['status']), **{key: count(last[key]) for key in ('tests', 'failures', 'errors', 'skipped')}), '']
        else:
            lines += [t('No tests were run through the utility; success is unconfirmed.'), '']
        bindings = [e for e in events if e['kind'] == 'attempt_session']
        if bindings:
            lines += [t('### Usage by attempt (included in the total)'), '',
                      t('| Role / worker | Attempt | Actual model | Input | Output | Cost USD |'), '|---|---|---|---:|---:|---:|']
            for binding in bindings:
                rows = [row for row in usage.get('session_usage', []) if row['session'] == binding['session']]
                totals = {field: sum(row[field] for row in rows) if rows and all(row[field] is not None for row in rows) else None
                          for field in ('input', 'output', 'cost_usd')}
                models = ', '.join(row['provider'] + '/' + row['model'] for row in rows) or t('no data')
                cost = t('no data') if totals['cost_usd'] is None else f'{totals["cost_usd"]:.6f}'
                lines.append(f'| {label(binding["role"])} / {label(binding["worker_id"])} | {label(binding["delegation_id"])} | '
                             f'{label(models)} | {count(totals["input"])} | {count(totals["output"])} | {cost} |')
            lines += ['', t('This breakdown is not added to the total again. Missing cost remains unknown.'), '']
        lines += [t('Time is measured from `start` to `finish`; earlier work is excluded.'),
                  t('Reviews and assignments follow the journal; unregistered actions cannot be detected.'),
                  t('All `lmstudio` models have no API fee; OpenRouter `:free` and OpenCode `-free` models are free cloud models; other known providers are classified as paid by default.'),
                  t('Reasoning and cache tokens are shown separately without adding overlapping counters.'),
                  t('Snapshot taken before the final answer; its tokens are excluded. Catalog-based cost and savings were not calculated.'), '']
        if usage['warnings']:
            warnings = []
            for warning in usage['warnings']:
                if warning.startswith('Токены — нет данных: '):
                    warning = t('Tokens unavailable: {reason}', reason=localization.diagnostic(warning.split(': ', 1)[1], language))
                else:
                    warning = localization.diagnostic(warning, language)
                warnings.append('- ' + label(warning))
            lines += [t('Notes:'), ''] + warnings + ['']
        return '\n'.join(lines)


    # it is our final step to finish a task, collect exports, parse usage, and write a Markdown report to report.md in the task directory
    def finish(self, task: str, export_paths: list[str] | None = None, executable: str = 'opencode', language: str | None = None) -> str:
        if __package__:
            from .localization import load_language
        else:
            from localization import load_language
        language = language or load_language(self.root)
        with self.lock(task):
            reason = blocking_reason(self.root, task)
            if reason:
                raise TaskHalted(reason)
            events = self.read(task)
            finished = next((e for e in events if e['kind'] == 'finish'), None)
            isolated = [e for e in events if e['kind'] == 'delegation' and e.get('workspace')]
            if isolated and not finished:
                if pending_attempts(events):
                    raise ValueError('Resolve all isolated attempts before finish')
                integrated = {e['delegation_id'] for e in events if e['kind'] == 'integration'}
                accepted = {e['delegation_id'] for e in events if e['kind'] == 'review' and e['result'] == 'accepted'}
                if any(e['event_id'] in accepted and e['event_id'] not in integrated for e in isolated):
                    raise ValueError('Integrate accepted isolated attempts before finish')
                latest = {e['work_item']: e for e in isolated}
                if any(e['event_id'] not in accepted & integrated for e in latest.values()):
                    raise ValueError('Every isolated work item needs an accepted, integrated latest attempt')
                runs = [e for e in events if e['kind'] == 'test' and e.get('scope') == 'full' and not e.get('delegation_id')]
                if (not runs or runs[-1]['status'] != 'passed' or not runs[-1].get('snapshot')
                        or compare(json.loads((self.task_dir(task)/runs[-1]['snapshot']).read_text(encoding='utf-8')),
                                   snapshot(self.root), [])['changed']):
                    raise ValueError('Finish needs a green full test of the integrated project')
            if finished:
                report = self.render(task, events, finished['usage'], finished['ended'], language)
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
                report = self.render(task, events, usage, ended, language)
            folder = self.task_dir(task)
            tmp = folder / ('report-'+uuid.uuid4().hex+'.tmp')
            tmp.write_text(report, encoding='utf-8')
            tmp.replace(folder/'report.md')
            return report

def launch_task_dashboard(root: Path, task: str, open_browser: bool) -> dict:
    """Launch from the CLI only; importing/using TaskMetrics stays side-effect free."""
    if __package__:
        from .dashboard.launcher import ensure_dashboard
    else:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from kit.dashboard.launcher import ensure_dashboard
    return ensure_dashboard(root, task, open_browser=open_browser)


def main(argv=None) -> int:
    """
    Command line. Exit codes tell the Master Chief what to do next:
    0 passed or done; 1 tests ran and failed; 4 no readable test result (setup or build);
    3 STOP: a loop guard is reached, ask the user; 2 wrong usage or a broken journal.
    """
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    args = build_parser().parse_args(argv)
    metrics = TaskMetrics(args.root)
    try:
        if args.action == 'start':
            limits = {name: getattr(args, name) for name in DEFAULT_LIMITS}
            event = metrics.start(args.task, args.session, args.title, limits, args.track_delegations)
            if (not args.no_dashboard and os.environ.get('OPENCODE_KIT_DASHBOARD', '').lower() not in ('off', '0')
                    and (metrics.root / 'opencode.jsonc').is_file() and (metrics.root / 'kit').is_dir()):
                try:
                    dashboard = launch_task_dashboard(metrics.root, args.task, not args.no_browser)
                    if not args.no_browser and not dashboard['opened']:
                        print('Dashboard browser did not open: ' + dashboard['url'], file=sys.stderr)
                except (OSError, ValueError, RuntimeError) as error:
                    dashboard = {'status': 'unavailable', 'error': str(error)}
                    print('Dashboard unavailable; task journal was saved: ' + str(error), file=sys.stderr)
                event = dict(event, dashboard=dashboard)
        elif args.action == 'review':
            event = metrics.review(args.task, args.work_item, args.result, args.checks)
        elif args.action == 'delegate':
            event = metrics.delegate(args.task, args.work_item, args.files, args.scope, args.requirements)
        elif args.action == 'inspect':
            event = metrics.inspect(args.task, args.work_item)
        elif args.action == 'resume':
            event = metrics.resume(args.task, args.reason)
        elif args.action == 'finish':
            print(metrics.finish(args.task, args.exports, args.opencode, args.language))
            return EXIT_OK
        elif args.action == 'check':
            command = args.command[1:] if args.command[:1] == ['--'] else args.command
            result = metrics.check(command, args.timeout, args.junit, args.junit_dir)
            print(result.pop('output'))
            print(json.dumps(result, ensure_ascii=False))
            if result['readable']:
                print(f'CHECK OK: the runner reads results ({result["tests"]} tests).', file=sys.stderr)
                return EXIT_OK
            print('CHECK FAILED: the runner cannot read test results.', file=sys.stderr)
            for hint in result['hints']:
                print('- ' + hint, file=sys.stderr)
            return EXIT_NO_RESULT
        else:
            command = args.command[1:] if args.command[:1] == ['--'] else args.command
            event = metrics.test(args.task, command, args.timeout, args.junit, args.junit_dir, args.scope, args.phase, args.attempt)
            print((metrics.task_dir(args.task)/event['log']).read_text(encoding='utf-8'))
            print(json.dumps(event, ensure_ascii=False))
            return report_test(event, args.task)
        print(json.dumps(event, ensure_ascii=False))
        if args.action == 'inspect' and event['unexpected']:
            print('UNEXPECTED EDITS: record rework and inspect these files: ' +
                  ', '.join(event['unexpected']), file=sys.stderr)
            return EXIT_TESTS_FAILED
        if event.get('halt'):
            print_stop(event['halt'], args.task)
            return EXIT_STOP
        return EXIT_OK
    except TaskHalted as halt:
        print_stop(str(halt), args.task)
        return EXIT_STOP
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(f'Metrics error: {error}', file=sys.stderr)
        return EXIT_USAGE


def report_test(event: dict, task: str) -> int:
    """Prints what the Master Chief should do after a test run and returns the exit code."""
    if event.get('halt'):
        print_stop(event['halt'], task)
        return EXIT_STOP
    category = event['category']
    if category == CATEGORY_PASSED:
        return EXIT_OK
    if category in {CATEGORY_FAILED, CATEGORY_INCOMPLETE}:
        print('TESTS FAILED: the tests ran. Read the failures: send the work item back to the executor '
              '(review --result rework) or fix the tests if they contradict the spec.', file=sys.stderr)
        return EXIT_TESTS_FAILED
    print('NO RESULT: the tests did not produce a readable result. Usually this is a setup or build '
          'problem, not an executor mistake. Record a rework only if the log shows a compile error in '
          'code the executor just wrote; otherwise fix the setup or ask the user.', file=sys.stderr)
    for hint in event.get('hints', []):
        print('- ' + hint, file=sys.stderr)
    return EXIT_NO_RESULT


def print_stop(reason: str, task: str) -> None:
    """The STOP message. The Master Chief must end the loop and wait for the user's decision."""
    print(f'STOP: {reason}', file=sys.stderr)
    print('Do not run more tests and do not send more reworks. Tell the user what happened and what '
          'you suggest, then wait. Continue only after the user decides, with: '
          f'task_metrics.py resume --task {task} --reason "<the user\'s decision>"', file=sys.stderr)


if __name__ == '__main__':
    sys.exit(main())
