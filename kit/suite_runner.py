"""Run the project's test command and read its result (Python unittest or JUnit XML).

The result becomes a category for the build loop: passed, tests failed, incomplete,
no readable result or timeout. The category, not the raw exit code, decides what
the Master Chief does next.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time
import xml.etree.ElementTree as ET

if __package__:
    from .journal import valid_number
else:
    from journal import valid_number

# What a test run means for the build loop.
CATEGORY_PASSED = 'passed'          # tests ran, all green
CATEGORY_FAILED = 'tests_failed'    # tests ran, some failed: a code or test problem
CATEGORY_INCOMPLETE = 'incomplete'  # tests ran without failures, but some were skipped
CATEGORY_NO_RESULT = 'no_result'    # no readable test results: setup, build or tool problem
CATEGORY_TIMEOUT = 'timeout'        # the command did not finish in time


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


class SuiteRunnerMixin:
    """Test command methods of TaskMetrics; they need only self.root (the project root)."""

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
