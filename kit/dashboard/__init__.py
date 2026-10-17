"""Local web dashboard for the kit: tasks, orchestration timeline, metrics and model settings.

task_metrics.py start launches it automatically (launcher.py -> runtime.py); see README.ru.md.
Hand-written examples of one task from a journal file:
    py -m kit.dashboard.console kit/dashboard/examples/events.jsonl
    py -m kit.dashboard.simple kit/dashboard/examples/events.jsonl
"""
