"""Read a task journal (.metrics/<task>/events.jsonl) and turn it into dashboard views.

The journal is written by kit/task_metrics.py while a task runs, so every reader here must
tolerate a writer that is still appending. Pure functions take the list of events; only
read_events and JournalTail touch the disk.

Event kinds (see task_metrics.EVENT_KINDS): start, delegation, inspection, review, test,
halt, resume, finish. Every event has "kind", "at" (Unix seconds) and "event_id".
inspection/review link to their delegation through "delegation_id".

Status: SKELETON. Every function raises NotImplementedError until it is implemented.
Lines marked "ПОДСКАЗКА" are learning hints; delete them once the function is done.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..task_metrics import (CATEGORY_FAILED, CATEGORY_INCOMPLETE, CATEGORY_NO_RESULT, CATEGORY_TIMEOUT,
                            DEFAULT_LIMITS, is_halted, since_last_resume, task_limits, trailing)

RUNNING, HALTED, FINISHED = 'running', 'halted', 'finished'

# Piece states shown on the timeline.
AT_EXECUTOR = 'executor'   # delegated, the executor has not returned (no inspection yet)
IN_REVIEW = 'review'       # inspected, no review recorded yet
ACCEPTED = 'accepted'      # the latest attempt was accepted
REWORK = 'rework'          # the latest attempt was sent back and no new attempt started yet
FAILED = 'failed'          # the executor returned no work and changed no files (error, rate limit)

NOT_GREEN = {CATEGORY_FAILED, CATEGORY_INCOMPLETE, CATEGORY_NO_RESULT, CATEGORY_TIMEOUT}


def parse_event(line: str, number: int) -> dict:
    """Parse one journal line into an event.

    Returns the decoded dict. It must be a dict with a str "kind" and an int/float "at"
    (bool is not a number).
    Raises:
        ValueError: invalid JSON or wrong shape; the message contains "line <number>".
    """
    # ПОДСКАЗКА: json.loads(line) превращает строку в dict/list/число. На плохом JSON он
    #   бросает json.JSONDecodeError — это подкласс ValueError. Поймай его через try/except
    #   и брось свой ValueError с номером строки: raise ValueError(...) from error
    #   (from сохраняет исходную причину в трассировке, как cause в Java).
    # ПОДСКАЗКА: проверка типа — isinstance(x, dict), isinstance(x, str).
    # ПОДСКАЗКА: ловушка — в Python bool является подклассом int: isinstance(True, int) == True.
    #   Поэтому для "at" нужно отдельно исключить bool. Посмотри, как это сделано в
    #   task_metrics.valid_number.
    raise NotImplementedError('dashboard step 1.1: parse_event')


def read_events(path: Path) -> list[dict]:
    """All events of one journal file, in file order.

    - Missing file -> [] (the task folder may exist before the first event).
    - Blank lines are skipped.
    - The LAST non-blank line may be cut in half by a writer that is still appending:
      if it is not valid JSON, it is ignored. Any earlier bad line raises ValueError
      (through parse_event, with its 1-based line number).
    - Read as UTF-8 text; a BOM at the start is accepted.
    """
    # ПОДСКАЗКА: Path.exists(); Path.read_text(encoding=...) — кодировка 'utf-8-sig' сама
    #   убирает BOM (так же сделано в kit/delegation_guard.py).
    # ПОДСКАЗКА: text.splitlines() — список строк без '\n'. Номер строки для сообщения
    #   удобно брать из enumerate(lines, start=1) — как цикл for с индексом в Java.
    # ПОДСКАЗКА: сначала отбери непустые строки вместе с их номерами (line.strip() пустая —
    #   строка пустая), тогда «последняя непустая» — это просто последний элемент списка.
    #   Для неё ошибку parse_event проглоти, для остальных — пропусти дальше (raise).
    raise NotImplementedError('dashboard step 1.2: read_events')


class JournalTail:
    """Incremental reader for the live view: each call returns only the new events.

    Keeps the byte offset of the first unread byte. A trailing line without "\\n" is not
    consumed yet: the writer may still be appending it, so the offset stays before it.
    If the file is now shorter than the offset (recreated), reading restarts from 0 and
    self.reset becomes True for that call (False otherwise). A missing file returns [].
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self.offset = 0
        self.reset = False

    def new_events(self) -> list[dict]:
        """Events appended since the previous call (see the class description)."""
        # ПОДСКАЗКА: работай с байтами, а не с текстом: self.path.read_bytes(). Смещение
        #   считается в байтах, а русская буква в UTF-8 занимает 2 байта.
        # ПОДСКАЗКА: срез data[self.offset:] — «всё начиная с позиции» (как substring).
        #   bytes.rfind(b'\n') находит последний перевод строки; всё после него — недописанная
        #   строка, её пока не трогаем.
        # ПОДСКАЗКА: перед декодированием готового куска: chunk.decode('utf-8-sig'), затем
        #   строки разбираются через parse_event. Не забудь сдвинуть self.offset.
        # ПОДСКАЗКА: self.reset в начале каждого вызова сбрасывай в False — тест это проверяет.
        raise NotImplementedError('dashboard step 1.3: JournalTail.new_events')


def task_status(events: list[dict]) -> str:
    """FINISHED if any finish event exists; otherwise HALTED if task_metrics.is_halted(events)
    returns an event; otherwise RUNNING.
    Raises:
        ValueError: events is empty.
    """
    # ПОДСКАЗКА: пустой список в Python ложен: if not events: ...
    # ПОДСКАЗКА: any(условие for e in events) — True, если условие верно хотя бы для одного
    #   элемента (как stream().anyMatch() в Java). Функция is_halted уже импортирована.
    raise NotImplementedError('dashboard step 1.4: task_status')


