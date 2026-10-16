"""Find the OpenCode CLI. One search order for every kit script.

Order:
1. An explicit command or path (anything other than the default name "opencode").
2. The CLI bundled with OpenCode Desktop on Windows. The user works in Desktop, so this CLI
   sees the same sessions and has the same version as the app that reads the overlay.
3. The native "opencode" executable on PATH (Linux, macOS, or no Desktop installed).

Windows .cmd/.bat wrappers (npm installs commands this way) are skipped: batch quoting can
alter forwarded arguments. A wrapper on PATH may also be a different, older OpenCode.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil

DEFAULT_COMMAND = 'opencode'
DESKTOP_CLI = Path('Programs') / '@opencodedesktop' / 'resources' / 'opencode-cli.exe'
WRAPPER_SUFFIXES = ('.cmd', '.bat')


def is_wrapper(executable: str) -> bool:
    """True for a Windows batch wrapper such as opencode.cmd."""
    return Path(executable).suffix.lower() in WRAPPER_SUFFIXES


def desktop_cli() -> str | None:
    """Path of the CLI inside OpenCode Desktop, or None when it is not installed."""
    local = os.environ.get('LOCALAPPDATA')
    if local:
        path = Path(local) / DESKTOP_CLI
        try:
            if path.is_file():
                return str(path)
        except OSError:
            pass
    if os.name != 'nt':
        if __package__:
            from .installer import find_desktop
        else:
            import sys
            sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
            from kit.installer import find_desktop
        found = find_desktop()
        return str(found.cli) if found else None
    return None


def locate_opencode(command: str = DEFAULT_COMMAND) -> str | None:
    """Return the OpenCode executable to run, or None when nothing suitable is found.

    An explicit command is resolved through PATH (or taken as a path) and returned even if it
    is a wrapper, so the caller can explain why it is rejected.
    """
    if command != DEFAULT_COMMAND:
        return shutil.which(command)
    found = desktop_cli()
    if found:
        return found
    on_path = shutil.which(DEFAULT_COMMAND)
    if on_path and not is_wrapper(on_path):
        return on_path
    return None
