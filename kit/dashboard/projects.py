"""Projects watched by the dashboard, their tasks and their model choice.

A project is a folder with the kit: it has opencode.jsonc and kit/. Tasks are the folders
.metrics/<task>/ that contain events.jsonl. The dashboard only reads inside the project
roots given on the command line; a task name from a URL is validated with the same rule as
task_metrics (TaskMetrics.task_dir), so "..\\" or reserved Windows names never reach the disk.

Status: SKELETON. Every function raises NotImplementedError until it is implemented.
"""
from __future__ import annotations

# Later iteration: multiple tasks and projects. Start with README.ru.md.

from dataclasses import dataclass
import json
from pathlib import Path

from ..check_env import strip_jsonc
from ..configurator import models_choices_configurator
from ..task_metrics import TaskMetrics
from . import journal

OVERLAY_PATH = Path('.opencode') / 'opencode.jsonc'


@dataclass(frozen=True)
class Project:
    """One watched project. key is a stable URL-safe id, name is shown in the UI."""
    key: str
    name: str
    root: Path


def project_key(root: Path, taken: set[str]) -> str:
    """URL-safe key from the folder name: lower case, every run of characters other than
    a-z, 0-9 replaced by one "-", stripped of "-" at both ends ("project" if nothing is left).
    If the key is already in `taken`, append "-2", "-3", ... until it is free."""
    # ПОЗЖЕ, этап нескольких проектов. root - Path папки, taken - уже занятые имена.
    # 'My Project' -> 'my-project'; имя занято -> 'my-project-2'.
    # 1. Возьми root.name, приведи к нижнему регистру.
    # 2. Обычным циклом сохраняй только a-z/0-9, группы остальных символов замени
    #    одним '-'. Удали '-' с краёв; ничего не осталось -> 'project'.
    # 3. Пока имя есть в taken, попробуй суффиксы -2, -3 и т.д. Верни свободную строку.
    # Здесь создаём имя для URL, не переименовываем папку на диске.
    raise NotImplementedError('dashboard step 3.1: project_key')


def discover(paths: list[Path]) -> list[Project]:
    """Projects for the given folders, in the given order.

    Each path is resolved. A folder without opencode.jsonc raises ValueError naming it
    (the user passed a wrong --project). The same resolved folder twice is kept once.
    name is the folder name; key comes from project_key.
    Raises:
        ValueError: a path is not a folder or has no opencode.jsonc; empty list.
    """
    # ПОЗЖЕ, после project_key. Явные пути -> список объектов Project(key, name, root).
    # Одна папка передана дважды -> один проект. [] или неправильная папка -> ValueError.
    # 1. Начни с проверки пустого списка. Для каждого пути вызови resolve().
    # 2. Проверь is_dir() и наличие opencode.jsonc; ошибка называет неверный путь.
    # 3. Уже встреченный путь пропусти. Для нового создай Project: name=root.name,
    #    key=project_key(root, занятые_ключи). Запомни путь и ключ; добавь в результат.
    # Не ищи проекты по всему диску: смотрим только переданные paths.
    raise NotImplementedError('dashboard step 3.2: discover')


def task_dir(project: Project, task: str) -> Path:
    """Folder of one task, validated exactly like TaskMetrics(project.root).task_dir(task)
    (it raises ValueError for a bad name). Does not require the folder to exist."""
    # ПОЗЖЕ. Вход: объект проекта и имя задачи, например 'demo'.
    # Результат: Path к <project.root>/.metrics/demo, даже если папки ещё нет.
    # Используй готовую TaskMetrics(project.root).task_dir(task) и верни её ответ.
    # Она уже отклоняет '../other' и запрещённые имена с ValueError.
    # Свою проверку пути не копируем: правило должно остаться единым.
    raise NotImplementedError('dashboard step 3.3: task_dir')


def list_tasks(project: Project) -> list[dict]:
    """Every task of the project, newest first (by started_at, then id).

    Look at <root>/.metrics/*/events.jsonl. Skip folders whose name task_dir rejects and
    journals that are empty or unreadable (journal.read_events raises ValueError).
    Row: id, title, status (journal.task_status), started_at, last_event_at.
    No .metrics folder -> [].
    """
    # ПОЗЖЕ, после discover/task_dir и готового чтения журнала.
    # Две папки с корректными журналами -> две строки с пятью полями из описания.
    # Нет .metrics или подходящих журналов -> [].
    # 1. Получи папку .metrics внутри project.root; начни с отсутствующей папки.
    # 2. Для каждой папки проверь имя через task_dir, прочитай events.jsonl.
    #    Неверное имя, пустой или испорченный журнал пропусти, а не всю выдачу.
    # 3. Для хорошего журнала создай строку id/title/status/started_at/last_event_at.
    #    status возьми из journal.task_status, не повторяй её условия.
    # 4. Сортируй новые задачи первыми по started_at, затем id. Способ сортировки
    #    отдельно разберём перед этапом. Чтение ошибок согласуем с тестами.
    raise NotImplementedError('dashboard step 3.4: list_tasks')


def model_choice(project: Project) -> dict:
    """What models the project uses, for the overview card.

    Keys:
        saved    models_choices_configurator.load_choices(root) — the user's choice file;
                 {} when absent; on ValueError (broken file) -> {"error": "<message>"}
        overlay  {"model": top-level "model" or None, "agents": {name: model}} read from
                 .opencode/opencode.jsonc through strip_jsonc; None when the file is absent;
                 {"error": "<message>"} when it cannot be parsed
        base     {"model": top-level "model", "agents": {name: model}} from opencode.jsonc
    "agents" maps only agents that have a str "model". Keys never appear in the result:
    the choice file stores only variable names.
    """
    # ПОЗЖЕ, обзор моделей; здесь только чтение, без изменения настроек.
    # Результат {'saved': ..., 'overlay': ..., 'base': ...}: выбор пользователя,
    # сгенерированный конфиг и основной конфиг. Это три разных источника.
    # 1. Начни с saved через models_choices_configurator.load_choices(project.root).
    #    Нет файла -> {}; ValueError -> {'error': str(error)} в saved.
    # 2. JSONC допускает комментарии: сначала strip_jsonc, затем json.loads.
    #    Добавь overlay из .opencode/opencode.jsonc: нет файла -> None.
    # 3. Аналогично извлеки model и agent->model из основного opencode.jsonc.
    #    Сохраняй только строковые model у агентов; ошибку разбора покажи как error.
    # Не возвращай конфиги целиком: там могут быть секретные значения ключей.
    raise NotImplementedError('dashboard step 3.5: model_choice')
