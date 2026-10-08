"""Build, validate, read and write the choice file .opencode/kit-models.json.

The file format is a contract with kit/run_opencode.py (see load_choices there):

    {
      "brain":     {"source": "opencode", "model": "provider/model"}
                   or {"source": "api", "baseURL": ..., "model": ..., "keyEnv": ...},
      "executors": {"source": "lmstudio"} or {"source": "lmstudio", "instance": ...}
                   or {"source": "api", "baseURL": ..., "model": ..., "keyEnv": ...}
    }

A missing section means "use the default". A missing file means "use the defaults".

Status: SKELETON. Every function raises NotImplementedError until it is implemented.
Lines marked "ПОДСКАЗКА" are learning hints; delete them once the function is done.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

# Where the choice file lives, relative to the project root.
CHOICES_PATH = Path('.opencode') / 'kit-models.json'

# A valid environment variable name: a letter or "_", then letters, digits or "_".
ENV_NAME = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')


# --- Step 1. Small dictionaries ------------------------------------------------

def brain_from_opencode(model: str) -> dict:
    """Choice "the brain uses a model that OpenCode already knows".

    Args:
        model: reference like "openai/gpt-6.1-sol" or "opencode-go/deepseek-v4.1-flash".

    Returns:
        {"source": "opencode", "model": <model without surrounding spaces>}

    Raises:
        ValueError: the model is empty or has no "/" (a provider name is required).
    """
    # ПОДСКАЗКА: это аналог маленького фабричного метода в Java, только вместо
    #   объекта возвращаем словарь. Словарь пишется так: {"key": value, ...}.
    # ПОДСКАЗКА: пробелы по краям убирает метод строки .strip().
    # ПОДСКАЗКА: проверка "есть ли подстрока" — оператор in: "/" in text.
    # ПОДСКАЗКА: ошибка выбрасывается как в Java, только слово другое: raise ValueError("...").
    raise NotImplementedError('step 1.1: brain_from_opencode')


def api_choice(base_url: str, model: str, key_env: str) -> dict:
    """Choice "use an own OpenAI-compatible API".

    Args:
        base_url: endpoint like "https://api.example.com/v1".
        model: model name at that service.
        key_env: NAME of the environment variable with the key, not the key itself.

    Returns:
        {"source": "api", "baseURL": <url without trailing "/">,
         "model": <model>, "keyEnv": <key_env>}; all values without surrounding spaces.

    Raises:
        ValueError: an empty value; the URL does not start with http:// or https://;
                    key_env is not a valid variable name (see ENV_NAME).
    """
    # ПОДСКАЗКА: сначала почисти все три строки через .strip(), потом проверяй.
    # ПОДСКАЗКА: "начинается с" — метод .startswith(...). Ему можно передать кортеж
    #   из двух вариантов сразу: text.startswith(('http://', 'https://')).
    # ПОДСКАЗКА: хвостовой "/" убирает .rstrip('/').
    # ПОДСКАЗКА: строка целиком подходит под шаблон, если ENV_NAME.fullmatch(text) не None.
    # ПОДСКАЗКА: пустая строка в Python ложна: if not text: ...
    raise NotImplementedError('step 1.2: api_choice')


def lmstudio_choice(instance: str | None = None) -> dict:
    """Choice "executors use the model already loaded in LM Studio".

    Args:
        instance: ID of a loaded instance, or None to let the launcher pick
                  the only loaded model. An empty or blank string counts as None.

    Returns:
        {"source": "lmstudio"} when there is no instance,
        {"source": "lmstudio", "instance": <instance>} otherwise.
    """
    # ПОДСКАЗКА: None в Python — это null в Java. Проверка: if instance is None.
    # ПОДСКАЗКА: и None, и пустая строка ложны, поэтому хватит одного if not ...
    #   Но " " (пробел) истинен — сначала .strip(), только не у None!
    raise NotImplementedError('step 1.3: lmstudio_choice')


def build_choices(brain: dict | None, executors: dict | None) -> dict:
    """Combine both sections into the content of the choice file.

    A section that is None is left out: the launcher will use its default.

    Returns:
        dict with keys "brain" and/or "executors"; {} when both are None.
    """
    # ПОДСКАЗКА: начни с пустого словаря result = {} и добавляй ключи по условию:
    #   result["brain"] = brain
    raise NotImplementedError('step 1.4: build_choices')


# --- Step 2. The file on disk --------------------------------------------------

def load_choices(root: Path) -> dict:
    """Read the choice file of the project.

    Args:
        root: project root folder.

    Returns:
        The dictionary from the file, or {} when the file does not exist.

    Raises:
        ValueError: the file is not valid JSON or does not contain a JSON object.
    """
    # ПОДСКАЗКА: полный путь = root / CHOICES_PATH (оператор / склеивает пути у Path).
    # ПОДСКАЗКА: существует ли файл — path.exists(); текст — path.read_text(encoding='utf-8').
    # ПОДСКАЗКА: текст в словарь — json.loads(text). Битый JSON бросает json.JSONDecodeError;
    #   поймай её и брось ValueError с понятным текстом (try / except ... as error).
    # ПОДСКАЗКА: "это словарь?" — isinstance(data, dict).
    raise NotImplementedError('step 2.1: load_choices')


def save_choices(root: Path, choices: dict) -> Path:
    """Write the choice file safely and return its path.

    Writes to a temporary file next to the target first and then replaces the target.
    If the program crashes in the middle, the old file stays whole.
    Creates the .opencode folder when it is missing. JSON is indented by 2 spaces,
    UTF-8, non-ASCII characters are kept as is, and the file ends with a newline.
    """
    # ПОДСКАЗКА: папка — path.parent; создать вместе с родителями без ошибки, если есть:
    #   folder.mkdir(parents=True, exist_ok=True).
    # ПОДСКАЗКА: временный файл рядом: path.with_name(path.name + '.tmp').
    # ПОДСКАЗКА: словарь в текст — json.dumps(choices, ensure_ascii=False, indent=2).
    # ПОДСКАЗКА: замена одним шагом — temporary.replace(path). Этот же приём есть
    #   в kit/run_opencode.py, функция prepare — подсмотри.
    raise NotImplementedError('step 2.2: save_choices')


def reset_choices(root: Path) -> bool:
    """Delete the choice file to return to the defaults.

    Returns:
        True when the file existed and was deleted, False when there was nothing to delete.
    """
    # ПОДСКАЗКА: удалить файл — path.unlink().
    raise NotImplementedError('step 2.3: reset_choices')
