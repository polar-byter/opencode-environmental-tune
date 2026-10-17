# Dashboard

The dashboard is a read-only view of a task: it reads the journal
(`.metrics/<ID>/events.jsonl`) and OpenCode sessions; `kit/task_metrics.py` owns the rules.
Start with README.ru.md.

- Operational code: `launcher.py` (start, reuse, stop), `runtime.py` (JSON API and
  `static/runtime.html`), `tracking.py`, `observations.py`, `delivery.py`, `controls.py`,
  `session_control.py`, `quota_monitor.py`.
- `journal.py` reads the journal for the views (`read_events`, `brief_summary`).
  Loop guard rules live only in `kit/loop_guards.py`; do not duplicate them here.
- `console.py`, `simple.py` and `static/simple.html` are small hand-written examples
  from learning Python. Keep them working and keep the user's own comments in them.
- The page stays plain HTML/JavaScript without frameworks.
- Source comments and docstrings are English; human-facing docs may be Russian.
- Run the dashboard tests from the project root:
  `py -m unittest discover -s kit/dashboard/tests -t .`
