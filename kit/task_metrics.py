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
EVENT_KINDS = {'start', 'review', 'test', 'halt', 'resume', 'finish'}
WINDOWS_RESERVED = frozenset({'CON', 'PRN', 'AUX', 'NUL',
                              *(f'COM{n}' for n in range(1, 10)), *(f'LPT{n}' for n in range(1, 10))})

# Loop guards. Any of them stops the task until the user decides how to continue.
DEFAULT_LIMITS = dict(
    max_reworks=3,      # returns of one piece to the executor
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

# Exit codes of the command line, so the brain can react without parsing text.
EXIT_OK = 0
EXIT_TESTS_FAILED = 1
EXIT_USAGE = 2
EXIT_STOP = 3
EXIT_NO_RESULT = 4


class TaskHalted(Exception):
    """The task reached a loop guard. The brain must stop and ask the user."""


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


def brain_tool_child_references(export):
    """Find child sessions that the brain started through its tools.

    When the brain calls an executor, OpenCode runs the executor in a separate
    child session. Its messages and tokens are not part of the brain's export,
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
    """Find the desktop or PATH OpenCode CLI when the default name is requested."""
    if executable != 'opencode':
        return executable
    desktop_cli = Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs/@opencodedesktop/resources/opencode-cli.exe'
    try:
        if desktop_cli.is_file():
            return str(desktop_cli)
    except OSError:
        pass
    return shutil.which('opencode') or executable


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
    recent = since_last_resume(events)
    tests = [e for e in recent if e['kind'] == 'test']
    reworks = {}
    for event in recent:
        if event['kind'] == 'review' and event['result'] == 'rework':
            reworks[event['piece']] = reworks.get(event['piece'], 0) + 1
    for piece, count in reworks.items():
        if count >= limits['max_reworks']:
            return (f'{piece} was sent back {count} times (limit {limits["max_reworks"]}). '
                    f'The spec or the tests may be wrong.')
    no_result = trailing(tests, {CATEGORY_NO_RESULT, CATEGORY_TIMEOUT})
    if no_result >= limits['max_no_result']:
        return (f'{no_result} test runs in a row gave no readable result (limit {limits["max_no_result"]}). '
                f'The project does not build or the test tool is not set up.')
    failed = trailing(tests, {CATEGORY_FAILED, CATEGORY_INCOMPLETE, CATEGORY_NO_RESULT, CATEGORY_TIMEOUT})
    if failed >= limits['max_failed_runs']:
        return f'{failed} test runs in a row were not green (limit {limits["max_failed_runs"]}).'
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
                     'send that piece back; otherwise fix the project or ask the user.')
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
    for name in DEFAULT_LIMITS:
        start.add_argument('--' + name.replace('_', '-'), type=int, dest=name,
                            help=f'loop guard, default {DEFAULT_LIMITS[name]}')
    review = sub.add_parser('review')
    review.add_argument('--piece', required=True)
    review.add_argument('--result', choices=['accepted', 'rework'], required=True)
    resume = sub.add_parser('resume')
    resume.add_argument('--reason', required=True)
    test = sub.add_parser('test')
    check = sub.add_parser('check')
    for command in (test, check):
        command.add_argument('--timeout', type=float, default=300)
        command.add_argument('--junit')
        command.add_argument('--junit-dir')
        command.add_argument('command', nargs=argparse.REMAINDER)
    finish = sub.add_parser('finish')
    finish.add_argument('--export', action='append', dest='exports')
    finish.add_argument('--opencode', default='opencode')
    for command in (start, review, resume, test, finish):
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

            return events
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
              limits: dict | None = None) -> dict:
        if session is not None:
            session_id(session)
        limits = dict(DEFAULT_LIMITS, **{k: v for k, v in (limits or {}).items() if v is not None})
        if set(limits) != set(DEFAULT_LIMITS) or any(type(v) is not int or v < 1 for v in limits.values()):
            raise ValueError('Limits must be positive integers: ' + ', '.join(DEFAULT_LIMITS))
        self.task_dir(task).mkdir(parents=True, exist_ok=False)
        with self.lock(task):
            # session=session puts the value into append's **data as the "session" key;
            # session_id(session) above has already validated it.
            return self.append(task, 'start', session=session, title=title or task, limits=limits)

    # check if the task is active (not finished) and return its events
    def active(self, task):
        events = self.read(task)
        if any(e['kind'] == 'finish' for e in events):
            raise ValueError('Task is finished; start a new task ID')
        return events

    def running(self, task):
        """Events of an active task that is not stopped by a loop guard; raises TaskHalted otherwise."""
        events = self.active(task)
        halt = is_halted(events)
        if halt:
            raise TaskHalted(halt['reason'])
        return events

    def guard(self, task: str, events: list[dict]) -> dict | None:
        """Appends a 'halt' event if a loop guard is reached. Returns that event or None."""
        reason = limit_breach(events, task_limits(events))
        return self.append(task, 'halt', reason=reason) if reason else None

    # record a review for a task, ensuring the piece and result are valid
    def review(self, task: str, piece: str, result: str) -> dict:
        piece = piece.strip()
        if not piece or result not in {'accepted', 'rework'}:
            raise ValueError('Review requires a piece and accepted/rework result')
        with self.lock(task):
            events = self.running(task)
            event = self.append(task, 'review', piece=piece, result=result)
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
             junit_dir: str | None = None) -> dict:
        xml, folder = self.report_source(junit, junit_dir)
        with self.lock(task):
            events = self.running(task)
            started = time.monotonic()
            output, code, parsed, category = self.execute(command, timeout, xml, folder)
            log = 'test-' + uuid.uuid4().hex + '.log'
            (self.task_dir(task) / log).write_text(output, encoding='utf-8')
            hints = diagnose(output, code, parsed, category, bool(xml or folder))
            event = self.append(task, 'test', command=command, returncode=code, log=log,
                                duration_seconds=time.monotonic()-started, category=category,
                                **({'hints': hints} if hints else {}), **parsed)
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
        rows, seen = {}, {}

        for sid in sorted(allowed):
            for export in sessions[sid]:
                warnings_list.extend(export.get('_metrics_warnings', []))
                for child in brain_tool_child_references(export) - allowed:
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
        warnings_list.append('Учтены сообщения в интервале задачи; служебные вызовы вне экспорта могут отсутствовать.')
        if any(r['missing_usage'] for r in rows.values()):
            warnings_list.append('В части сообщений нет корректного расхода токенов; соответствующие суммы неизвестны.')
        return dict(models=list(rows.values()), warnings=list(dict.fromkeys(warnings_list)), sessions=sorted(allowed))

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
                children = brain_tool_child_references(export)
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
        no_result = [e for e in tests if e.get('category') in {CATEGORY_NO_RESULT, CATEGORY_TIMEOUT}]
        if no_result:
            lines += [f'⚙️ Прогоны без результата (сборка, окружение или зависание): **{len(no_result)}**. '
                      'Они не считаются ошибками исполнителя.', '']
        halts = [e for e in events if e['kind'] == 'halt']
        if halts:
            resumes = [e for e in events if e['kind'] == 'resume']
            lines += [f'⛔ Остановки по защитным лимитам: **{len(halts)}** · продолжений после решения пользователя: '
                      f'**{len(resumes)}**', '']
            lines += ['- Остановка: ' + label(e['reason']) for e in halts]
            lines += ['- Продолжение: ' + label(e['reason']) for e in resumes]
            lines.append('')
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

    # it is our final step to finish a task, collect exports, parse usage, and write a Markdown report to report.md in the task directory
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

def main(argv=None) -> int:
    """
    Command line. Exit codes tell the brain what to do next:
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
            event = metrics.start(args.task, args.session, args.title, limits)
        elif args.action == 'review':
            event = metrics.review(args.task, args.piece, args.result)
        elif args.action == 'resume':
            event = metrics.resume(args.task, args.reason)
        elif args.action == 'finish':
            print(metrics.finish(args.task, args.exports, args.opencode))
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
            event = metrics.test(args.task, command, args.timeout, args.junit, args.junit_dir)
            print((metrics.task_dir(args.task)/event['log']).read_text(encoding='utf-8'))
            print(json.dumps(event, ensure_ascii=False))
            return report_test(event, args.task)
        print(json.dumps(event, ensure_ascii=False))
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
    """Prints what the brain should do after a test run and returns the exit code."""
    if event.get('halt'):
        print_stop(event['halt'], task)
        return EXIT_STOP
    category = event['category']
    if category == CATEGORY_PASSED:
        return EXIT_OK
    if category in {CATEGORY_FAILED, CATEGORY_INCOMPLETE}:
        print('TESTS FAILED: the tests ran. Read the failures: send the piece back to the executor '
              '(review --result rework) or fix the tests if they contradict the spec.', file=sys.stderr)
        return EXIT_TESTS_FAILED
    print('NO RESULT: the tests did not produce a readable result. Usually this is a setup or build '
          'problem, not an executor mistake. Record a rework only if the log shows a compile error in '
          'code the executor just wrote; otherwise fix the setup or ask the user.', file=sys.stderr)
    for hint in event.get('hints', []):
        print('- ' + hint, file=sys.stderr)
    return EXIT_NO_RESULT


def print_stop(reason: str, task: str) -> None:
    """The STOP message. The brain must end the loop and wait for the user's decision."""
    print(f'STOP: {reason}', file=sys.stderr)
    print('Do not run more tests and do not send more reworks. Tell the user what happened and what '
          'you suggest, then wait. Continue only after the user decides, with: '
          f'task_metrics.py resume --task {task} --reason "<the user\'s decision>"', file=sys.stderr)


if __name__ == '__main__':
    sys.exit(main())
