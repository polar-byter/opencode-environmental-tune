"""Projects watched by the dashboard, their tasks and their model choice.

A project is a folder with the kit: it has opencode.jsonc and kit/. Tasks are the folders
.metrics/<task>/ that contain events.jsonl. The dashboard only reads inside the project
roots given on the command line; a task name from a URL is validated with the same rule as
task_metrics (TaskMetrics.task_dir), so "..\\" or reserved Windows names never reach the disk.

Status: SKELETON. Every function raises NotImplementedError until it is implemented.
"""
from __future__ import annotations

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
    raise NotImplementedError('dashboard step 3.1: project_key')


def discover(paths: list[Path]) -> list[Project]:
    """Projects for the given folders, in the given order.

    Each path is resolved. A folder without opencode.jsonc raises ValueError naming it
    (the user passed a wrong --project). The same resolved folder twice is kept once.
    name is the folder name; key comes from project_key.
    Raises:
        ValueError: a path is not a folder or has no opencode.jsonc; empty list.
    """
    raise NotImplementedError('dashboard step 3.2: discover')


def task_dir(project: Project, task: str) -> Path:
    """Folder of one task, validated exactly like TaskMetrics(project.root).task_dir(task)
    (it raises ValueError for a bad name). Does not require the folder to exist."""
    raise NotImplementedError('dashboard step 3.3: task_dir')


def list_tasks(project: Project) -> list[dict]:
    """Every task of the project, newest first (by started_at, then id).

    Look at <root>/.metrics/*/events.jsonl. Skip folders whose name task_dir rejects and
    journals that are empty or unreadable (journal.read_events raises ValueError).
    Row: id, title, status (journal.task_status), started_at, last_event_at.
    No .metrics folder -> [].
    """
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
    raise NotImplementedError('dashboard step 3.5: model_choice')
