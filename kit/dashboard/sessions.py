"""OpenCode sessions of a task: token usage by model group and the live activity feed.

Exporting sessions runs the OpenCode CLI and takes seconds, so results are cached per
root session for CACHE_SECONDS. The CLI is found by kit/opencode_cli.py (through
TaskMetrics.collect_exports) — the same OpenCode the rest of the kit uses.

Status: SKELETON. Every function raises NotImplementedError until it is implemented.
Later iteration: tokens and CLI integration. Start with README.ru.md.
"""
from __future__ import annotations

from pathlib import Path
import threading
import time

from ..task_metrics import TaskMetrics
from . import activity

CACHE_SECONDS = 15
GROUPS = ('paid', 'local', 'free', 'unknown')
TOKEN_FIELDS = ('input', 'output', 'reasoning', 'cache_read', 'cache_write')


def group_totals(usage: dict) -> dict:
    """Sum the rows of TaskMetrics.parse_exports(...)["models"] by their "group".

    Returns {group: {field: total}} for every group in GROUPS (all fields 0 when the group
    has no rows). If any row of a group has None in a field, the group total of that field
    is None: an unknown part makes the sum unknown.
    """
    # ПОЗЖЕ, этап токенов. usage уже готов: его models - список строк по моделям.
    # Две local-модели с input=2 и input=3 -> totals['local']['input']=5.
    # Если у одной input=None -> сумма input=None, не 2: часть данных неизвестна.
    # 1. Создай по словарю счётчиков с нулями для каждой группы GROUPS.
    # 2. Перебирай usage['models']; для её group перебирай TOKEN_FIELDS.
    # 3. Складывай известные числа. Если встретился None, оставь итог None,
    #    даже если следующие строки содержат числа. Другие поля считай независимо.
    # Пустой models -> все группы со всеми полями 0. Здесь не собираем данные CLI.
    raise NotImplementedError('dashboard step 5.1: group_totals')


def session_roles(exports: list[dict], root_session: str) -> dict:
    """{session id: role}: "master_chief" for root_session, "executor" for every other
    exported session (children are created by the Master Chief's task tool)."""
    # ПОЗЖЕ. Сессия - разговор OpenCode; её id лежит в export['info']['id'].
    # Например id='root' и 'child', root_session='root' ->
    # {'root': 'master_chief', 'child': 'executor'}.
    # Перебери exports, сравни каждый id с root_session, запиши роль в словарь.
    # Нет exports -> {}. Не путай id разговора с task ID или work_item.
    raise NotImplementedError('dashboard step 5.2: session_roles')


class SessionCache:
    """Cached exports per (project root, root session).

    fetch(root, session) returns the list of exports from
    TaskMetrics(root).collect_exports(session); a second call within CACHE_SECONDS returns the
    cached list without running the CLI. `clock` is injectable for tests (default
    time.monotonic). The cache is shared by server threads, so access is guarded by a lock.
    On error the exception propagates and nothing is cached.
    """

    def __init__(self, clock=time.monotonic, collect=None):
        self.clock = clock
        # collect(root, session) -> exports; tests pass a fake instead of the real CLI.
        self.collect = collect or (lambda root, session: TaskMetrics(root).collect_exports(session))
        self.lock = threading.Lock()
        self.entries: dict[tuple[str, str], tuple[float, list[dict]]] = {}

    def fetch(self, root: Path, session: str) -> list[dict]:
        """Exports of the session tree, cached (see the class description)."""
        # ПОЗЖЕ, после обычного получения экспорта. Кэш - временно сохранённый ответ.
        # Два вызова для того же проекта/сессии за 15 секунд -> collect вызывается один раз.
        # 1. Ключ записи включает str(root) И session: разные проекты не смешиваются.
        # 2. self.clock() даёт время; entries хранит время получения и список exports.
        #    Есть запись моложе CACHE_SECONDS -> верни её список.
        # 3. Иначе вызови self.collect(root, session), сохрани время/список и верни список.
        #    Если collect бросил ошибку, её не скрывай и новую запись не сохраняй.
        # 4. Доступ защищает self.lock: сервер может вызвать fetch из двух потоков.
        #    Перед этапом разберём 'with self.lock' и подставные clock/collect в тестах.
        # Не запускай CLI напрямую: готовая self.collect делает это или заменяется тестом.
        raise NotImplementedError('dashboard step 5.3: SessionCache.fetch')


def task_sessions(cache: SessionCache, root: Path, events: list[dict], now: float) -> dict:
    """Everything the task page shows about sessions.

    The root session is events[0]["session"]; without it -> {"available": False,
    "reason": "the task was started without --session"}.
    Otherwise exports = cache.fetch(root, session); usage =
    TaskMetrics(root).parse_exports(exports, session, start at, finish "ended" or now).
    Returns {"available": True, "groups": group_totals(usage), "models": usage["models"],
    "warnings": usage["warnings"], "feed": activity.merge_feeds([...feed_items per export
    with its role...]), "now": {session id: activity.current_step(export)} for busy sessions}.
    A ValueError from the CLI or the parser -> {"available": False, "reason": str(error)}.
    """
    # ПОЗЖЕ, когда готовы кэш, group_totals и activity. Это данные для страницы токенов.
    # Нет session у start -> {'available': False, 'reason': ...}, не ошибка и не нули.
    # 1. Начни с этого случая. Затем получи exports через cache.fetch(root, session).
    # 2. parse_exports готового TaskMetrics считает usage за интервал задачи:
    #    start.at -> finish.ended, либо now, если задача ещё идёт.
    # 3. Получи groups через group_totals; models/warnings возьми из usage.
    # 4. session_roles задаёт роль каждому export. Для каждого вызови feed_items;
    #    списки передай merge_feeds. В now включи только НЕ None из current_step.
    # 5. Собери ответ с available=True и полями выше. ValueError от CLI/разбора
    #    преврати в available=False с reason=str(error), не в «0 токенов».
    # Начнём с одного export и каждого поля отдельно, не всего ответа сразу.
    raise NotImplementedError('dashboard step 5.4: task_sessions')
