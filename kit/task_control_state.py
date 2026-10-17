"""Durable user controls, independent of the metrics journal and loop guards."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import time
import uuid

TRANSITIONS = frozenset(('pausing', 'resuming', 'cancelling', 'deleting'))
STATUSES = TRANSITIONS | {'running', 'paused', 'cancelled', 'deleted', 'error'}


def plain_path(path: Path) -> Path:
    """Reject redirected paths, including junctions, before mutation.

    Every existing component of the absolute path is checked for a symlink or junction.
    Comparing with resolve() is not used: on Windows it also expands 8.3 short names
    (C:\\Users\\RUNNER~1) and normalizes letter case, so a plain folder would look like a link.
    """
    if '..' in path.parts:
        raise ValueError('Control paths must not contain ".."')
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        if current.is_symlink() or getattr(current, 'is_junction', lambda: False)():
            raise ValueError('Control paths must not contain links or junctions')
    return path


def state_path(root: Path, task: str) -> Path:
    if not isinstance(task, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', task):
        raise ValueError('Invalid task ID')
    if task.upper() in {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}:
        raise ValueError('Reserved task ID')
    base = plain_path(Path(root).resolve() / '.metrics')
    folder = plain_path(base / '.task-controls')
    return plain_path(folder / (task + '.json'))


def read_state(root: Path, task: str) -> dict:
    path = state_path(root, task)
    if not path.exists():
        return {}
    if path.stat().st_size > 65536:
        raise ValueError('Control state is too large')
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict) or value.get('status') not in STATUSES or value.get('task') != task:
        raise ValueError('Invalid task control state')
    return value


def write_state(root: Path, task: str, **state) -> dict:
    path = state_path(root, task)
    path.parent.mkdir(parents=True, exist_ok=True)
    value = dict(state, task=task, updated_at=time.time())
    if value.get('status') not in STATUSES:
        raise ValueError('Invalid task control status')
    temporary = path.with_suffix('.' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('x', encoding='utf-8') as handle:
            json.dump(value, handle, ensure_ascii=False, allow_nan=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return value


@contextmanager
def operation_lock(root: Path, task: str):
    """An OS-released lock survives worker crashes without a stale lock file."""
    path = state_path(root, task).with_suffix('.lock')
    plain_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as handle:
        handle.seek(0, os.SEEK_END)
        if not handle.tell():
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise ValueError('Task control operation is already in progress') from error
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def blocking_reason(root: Path, task: str) -> str | None:
    state = read_state(root, task)
    status = state.get('status')
    if status == 'resuming' and state.get('allow_execution') is True:
        try:
            with operation_lock(root, task):
                return 'Task continuation was interrupted; inspect its dashboard before executing new work.'
        except ValueError:
            return None  # A live worker is admitting the continuation prompt.
    if status and status != 'running' and not (status == 'resuming' and state.get('allow_execution') is True):
        return f'Task control: {status}. Use the dashboard to inspect or continue this task.'
    return None
