"""Presentation language only; never change model settings or journal facts."""
from __future__ import annotations

from functools import lru_cache
import json
import locale
import os
from pathlib import Path
import re
import sys
import uuid

if __package__:
    from .task_control_state import plain_path
else:
    from task_control_state import plain_path

PREFERENCES = Path('.metrics') / '.configurator-ui.json'
LANGUAGES = ('en', 'ru')


def choose_language(values, default='en'):
    """Choose the first supported locale, accepting BCP-47 and POSIX spellings."""
    if isinstance(values, str):
        values = values.split(',')
    for value in values or ():
        if not isinstance(value, str):
            continue
        pieces = value.strip().split(';')
        if any(piece.strip().startswith('q=') and piece.strip()[2:] in ('0', '0.0', '0.00', '0.000') for piece in pieces[1:]):
            continue
        language = re.split(r'[-_.@]', pieces[0].lower())[0]
        if language in LANGUAGES:
            return language
    return default


def windows_language():
    """Read the user's Windows UI language without changing process locale."""
    import ctypes
    code = ctypes.windll.kernel32.GetUserDefaultUILanguage()
    return locale.windows_locale.get(code, '')


def request_language(header, fallback='en'):
    candidates = []
    for index, item in enumerate((header or '').split(',')):
        parts = item.strip().split(';')
        try:
            weight = next((float(part.strip()[2:]) for part in parts[1:] if part.strip().startswith('q=')), 1.0)
        except ValueError:
            continue
        if 0 < weight <= 1:
            candidates.append((-weight, index, parts[0]))
    return choose_language([value for _, _, value in sorted(candidates)], fallback)


def system_language():
    """Windows UI language or POSIX message locale; unsupported means English."""
    if sys.platform == 'win32':
        try:
            return choose_language([windows_language()])
        except (OSError, AttributeError):
            return 'en'
    for key in ('LC_ALL', 'LC_MESSAGES', 'LANGUAGE', 'LANG'):
        value = os.environ.get(key)
        if value:
            return choose_language(value.split(':'))
    try:
        return choose_language([locale.getlocale()[0]])
    except (ValueError, TypeError):
        return 'en'


def saved_language(root):
    """Missing/corrupt preferences are not an explicit language selection."""
    try:
        path = plain_path(Path(root) / PREFERENCES)
        if path.stat().st_size > 4096:
            return None
        value = json.loads(path.read_text(encoding='utf-8')).get('language')
        return value if value in LANGUAGES else None
    except (OSError, ValueError, AttributeError, TypeError):
        return None


def load_language(root):
    return saved_language(root) or system_language()


def save_language(root, language):
    if language not in LANGUAGES:
        raise ValueError('Unsupported language')
    path = plain_path(Path(root) / PREFERENCES)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '-' + uuid.uuid4().hex + '.tmp')
    try:
        temporary.write_text(json.dumps({'language': language}) + '\n', encoding='utf-8')
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


@lru_cache(maxsize=1)
def catalog():
    """English source keys, Russian translations. User content never enters here."""
    return json.loads((Path(__file__).parent / 'locales' / 'ru.json').read_text(encoding='utf-8'))


def text(key, language='en', **values):
    template = catalog().get(key, key) if language == 'ru' else key
    return template.format(**values) if values else template


def diagnostic(value, language='en'):
    """Translate known complete system messages; leave arbitrary diagnostics intact."""
    if not isinstance(value, str):
        return value
    messages = catalog()
    if value in messages:
        return text(value, language)
    for english, russian in messages.items():
        if value == russian:
            return russian if language == 'ru' else english
    for prefix, key in (('Токены — нет данных: ', 'Tokens unavailable: {reason}'),
                        ('Посторонняя сессия исключена: ', 'Unrelated session excluded: {reason}')):
        if value.startswith(prefix):
            return text(key, language, reason=diagnostic(value[len(prefix):], language))
    match = re.fullmatch(r'OpenCode: не выполнено действие (.+); состояние не подтверждено', value)
    if match:
        return text('OpenCode operation {operation} failed; outcome unconfirmed', language, operation=match[1])
    return value


def task_presentation(value, language):
    """Copy/translate only known presentation fields, never public model messages."""
    result = dict(value)
    for field in ('control', 'tokens', 'completion'):
        if isinstance(value.get(field), dict):
            result[field] = dict(value[field])
            for key in ('error', 'message', 'reason', 'launcher_error'):
                if key in result[field]:
                    result[field][key] = diagnostic(result[field][key], language)
            if isinstance(result[field].get('warnings'), list):
                result[field]['warnings'] = [diagnostic(row, language) for row in result[field]['warnings']]
    if isinstance(value.get('work'), dict):
        work = result['work'] = dict(value['work'])
        work['errors'] = [diagnostic(row, language) for row in work.get('errors', [])]
        if work.get('errors'):
            work['error'] = '. '.join(work['errors'])
        elif work.get('error'):
            work['error'] = diagnostic(work['error'], language)
        for field in ('progress', 'sessions'):
            if isinstance(work.get(field), dict):
                work[field] = dict(work[field])
                if 'reason' in work[field]:
                    work[field]['reason'] = diagnostic(work[field]['reason'], language)
    return result
