"""Project installation and Desktop discovery; no GUI, model calls or key copying."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlencode

from .task_control_state import plain_path

DOWNLOAD_URL = 'https://opencode.ai/download'
MANIFEST = Path('.metrics/.kit-installation.json')
IGNORE_LINES = ('.metrics/', '.opencode/kit-models.json', '.opencode/opencode.jsonc',
                '.opencode/opencode.jsonc.tmp', '__pycache__/', '*.pyc')
ROOT_FILES = ('AGENTS.md', 'opencode.jsonc', 'LOCAL_MODELS.ru.md', 'METRICS.ru.md',
              'QUICKSTART.ru.md', 'QUICKSTART.en.md', 'OPENCODE_KIT.ru.md', 'OPENCODE_KIT.en.md')
TREES = ('kit', '.opencode/commands', 'docs')
SKIP = {'.git', '.metrics', '__pycache__', '.venv', 'node_modules', '.aws', '.ssh',
        '.codex', '.agents', 'auth.json', 'credentials.json'}


@dataclass(frozen=True)
class Desktop:
    application: Path
    cli: Path


class InstallError(ValueError):
    """An actionable installer error; never includes a provider response or key."""


def desktop_from_path(application: Path) -> Desktop | None:
    """Recognize a Desktop app and its bundled CLI, not a terminal-only install."""
    path = Path(application).expanduser().resolve()
    if path.name.endswith('.app') and path.is_dir():
        cli = path / 'Contents/Resources/opencode-cli'
    elif path.is_file() and path.name.lower() in ('opencode.exe', 'opencode', 'opencode-desktop', 'opencode.appimage'):
        cli = path.parent / 'resources' / ('opencode-cli.exe' if path.suffix.lower() == '.exe' else 'opencode-cli')
    else:
        return None
    return Desktop(path, cli) if cli.is_file() else None


def find_desktop() -> Desktop | None:
    """Search common vendor installation locations and Windows App Paths."""
    candidates = []
    if sys.platform == 'win32':
        for variable, suffix in (('LOCALAPPDATA', 'Programs/@opencodedesktop/OpenCode.exe'),
                                 ('LOCALAPPDATA', 'Programs/OpenCode/OpenCode.exe'),
                                 ('ProgramFiles', 'OpenCode/OpenCode.exe')):
            if os.environ.get(variable):
                candidates.append(Path(os.environ[variable]) / suffix)
        try:
            import winreg
            for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                try:
                    with winreg.OpenKey(hive, r'Software\Microsoft\Windows\CurrentVersion\App Paths\OpenCode.exe') as key:
                        candidates.append(Path(winreg.QueryValue(key, None)))
                except OSError:
                    continue
        except ImportError:
            pass
    elif sys.platform == 'darwin':
        candidates += [Path('/Applications/OpenCode.app'), Path.home() / 'Applications/OpenCode.app']
    else:
        candidates += [Path(prefix) / name for prefix in ('/opt/OpenCode', '/opt/opencode', '/usr/lib/opencode')
                       for name in ('opencode', 'opencode-desktop')]
    for name in ('OpenCode.exe', 'opencode-desktop'):
        if executable := shutil.which(name):
            candidates.append(Path(executable))
    return next((found for path in candidates if (found := desktop_from_path(path))), None)


def payload(source: Path) -> dict[str, bytes]:
    """Read an explicit distributable allowlist. Never copy journals or saved keys."""
    source = plain_path(Path(source).absolute())
    files = {}
    for name in ROOT_FILES:
        path = plain_path(source / name)
        if not path.is_file():
            raise InstallError('The kit download is incomplete. Extract the full ZIP archive first.')
        files[name] = path.read_bytes()
    agents = files['AGENTS.md'].decode('utf-8')
    start, end = agents.find('## Work plan (memory)'), agents.find('## Source snapshot boundaries')
    if 0 <= start < end:
        agents = agents[:start] + ('## Work plan (memory)\n'
            '- Keep the active work plan in `currentsteps.md` in this project root. Create it if missing.\n'
            '- Read it at session start and update it after major steps. This installed project uses a local plan.\n\n') + agents[end:]
        files['AGENTS.md'] = agents.encode('utf-8')
    for tree in TREES:
        folder = plain_path(source / tree)
        if not folder.is_dir():
            raise InstallError('The kit download is incomplete. Extract the full ZIP archive first.')
        for current, dirs, names in os.walk(folder, followlinks=False):
            for name in dirs + names:
                path = Path(current) / name
                if path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
                    raise InstallError('The kit contains a link. Use an extracted official kit archive.')
            dirs[:] = [name for name in dirs if name.lower() not in SKIP and not name.lower().startswith('.env')]
            for name in names:
                if name.lower() in SKIP or name.lower().startswith('.env') or name.endswith(('.pyc', '.pyo')):
                    continue
                path = Path(current) / name
                files[path.relative_to(source).as_posix()] = path.read_bytes()
    return files


def project_path(value: str, source: Path) -> Path:
    """Require a separate absolute project folder, without following links."""
    if not value.strip():
        raise InstallError('Choose a project folder first.')
    path = Path(value.strip()).expanduser()
    if not path.is_absolute():
        raise InstallError('Enter a full folder path, for example D:\\Projects\\my-project.')
    try:
        path = plain_path(path.absolute())
    except (OSError, ValueError):
        raise InstallError('Choose a regular folder, not a symbolic link or junction.') from None
    source = Path(source).resolve()
    if path == Path(path.anchor) or path.is_relative_to(source) or source.is_relative_to(path):
        raise InstallError('Choose a separate project folder outside the downloaded kit.')
    if path.exists() and not path.is_dir():
        raise InstallError('This path is a file. Choose a folder instead.')
    return path


def installed(project: Path) -> bool:
    """A previous installation can reopen settings; never silently upgrade it."""
    try:
        value = json.loads(plain_path(project / MANIFEST).read_text(encoding='utf-8'))
        return value.get('format') == 1 and all(plain_path(project / name).is_file()
            for name in ('AGENTS.md', 'opencode.jsonc', 'kit/run_opencode.py'))
    except (OSError, ValueError, AttributeError):
        return False


def install_project(source: Path, destination: str) -> dict:
    """Create missing folders and install without overwriting existing project data.

    Preflight all conflicts. Exclusive file creation prevents a race from replacing
    user files. On failure remove only this call's unchanged files and empty dirs.
    Existing model settings, project code, TASK.md and README.md remain untouched.
    """
    project = project_path(destination, source)
    if installed(project):
        return {'project': str(project), 'reused': True, 'files': 0}
    files = payload(source)
    for name in ('kit', 'AGENTS.md', 'opencode.jsonc', 'opencode.json', '.opencode/opencode.jsonc', '.opencode/opencode.json'):
        if (project / name).exists():
            raise InstallError('This folder already has OpenCode configuration or a kit. Choose another folder; nothing was replaced.')
    for name in files:
        target = plain_path(project / name)
        if target.exists() or any(parent.exists() and not parent.is_dir() for parent in target.parents):
            raise InstallError('Some kit files already exist in this folder. Choose another folder; nothing was replaced.')
    created, directories = {}, []
    ignore = plain_path(project / '.gitignore')
    old_ignore = ignore.read_bytes() if ignore.exists() else None
    ignore_bytes = (old_ignore or b'') + b'\n# OpenCode Kit: local settings and task journals\n' + '\n'.join(IGNORE_LINES).encode() + b'\n'
    def mkdir(path):
        if path.is_dir():
            return
        mkdir(path.parent)
        path.mkdir()
        directories.append(path)
    def create(path, content):
        with path.open('xb') as stream:
            created[path] = b''
            try:
                stream.write(content)
                stream.flush()
            except OSError:
                try:
                    stream.close()
                except OSError:
                    pass
                created[path] = path.read_bytes()
                raise
            created[path] = content
    def replace_ignore(content):
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=project, prefix='.kit-ignore-', delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(content)
            if ignore.read_bytes() != (old_ignore if content == ignore_bytes else ignore_bytes):
                raise InstallError('The project changed during installation. Try again.')
            os.replace(temporary, ignore)
        finally:
            if temporary and temporary.exists():
                temporary.unlink()
    try:
        mkdir(project)
        for name, content in files.items():
            path = project / name
            mkdir(path.parent)
            create(path, content)
        if old_ignore is None:
            create(ignore, ignore_bytes)
        else:
            if ignore.read_bytes() != old_ignore:
                raise InstallError('The project changed during installation. Try again.')
            replace_ignore(ignore_bytes)
        mkdir((project / MANIFEST).parent)
        metadata = {'format': 1, 'installed_at': datetime.now(timezone.utc).isoformat(),
                    'files': {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}}
        content = json.dumps(metadata, ensure_ascii=True, indent=2).encode()
        create(project / MANIFEST, content)
    except BaseException:
        if old_ignore is not None and ignore.is_file() and ignore.read_bytes() == ignore_bytes:
            replace_ignore(old_ignore)
        for path, content in reversed(list(created.items())):
            if path.is_file() and path.read_bytes() == content:
                path.unlink()
        for path in reversed(directories):
            try:
                path.rmdir()
            except OSError:
                pass
        raise
    return {'project': str(project), 'reused': False, 'files': len(files)}


def open_project(desktop: Desktop, project: Path):
    """Launch Desktop with an encoded project-opening URI; never submit a prompt.

    Desktop versions differ in deep-link handling. Successful process launch is
    an opening request, not proof that the UI selected the folder. Keep a visible
    manual Open Project fallback in the installer.
    """
    project = plain_path(Path(project).absolute())
    if not installed(project) or not (project / '.opencode/opencode.jsonc').is_file():
        raise InstallError('Prepare the project models before opening OpenCode.')
    if desktop_from_path(desktop.application) != desktop:
        raise InstallError('OpenCode Desktop was not found. Install it or choose its application file.')
    uri = 'opencode://open-project?' + urlencode({'directory': str(project)})
    command = (['open', '-a', str(desktop.application), uri] if desktop.application.suffix == '.app'
               else [str(desktop.application), uri])
    return subprocess.Popen(command, cwd=project, stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
