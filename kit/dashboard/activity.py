"""Live activity feed from OpenCode session exports: what the Master Chief and executors do now.

Pure functions over the JSON of `opencode session export <id>` (OpenCode 2.0.26 format):
    export = {"info": {"id", "title", "time", ...}, "messages": [message, ...]}
    message = {"id", "type": "assistant" | "user" | "system" | "idle", "agent",
               "model": {"providerID", "id"}, "time": {"created", "completed"} (ms),
               "content": [part, ...], "tokens": {...}}
    part = {"type": "text" | "reasoning" | "tool", ...}
    tool part = {"type": "tool", "name", "state": {"status", "input": {...}},
                 "time": {"created", "ran", "completed"}}
Reasoning text is never shown: it may be long and is not meant for the user.

Status: SKELETON. Every function raises NotImplementedError until it is implemented.
Later iteration: real OpenCode exports. Start with README.ru.md.
"""
from __future__ import annotations

# Longest text shown for one feed item; longer text ends with "…".
MAX_TEXT = 160
# Tool input keys shown as the target of a call, in priority order.
TARGET_KEYS = ('path', 'filePath', 'command', 'pattern', 'description', 'url')


def shorten(text: str, limit: int = MAX_TEXT) -> str:
    """Collapse all whitespace runs to one space and strip; if longer than limit characters,
    cut to limit-1 characters and append "…" (so the result has exactly limit characters)."""
    # ПОЗЖЕ, этап ленты OpenCode. Вход - текст, выход - короткая строка.
    # Примеры: '  a \n b  ' -> 'a b'; 'abcdefgh', limit=5 -> 'abcd…'.
    # 1. text.split() разбивает по любым пробелам/переносам; ' '.join(...) соединяет
    #    слова одним пробелом. Сначала попробуй только эту очистку.
    # 2. Если длина больше limit, оставь первые limit-1 символов и добавь '…'.
    #    Если равна limit или меньше - не обрезай. Пустой текст -> ''.
    raise NotImplementedError('dashboard step 2.1: shorten')


def tool_target(part: dict) -> str:
    """Short human target of a tool call: the first present non-empty str value among
    TARGET_KEYS in part["state"]["input"], passed through shorten(). "" when none.
    Must not fail on a missing or non-dict state/input."""
    # ПОЗЖЕ, после shorten. Показываем, с чем работал инструмент.
    # {'state': {'input': {'path': 'app.py'}}} -> 'app.py'; {} -> ''.
    # 1. Достань state через get; если не dict, верни ''. Затем так же input.
    # 2. Перебирай TARGET_KEYS по порядку: path важнее command, если есть оба.
    # 3. Первую непустую строку передай shorten и верни. Другие типы пропускай.
    #    Ничего не найдено -> ''. Вложенные [] или строки не должны вызвать ошибку.
    raise NotImplementedError('dashboard step 2.2: tool_target')


def feed_items(export: dict, session_role: str) -> list[dict]:
    """Feed rows of one session, oldest first.

    Only assistant messages count. For each part in message["content"]:
      - "text" with non-blank text -> kind "text", text = shorten(text)
      - "tool"                     -> kind "tool", tool = part["name"], target = tool_target(part),
                                      status = part["state"]["status"] (None if absent)
      - anything else (reasoning, unknown) is skipped
    Every row also has: session (export info id), role (session_role, e.g. "master_chief" or
    "executor"), agent (message "agent"), model ("providerID/id" or "unknown"), and at
    (seconds: part time "created" if present, else message time "created", divided by 1000).
    """
    # ПОЗЖЕ, после shorten/tool_target. export - словарь разговора, НЕ events.jsonl.
    # session_role приходит готовой строкой ('master_chief' или 'executor').
    # Пример: assistant с текстом и read('TASK.md') -> две строки: text и tool.
    # user/reasoning/пустой текст не входят. Время 1500 мс -> at=1.5 секунды.
    # 1. Сначала разберём пример export из tests/test_activity.py: messages -
    #    список сообщений, content у каждого - список частей сообщения.
    # 2. Начни с двух циклов: по assistant-сообщениям, затем по их content.
    #    Добавляй только непустой text с shorten; пока без инструментов.
    # 3. Добавь общие поля строки из описания: session, role, agent, model, at.
    #    Нет модели -> 'unknown'; нет времени части -> время сообщения / 1000.
    # 4. Затем добавь tool с tool_target и status (нет -> None). Верни строки
    #    от старых к новым. Не запускай CLI из этой функции.
    raise NotImplementedError('dashboard step 2.3: feed_items')


def merge_feeds(feeds: list[list[dict]], limit: int = 50) -> list[dict]:
    """Merge several feeds into one, sorted by "at" ascending (stable for equal "at"),
    and keep only the newest `limit` rows."""
    # ПОЗЖЕ, после feed_items. Вход - несколько списков, выход - один список.
    # [[{'at': 1}, {'at': 3}], [{'at': 2}]], limit=2 -> [{'at': 2}, {'at': 3}].
    # 1. Двумя циклами добавь все строки в общий список.
    # 2. Отсортируй по at: sort(key=...) получает функцию, возвращающую время строки.
    #    Перед упражнением разберём такую функцию; lambda не обязательна.
    # 3. Оставь последние limit строк (самые новые), но их порядок - от старых к новым.
    #    При одинаковом at Python-сортировка сохраняет прежний порядок. [] -> [].
    raise NotImplementedError('dashboard step 2.4: merge_feeds')


def current_step(export: dict) -> dict | None:
    """What the session is doing right now, or None if it is idle.

    Look at the last assistant message. If it has no time.completed, the session is busy:
    return its last tool part with status "running" or "pending" as
    {"tool", "target", "since"}, or, if there is none, {"tool": None, "target": "", "since":
    message created / 1000}. "since" for a tool is its time.created / 1000.
    A completed last message (or no assistant message) means idle -> None.
    """
    # ПОЗЖЕ, после tool_target. Это активность РАЗГОВОРА, не task_status задачи.
    # Последнее assistant-сообщение завершено -> None. Не завершено и запускает
    # bash в 3000 мс -> {'tool': 'bash', 'target': ..., 'since': 3.0}.
    # 1. Циклом запомни последнее assistant-сообщение. Нет такого -> None.
    # 2. Есть time.completed -> None; иначе разговор пока занят.
    # 3. Среди его частей запомни последний tool со status running/pending.
    #    Верни его name, tool_target(part), время created / 1000.
    # 4. Нет активного инструмента -> tool=None, target='', since=время сообщения / 1000.
    raise NotImplementedError('dashboard step 2.5: current_step')
