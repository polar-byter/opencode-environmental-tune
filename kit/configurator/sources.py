"""Lists of models the user can choose from.

Three sources:
- OpenCode itself: the command "opencode models" prints every model it can use
  (OpenCode Go, a ChatGPT subscription connected with /connect, other providers);
- an own OpenAI-compatible API: GET <baseURL>/models with the key;
- LM Studio: instances that are already loaded (kit/lmstudio_models.py does the work).

The parse_* functions are pure: text or a dict in, a list out. They are tested without
network. The other functions only fetch data and hand it to a parse_* function.

Status: SKELETON. Every function raises NotImplementedError until it is implemented.
Lines marked "ПОДСКАЗКА" are learning hints; delete them once the function is done.
"""
from __future__ import annotations

import json
import subprocess
import urllib.request

from .. import lmstudio_models
from ..run_opencode import find_opencode

TIMEOUT = 30  # seconds for any outside call


# --- Step 3. Pure parsing ------------------------------------------------------

def parse_opencode_models(text: str) -> list[str]:
    """Turn the output of "opencode models" into a list of model references.

    Every useful line starts with a reference like "openai/gpt-6.1-sol"; anything
    after the first space on that line is ignored. Lines without "/" (headers, empty
    lines, messages) are skipped.

    Returns:
        Unique references, sorted alphabetically.
    """
    # ПОДСКАЗКА: строки текста — text.splitlines(); слова строки — line.split().
    #   У пустой строки split() вернёт пустой список — его первый элемент брать нельзя.
    # ПОДСКАЗКА: уникальность — множество set(), как HashSet в Java.
    # ПОДСКАЗКА: sorted(коллекция) вернёт новый отсортированный список.
    raise NotImplementedError('step 3.1: parse_opencode_models')


def parse_api_models(data: dict) -> list[str]:
    """Take model names from an OpenAI-style answer of GET /models.

    Expected shape: {"data": [{"id": "model-a", ...}, {"id": "model-b", ...}]}.

    Returns:
        Sorted unique ids. Entries without a string "id" are skipped.

    Raises:
        ValueError: there is no "data" list (the address is probably wrong).
    """
    # ПОДСКАЗКА: data.get("data") вернёт None вместо исключения, если ключа нет.
    # ПОДСКАЗКА: isinstance(x, list), isinstance(x, dict), isinstance(x, str).
    # ПОДСКАЗКА: можно в одну строку через генератор списка (list comprehension):
    #   [item["id"] for item in items if <условие>] — см. учебник, глава 03.
    raise NotImplementedError('step 3.2: parse_api_models')


# --- Step 4. Fetching ----------------------------------------------------------

def opencode_models(command: str = 'opencode') -> list[str]:
    """Ask OpenCode which models it can use.

    Runs "<opencode> models" without a shell, waits at most TIMEOUT seconds and parses
    the output with parse_opencode_models.

    Raises:
        ValueError: OpenCode is not found (find_opencode raises it) or exits with an error;
                    the message includes the error text of OpenCode.
    """
    # ПОДСКАЗКА: путь к исполняемому файлу — find_opencode(command), она уже есть.
    # ПОДСКАЗКА: запуск: subprocess.run([exe, 'models'], capture_output=True, text=True,
    #   timeout=TIMEOUT). Результат: .returncode, .stdout, .stderr.
    # ПОДСКАЗКА: в глава 09 учебника есть пример subprocess.
    raise NotImplementedError('step 4.1: opencode_models')


def api_models(base_url: str, api_key: str) -> list[str]:
    """Ask an own API for its models: GET <base_url>/models with "Authorization: Bearer <key>".

    Returns:
        parse_api_models of the JSON answer.

    The key is used only for this request and is never printed.
    """
    # ПОДСКАЗКА: адрес: base_url.rstrip('/') + '/models'.
    # ПОДСКАЗКА: запрос с заголовками — urllib.request.Request(url, headers={...});
    #   отправка — with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
    #   JSON из ответа — json.load(response). Похожий код есть в kit/lmstudio_models.py.
    raise NotImplementedError('step 4.2: api_models')


def lmstudio_instances(base: str = lmstudio_models.DEFAULT_BASE) -> list[tuple[str, str]]:
    """Loaded LM Studio instances as (instance id, display name) pairs, sorted by name."""
    # ПОДСКАЗКА: всё уже умеет lmstudio_models.loaded_models(base). Она возвращает
    #   объекты LoadedModel с полями .id и .name. Осталось превратить их в пары.
    # ПОДСКАЗКА: пара (кортеж) пишется в круглых скобках: (model.id, model.name).
    # ПОДСКАЗКА: сортировка по второму элементу: sorted(pairs, key=lambda pair: pair[1]).
    raise NotImplementedError('step 4.3: lmstudio_instances')
