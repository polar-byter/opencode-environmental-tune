"""Loop guards: decide from the journal whether a task must stop and ask the user.

These are pure functions over the list of events. task_metrics.py appends a "halt"
event when limit_breach() returns a reason; a later "resume" event lifts it.
"""
from __future__ import annotations

if __package__:
    from .journal import normalize_work_item
    from .suite_runner import CATEGORY_FAILED, CATEGORY_INCOMPLETE, CATEGORY_NO_RESULT, CATEGORY_TIMEOUT
else:
    from journal import normalize_work_item
    from suite_runner import CATEGORY_FAILED, CATEGORY_INCOMPLETE, CATEGORY_NO_RESULT, CATEGORY_TIMEOUT

# Loop guards. Any of them stops the task until the user decides how to continue.
DEFAULT_LIMITS = dict(
    max_reworks=3,      # returns of one work item to the executor
    max_no_result=3,    # test runs in a row without readable test results (setup or build problem)
    max_failed_runs=12, # test runs in a row that are not fully green (a module of several
                        # functions stays red until its last function is done, so this is generous)
    max_runs=60,        # test runs in total; raise it with --max-runs for a large project
)


class TaskHalted(Exception):
    """The task reached a loop guard. The Master Chief must stop and ask the user."""


def since_last_resume(events: list[dict]) -> list[dict]:
    """Events after the last 'resume'; all events if the task was never resumed."""
    for index in range(len(events) - 1, -1, -1):
        if events[index]['kind'] == 'resume':
            return events[index + 1:]
    return events


def is_halted(events: list[dict]) -> dict | None:
    """The active 'halt' event, or None. A later 'resume' cancels a halt."""
    for event in reversed(events):
        if event['kind'] == 'resume':
            return None
        if event['kind'] == 'halt':
            return event
    return None


def trailing(tests: list[dict], categories: set[str]) -> int:
    """How many of the last test runs in a row fall into the given categories."""
    count = 0
    for event in reversed(tests):
        if event.get('category') not in categories:
            break
        count += 1
    return count


def limit_breach(events: list[dict], limits: dict) -> str | None:
    """
    Checks the loop guards against the journal. Returns a human-readable reason or None.

    Only events after the last 'resume' count: after the user's decision every guard
    starts from zero.
    """
    recent = [normalize_work_item(event) for event in since_last_resume(events)]
    tests = [e for e in recent if e['kind'] == 'test']
    if __package__:
        from .execution_policy import attempt_counts, budget_reason
    else:
        from execution_policy import attempt_counts, budget_reason
    isolated = {e['event_id']: e for e in events if e['kind'] == 'delegation' and e.get('workspace')}
    for item in {e['work_item'] for e in isolated.values()}:
        bindings = [e for e in events if e['kind'] == 'attempt_session'
                    and e.get('delegation_id') in isolated and isolated[e['delegation_id']]['work_item'] == item]
        if bindings:
            role = 'executor' if bindings[-1].get('fixer_enabled') is False else None
            reason = budget_reason(attempt_counts(events, item), bindings[-1].get('policy'), role)
            if reason:
                return item + ': ' + reason
    reworks, failures = {}, {}
    for event in recent:
        if event.get('delegation_id') in isolated:
            continue
        if event['kind'] == 'review' and event['result'] == 'rework':
            reworks[event['work_item']] = reworks.get(event['work_item'], 0) + 1
        elif event['kind'] == 'review' and event['result'] == 'failed':
            failures[event['work_item']] = failures.get(event['work_item'], 0) + 1
    for work_item, count in reworks.items():
        if count >= limits['max_reworks']:
            return (f'{work_item} was sent back {count} times (limit {limits["max_reworks"]}). '
                    f'The spec or the tests may be wrong.')
    # A failed attempt is not a rework, but endless retries of a broken executor must stop too.
    for work_item, count in failures.items():
        if count >= limits['max_reworks']:
            return (f'The executor failed {count} times on {work_item} without changing files '
                    f'(limit {limits["max_reworks"]}). Check that the executor model is available.')
    no_result = trailing(tests, {CATEGORY_NO_RESULT, CATEGORY_TIMEOUT})
    if no_result >= limits['max_no_result']:
        return (f'{no_result} test runs in a row gave no readable result (limit {limits["max_no_result"]}). '
                f'The project does not build or the test tool is not set up.')
    # A module's red tests must not accumulate with unrelated modules or the initial baseline.
    for scope in sorted({e.get('scope', 'full') for e in tests}):
        scoped = [e for e in tests if e.get('phase') != 'baseline' and
                  (e.get('scope', 'full') == scope or
                   (e.get('scope', 'full') == 'full' and e['status'] == 'passed'))]
        failed = trailing(scoped, {CATEGORY_FAILED, CATEGORY_INCOMPLETE, CATEGORY_NO_RESULT, CATEGORY_TIMEOUT})
        if failed >= limits['max_failed_runs']:
            return (f'{failed} test runs in a row were not green in {scope} '
                    f'(limit {limits["max_failed_runs"]}).')
    if len(tests) >= limits['max_runs']:
        return f'{len(tests)} test runs in this task (limit {limits["max_runs"]}).'
    return None


def task_limits(events: list[dict]) -> dict:
    """Limits stored in the start event; defaults for journals written before limits existed."""
    stored = events[0].get('limits')
    return dict(DEFAULT_LIMITS, **(stored if isinstance(stored, dict) else {}))
