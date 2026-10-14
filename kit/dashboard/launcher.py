"""Own and reuse a local dashboard process; the metrics class never starts it."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import urlencode, urlsplit
import urllib.request
import uuid
import webbrowser

from ..task_metrics import TaskMetrics

SERVICE = 'opencode-kit-dashboard'
VERSION = 1
READY_TIMEOUT = 12.0
_children = []


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def local_request(request, timeout):
    """Local control requests bypass proxies and never follow redirects."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    return opener.open(request, timeout=timeout)


def project_id(root: Path) -> str:
    return hashlib.sha256(os.path.normcase(str(root.resolve())).encode('utf-8')).hexdigest()[:16]


def runtime_folder(root: Path) -> Path:
    return root.resolve() / '.metrics' / '.dashboard'


def write_state(root: Path, state: dict) -> None:
    """Publish a complete state file, never a partially written JSON document."""
    folder = runtime_folder(root)
    folder.mkdir(parents=True, exist_ok=True)
    temporary = folder / ('runtime-' + uuid.uuid4().hex + '.tmp')
    try:
        temporary.write_text(json.dumps(state, ensure_ascii=False), encoding='utf-8')
        temporary.replace(folder / 'runtime.json')
    finally:
        temporary.unlink(missing_ok=True)


def read_state(root: Path) -> dict | None:
    try:
        state = json.loads((runtime_folder(root) / 'runtime.json').read_text(encoding='utf-8'))
        return state if isinstance(state, dict) else None
    except (OSError, ValueError):
        return None


def local_url(value: str) -> bool:
    """Do not follow a manually edited runtime record to a remote host."""
    try:
        parts = urlsplit(value)
        return (parts.scheme == 'http' and parts.hostname == '127.0.0.1'
                and parts.username is None and parts.password is None
                and parts.port is not None and 0 < parts.port < 65536
                and parts.path in ('', '/') and not parts.query and not parts.fragment)
    except (TypeError, ValueError, AttributeError):
        return False


def health(root: Path, state: dict | None, timeout: float = 0.5) -> dict | None:
    if not state or not local_url(state.get('base_url')):
        return None
    if state.get('service') != SERVICE or state.get('version') != VERSION:
        return None
    if state.get('project_root') != str(root.resolve()):
        return None
    if not isinstance(state.get('instance_id'), str) or not state['instance_id']:
        return None
    if type(state.get('pid')) is not int or state['pid'] <= 0:
        return None
    try:
        with local_request(state['base_url'].rstrip('/') + '/api/health', timeout) as response:
            data = json.load(response)
        expected = ('service', 'version', 'project_root', 'instance_id', 'pid', 'base_url')
        if not isinstance(data, dict) or any(data.get(key) != state.get(key) for key in expected):
            return None
        return data
    except (OSError, ValueError):
        return None


@contextmanager
def launch_lock(root: Path, timeout: float):
    """A process-level lock released by the OS even if its owner crashes."""
    folder = runtime_folder(root)
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / 'launch.lock').open('a+b') as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b'0')
            handle.flush()
        deadline = time.monotonic() + timeout
        while True:
            handle.seek(0)
            try:
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError('Another dashboard launch is still in progress')
                time.sleep(0.05)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def start_process(root: Path, instance: str) -> subprocess.Popen:
    folder = runtime_folder(root)
    command = [sys.executable, '-u', '-m', 'kit.dashboard.runtime',
               '--project', str(root), '--instance', instance, '--port', '0']
    options = {'cwd': root, 'stdin': subprocess.DEVNULL}
    if os.name == 'nt':
        options['creationflags'] = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        options['start_new_session'] = True
    with (folder / 'server.log').open('ab') as log:
        process = subprocess.Popen(command, stdout=log, stderr=log, **options)
    _children.append(process)
    return process


def task_url(root: Path, task: str, base_url: str) -> str:
    TaskMetrics(root).task_dir(task)
    if not local_url(base_url):
        raise ValueError('Invalid dashboard address')
    return base_url.rstrip('/') + '/?' + urlencode({'project': project_id(root), 'task': task})


