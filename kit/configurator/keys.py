"""API keys in Windows user environment variables.

The choice file stores only the NAME of a variable. The key itself is saved in the
user's environment (registry HKEY_CURRENT_USER\\Environment), like the command setx
does. New programs started after saving see the variable; already running ones
(an open terminal, VS Code) do not, so they must be restarted.

Why the file is called keys.py and not secrets.py: Python already has a standard
module "secrets", and a file with the same name can hide it.

Status: SKELETON. Every function raises NotImplementedError until it is implemented,
except notify_windows, which is ready (it calls the Windows API directly).
Lines marked "ПОДСКАЗКА" are learning hints; delete them once the function is done.
"""
from __future__ import annotations

import os
import re
import sys

try:
    import winreg  # exists only on Windows
except ImportError:  # tests on other systems replace it with a fake
    winreg = None

BRAIN_KEY_ENV = 'OCK_BRAIN_API_KEY'
EXECUTOR_KEY_ENV = 'OCK_EXECUTOR_API_KEY'
ENVIRONMENT_KEY = 'Environment'  # registry path under HKEY_CURRENT_USER

ENV_NAME = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')


# --- Step 5. Pure helpers ------------------------------------------------------

def is_valid_env_name(name: str) -> bool:
    """returns True if the name can be an environment variable name (see ENV_NAME condition)."""
    return bool(ENV_NAME.fullmatch(name))

def mask(value: str) -> str:
    """Show a key safely: first 4 and last 4 characters, the rest hidden.
    "sk-abcdefgh12345678" -> "sk-a....5678". Keys of 8 characters or shorter -> "••••".
    An empty key -> "".
    """
    result_string = ''
    if not value:
        return result_string
    if len(value) <= 8:
        result_string = 4 * '\u2022' 
    else:
        result_string = value[:4] + '\u2026' + value[-4:]
    return result_string


# --- Step 6. The registry ------------------------------------------------------

def read_user_variable(name: str) -> str | None:
    """Value of a user environment variable from the registry, or None if it is absent.

    Reads the registry, not os.environ: right after saving, this program's os.environ
    is already updated, but other programs only learn about the value from the registry.
    """
    # ПОДСКАЗКА: открыть ключ реестра:
    #   with winreg.OpenKey(winreg.HKEY_CURRENT_USER, ENVIRONMENT_KEY) as key:
    #       value, kind = winreg.QueryValueEx(key, name)
    # ПОДСКАЗКА: если значения нет, QueryValueEx бросает FileNotFoundError — поймай её.
    raise NotImplementedError('step 6.1: read_user_variable')


def save_user_variable(name: str, value: str) -> None:
    """Save a user environment variable, like "setx NAME VALUE".

    Also puts the value into os.environ so this program and the programs it starts
    (for example kit/run_opencode.py) see it at once. Then calls notify_windows().

    Raises:
        ValueError: name is not a valid variable name, or value is empty.
    """
    # ПОДСКАЗКА: сначала проверки (is_valid_env_name уже будет готова).
    # ПОДСКАЗКА: открыть ключ на запись:
    #   with winreg.OpenKey(winreg.HKEY_CURRENT_USER, ENVIRONMENT_KEY, 0, winreg.KEY_SET_VALUE) as key:
    #       winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
    # ПОДСКАЗКА: os.environ ведёт себя как словарь: os.environ[name] = value.
    raise NotImplementedError('step 6.2: save_user_variable')


def key_is_set(name: str) -> bool:
    """True when the variable has a non-empty value in os.environ or in the registry."""
    # ПОДСКАЗКА: os.environ.get(name) вернёт None, если переменной нет.
    # ПОДСКАЗКА: "или" в Python пишется словом or.
    raise NotImplementedError('step 6.3: key_is_set')


# --- Ready helper ---------------------------------------------------------------

def notify_windows() -> None:
    """Tell running Windows programs that the environment changed (what setx does).

    Ready code, not a learning step: it calls the Windows API through ctypes.
    Programs that listen (Explorer, new terminals started from it) pick up the change.
    Already open terminals and VS Code still need a restart.
    """
    if sys.platform != 'win32':
        return
    import ctypes
    HWND_BROADCAST = 0xFFFF
    WM_SETTINGCHANGE = 0x001A
    SMTO_ABORTIFHUNG = 0x0002
    result = ctypes.c_ulong()
    ctypes.windll.user32.SendMessageTimeoutW(
        HWND_BROADCAST, WM_SETTINGCHANGE, 0, 'Environment',
        SMTO_ABORTIFHUNG, 5000, ctypes.byref(result))
