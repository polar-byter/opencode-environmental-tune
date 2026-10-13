"""Change detection for the live page (Server-Sent Events).

The browser keeps one EventSource connection to /api/stream. The server polls the files
that matter every POLL_SECONDS and sends one event per change; the page then reloads only
the affected part. Polling file size and mtime is enough: the kit appends to its journal
and rewrites the choice file and the overlay as whole files.

Status: SKELETON. Every function raises NotImplementedError until it is implemented.
Later optional optimization. Manual refresh comes first; see README.ru.md.
"""
from __future__ import annotations

import json
from pathlib import Path

POLL_SECONDS = 1.0
HEARTBEAT_SECONDS = 15.0


def stamp(path: Path) -> tuple[int, int] | None:
    """(size, mtime_ns) of the file, or None when it does not exist or cannot be read."""
    # ПОЗЖЕ, необязательное автообновление. Вход Path, выход пара чисел или None.
    # Пример: (200, 123456789) - размер 200 байтов и время последнего изменения.
    # 1. path.stat() даёт сведения о файле; возьми st_size и st_mtime_ns.
    # 2. Верни их парой. OSError (файл отсутствует/недоступен) -> None.
    # Содержимое не читаем: сравниваем сведения при следующем опросе.
    raise NotImplementedError('dashboard step 6.1: stamp')


def watched_files(roots: dict[str, Path]) -> dict[tuple[str, str], Path]:
    """Files to watch, by (project key, name).

    For every project: ("choice", .opencode/kit-models.json), ("overlay",
    .opencode/opencode.jsonc), and ("task:<id>", .metrics/<id>/events.jsonl) for every
    existing task folder. The list is rebuilt on every poll so new tasks appear.
    """
    # ПОЗЖЕ, после списка проектов. roots: {'demo': Path(...)}.
    # Результат, например: {('demo', 'choice'): Path(.../kit-models.json), ...}.
    # Пара в ключе хранит проект и назначение файла: одинаковые имена не смешаются.
    # 1. Циклом добавь choice и overlay для каждого проекта по путям выше.
    # 2. Добавь task:<id> с events.jsonl для существующих папок задач в .metrics.
    # 3. Верни новый словарь. Повторный вызов должен заметить новые папки;
    #    отсутствующая .metrics не мешает добавить choice/overlay.
    raise NotImplementedError('dashboard step 6.2: watched_files')


class ChangeWatcher:
    """Remembers the last stamp of every watched file.

    poll(files) compares the stamps with the previous call and returns change rows
    {"project", "name"} for files that appeared, changed or disappeared, sorted by
    (project, name). The very first call only records the stamps and returns [].
    """

    def __init__(self):
        self.stamps: dict[tuple[str, str], tuple[int, int] | None] | None = None

    def poll(self, files: dict[tuple[str, str], Path]) -> list[dict]:
        """See the class description."""
        # ПОЗЖЕ, после stamp. Объект помнит сведения о файлах между вызовами.
        # Первый poll -> []; файл изменился -> [{'project': 'demo', 'name': 'choice'}].
        # 1. Собери новый словарь сведений: для каждого файла вызови stamp.
        # 2. self.stamps is None означает самый первый опрос. Сохрани новые
        #    сведения и верни []; первый опрос не является изменением.
        # 3. В следующих вызовах сравни старые и новые пары по ВСЕМ ключам:
        #    важно заметить также исчезнувший файл/ключ. Различие -> строка результата.
        # 4. Обнови self.stamps и отсортируй результат по project, затем name.
        #    Ничего не изменилось -> []. Перед этапом разберём сравнение словарей.
        raise NotImplementedError('dashboard step 6.3: ChangeWatcher.poll')


def sse_message(event: str, data: dict) -> bytes:
    """One Server-Sent Event: b"event: <event>\\ndata: <compact JSON>\\n\\n", UTF-8.
    The JSON is produced with ensure_ascii=False and separators=(",", ":"), so it has no
    newline inside (a newline would end the event early)."""
    # ПОЗЖЕ, после ручного обновления. SSE - несколько текстовых строк по сети:
    # event: change
    # data: {"project":"demo"}
    # затем ПУСТАЯ строка, отмечающая конец сообщения.
    # 1. data преврати в JSON через json.dumps с настройками из описания.
    # 2. Собери текст с '\n' после event/data и ещё одним '\n' в конце.
    # 3. encode('utf-8') даёт bytes для отправки. Это не обычный JSON-ответ:
    #    служебные event:/data: нужны EventSource в браузере.
    raise NotImplementedError('dashboard step 6.4: sse_message')