@contextmanager
def process_exit_waiter(pid: int):
    """Wait for actual process exit, including children created by another CLI."""
    if os.name == 'nt':
        import ctypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        kernel.WaitForSingleObject.restype = ctypes.c_uint32
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel.CloseHandle.restype = ctypes.c_int
        handle = kernel.OpenProcess(0x00100000, False, pid)
        if not handle:
            if ctypes.get_last_error() == 87:
                yield lambda timeout: None
                return
            raise ctypes.WinError(ctypes.get_last_error())
        def wait(timeout):
            result = kernel.WaitForSingleObject(handle, max(1, int(timeout * 1000)))
            if result == 258:
                raise TimeoutError('Dashboard process did not exit')
            if result != 0:
                raise ctypes.WinError(ctypes.get_last_error())
        try:
            yield wait
        finally:
            kernel.CloseHandle(handle)
    else:
        def wait(timeout):
            deadline = time.monotonic() + timeout
            while True:
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    return
                if time.monotonic() >= deadline:
                    raise TimeoutError('Dashboard process did not exit')
                time.sleep(0.05)
        yield wait


def ensure_dashboard(root: Path, task: str, *, open_browser: bool = True,
                     timeout: float = READY_TIMEOUT) -> dict:
    """Validate the task, reuse/start our server, then optionally open its task page."""
    root = Path(root).resolve()
    if timeout <= 0:
        raise ValueError('Dashboard timeout must be positive')
    folder = TaskMetrics(root).task_dir(task)
    if not (folder / 'events.jsonl').is_file():
        raise ValueError('Register the task before starting its dashboard')
    if folder.resolve().parent != (root / '.metrics').resolve():
        raise ValueError('Task directory is outside the project journal folder')
    started = False
    with launch_lock(root, timeout):
        state = read_state(root)
        if health(root, state) is None:
            instance = uuid.uuid4().hex
            process = start_process(root, instance)
            deadline = time.monotonic() + timeout
            try:
                while True:
                    state = read_state(root)
                    if (state and state.get('instance_id') == instance
                            and state.get('pid') == process.pid and health(root, state) is not None):
                        break
                    if process.poll() is not None:
                        raise RuntimeError('Dashboard process exited; see ' + str(runtime_folder(root) / 'server.log'))
                    if time.monotonic() >= deadline:
                        raise TimeoutError('Dashboard did not become ready; see ' + str(runtime_folder(root) / 'server.log'))
                    time.sleep(0.05)
            except BaseException:
                # Only the child created by this attempt may be terminated here.
                if process.poll() is None:
                    process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
                if process in _children:
                    _children.remove(process)
                raise
            started = True
        url = task_url(root, task, state['base_url'])
        result = {'status': 'ready', 'url': url, 'started': started, 'opened': False,
                  'pid': state['pid'], 'instance_id': state['instance_id']}
        if open_browser:
            try:
                result['opened'] = bool(webbrowser.open(url, new=0))
            except (OSError, webbrowser.Error) as error:
                result['browser_error'] = str(error)
        return result


def stop_dashboard(root: Path, timeout: float = READY_TIMEOUT) -> bool:
    """Stop only a server whose identity matches this project's runtime record."""
    root = Path(root).resolve()
    with launch_lock(root, timeout):
        state = read_state(root)
        if health(root, state) is None:
            return False
        token = state.get('control_token')
        if not isinstance(token, str) or not token:
            raise ValueError('Dashboard control token is missing')
        with process_exit_waiter(state['pid']) as wait_for_exit:
            request = urllib.request.Request(state['base_url'].rstrip('/') + '/api/stop', data=b'',
                                             headers={'X-Dashboard-Token': token}, method='POST')
            with local_request(request, 2) as response:
                response.read()
            deadline = time.monotonic() + timeout
            while health(root, state) is not None:
                if time.monotonic() >= deadline:
                    raise TimeoutError('Dashboard did not stop')
                time.sleep(0.05)
            for process in list(_children):
                if process.pid == state['pid']:
                    process.wait(timeout=5)
                    _children.remove(process)
            wait_for_exit(max(0.01, deadline - time.monotonic()))
        return True


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--task', help='an already registered task to open')
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--stop', action='store_true', help='stop this project dashboard')
    args = parser.parse_args(argv)
    if not args.stop and not args.task:
        parser.error('--task is required unless --stop is used')
    try:
        result = ({'stopped': stop_dashboard(args.root)} if args.stop else
                  ensure_dashboard(args.root, args.task, open_browser=not args.no_browser))
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        print('Dashboard: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