def pieces(events: list[dict]) -> list[dict]:
    """One row per delegated piece, in the order of its first delegation.

    Row fields:
        piece        piece name
        files        files of the latest delegation of this piece
        scope        scope of the latest delegation (piece name if missing)
        attempts     number of delegation events for this piece
        reworks      number of reviews with result "rework" for this piece
        failures     number of reviews with result "failed" (not reworks)
        state        AT_EXECUTOR | IN_REVIEW | ACCEPTED | REWORK | FAILED, from the latest
                     attempt: no inspection and no review -> AT_EXECUTOR; inspection but no
                     review -> IN_REVIEW; review accepted -> ACCEPTED; rework -> REWORK;
                     failed -> FAILED
        started_at   "at" of the first delegation
        accepted_at  "at" of the accepting review of the latest attempt, else None
        unexpected   sorted unique files listed in "unexpected" of its inspections and reviews

    An inspection/review belongs to the delegation whose event_id equals its delegation_id.
    Without delegation_id (old journals) it belongs to the latest earlier delegation of the
    same piece. Inspections/reviews of an unknown piece are ignored.
    """
    # ПОДСКАЗКА: это самая большая функция шага — делай в два прохода.
    #   1) Один проход по событиям: строки частей в dict {piece: row} и попытки в dict
    #      {event_id делегирования: {...что известно о попытке...}}. С Python 3.7 dict
    #      помнит порядок вставки — как LinkedHashMap, поэтому «порядок первого
    #      делегирования» получится сам.
    #   2) Второй проход по строкам: состояние по последней попытке каждой части.
    # ПОДСКАЗКА: dict.setdefault(key, default) — вернуть значение или сначала положить
    #   default (как computeIfAbsent).
    # ПОДСКАЗКА: для unexpected удобен set(): .update(список) добавляет без повторов;
    #   в конце sorted(множество) даёт отсортированный список.
    # ПОДСКАЗКА: event.get('delegation_id') вернёт None, если ключа нет, — без исключения.
    raise NotImplementedError('dashboard step 1.5: pieces')


def test_runs(events: list[dict]) -> list[dict]:
    """Every test event as a uniform row, in journal order.

    Row: at, scope (default "full"), phase (default "work"), status, category,
    tests, failures, errors, skipped, duration (from "duration_seconds").
    A counter missing from the event stays None: unknown is not zero.
    """
    # ПОДСКАЗКА: e.get('scope', 'full') — значение по умолчанию, если ключа нет.
    # ПОДСКАЗКА: всю функцию можно записать одним списковым включением:
    #   [dict(...) for e in events if e['kind'] == 'test'] — как stream().filter().map().
    raise NotImplementedError('dashboard step 1.6: test_runs')


def guard_status(events: list[dict]) -> list[dict]:
    """Current value of every loop guard, computed exactly like task_metrics.limit_breach.

    One row per name in DEFAULT_LIMITS order: {name, value, limit, detail}.
    Only events after the last resume count (since_last_resume).
        max_reworks      largest per-piece count of rework reviews or of failed reviews (each
                         is checked against this limit separately, as in limit_breach);
                         detail = that piece (the first one in journal order on a tie, reworks
                         before failures), or None when 0
        max_no_result    trailing(tests, {no_result, timeout}); detail None
        max_failed_runs  largest trailing(scoped, NOT_GREEN) over scopes, where "scoped" is
                         built as in limit_breach (baseline excluded, green full runs reset
                         every scope); detail = that scope (the first in sorted order on a
                         tie, as limit_breach checks them), or None when 0
        max_runs         number of test runs; detail None
    limit comes from task_limits(events).
    """
    # ПОДСКАЗКА: открой kit/task_metrics.py, функцию limit_breach, и повтори её подсчёт.
    #   Разница одна: limit_breach останавливается на первом превышении, а здесь нужно
    #   посчитать значение каждого лимита. since_last_resume и trailing уже импортированы.
    # ПОДСКАЗКА: «ничья по максимуму — первый по порядку» получается, если обновлять
    #   максимум только при строго большем значении (>), а не при >=.
    # ПОДСКАЗКА: строки результата — в порядке ключей DEFAULT_LIMITS: for name in DEFAULT_LIMITS.
    raise NotImplementedError('dashboard step 1.7: guard_status')


def summary(events: list[dict]) -> dict:
    """Header of the task page.

    Keys: title (start.title), session (start.session), status (task_status),
    started_at (start.at), ended_at (finish "ended" if finished, else None),
    last_event_at (at of the last event), pieces (len of pieces()), reworks (total
    rework reviews), failures (total failed reviews), work_runs and green_work_runs
    (non-baseline tests; green = status "passed"), last_full (the last non-baseline test
    row with scope "full", or None), halt_reason (reason of the active halt, or None).
    """
    # ПОДСКАЗКА: собирай из уже готовых функций шага: task_status, pieces, test_runs, is_halted.
    #   Своей логики здесь почти нет — это «сборщик».
    # ПОДСКАЗКА: events[-1] — последний элемент списка (как list.get(list.size() - 1)).
    # ПОДСКАЗКА: sum(1 for e in events if ...) — счётчик по условию; True считается как 1,
    #   поэтому работает и sum(r['status'] == 'passed' for r in runs).
    raise NotImplementedError('dashboard step 1.8: summary')
