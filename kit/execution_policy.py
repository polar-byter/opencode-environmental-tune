"""Pure limits and escalation decisions; no sessions, IO or journal mutations."""
from __future__ import annotations

import math


DEFAULT_POLICY = {
    'maxExecutors': 1,
    'maxSteps': 24,
    'maxSeconds': 600,
    'maxRepeatedActions': 3,
    'fixerMaxSteps': 32,
    'fixerMaxSeconds': 600,
}


def normalize_policy(value: dict | None = None) -> dict:
    """Return an independent complete policy, preserving legacy sequential defaults.

    None and an empty dict use DEFAULT_POLICY. Accept a partial dict with only
    the default keys; do not mutate the input or DEFAULT_POLICY. Every supplied
    value must be an int, not bool. Ranges are inclusive: maxExecutors 1..8,
    maxSteps/fixerMaxSteps 1..256, maxSeconds/fixerMaxSeconds 1..3600,
    maxRepeatedActions 2..32. Reject non-dicts, unknown keys, invalid types and
    out-of-range values with ValueError. Never coerce strings or floats.
    """
    if value is None:
        value = {}
    if not isinstance(value, dict) or value.keys() - DEFAULT_POLICY.keys():
        raise ValueError('Unknown execution policy fields')
    result = dict(DEFAULT_POLICY)
    bounds = {'maxExecutors': (1, 8), 'maxRepeatedActions': (2, 32),
              'maxSteps': (1, 256), 'fixerMaxSteps': (1, 256),
              'maxSeconds': (1, 3600), 'fixerMaxSeconds': (1, 3600)}
    for key, number in value.items():
        low, high = bounds[key]
        if type(number) is not int or not low <= number <= high:
            raise ValueError(f'{key} must be an integer between {low} and {high}')
        result[key] = number
    return result


def limit_reason(*, steps: int, repeated_actions: int, elapsed_seconds: float,
                 policy: dict | None = None) -> str | None:
    """Classify public execution counters without interpreting private reasoning.

    Validate policy with normalize_policy. steps/repeated_actions are nonnegative
    ints (not bool); elapsed_seconds is a finite nonnegative int/float, not bool.
    Invalid input raises ValueError. Return step_limit at steps >= maxSteps;
    otherwise repeated_actions at repeated_actions >= maxRepeatedActions;
    otherwise deadline at elapsed_seconds >= maxSeconds; else None. This order
    is deterministic. The controller supplies repeated_actions only for identical
    public tool actions without verified result/file progress. A stale progress
    file or no events alone must never increment this counter. A returned reason
    is a signal, not evidence that an executing session has already stopped.
    """
    policy = normalize_policy(policy)
    if any(type(n) is not int or n < 0 for n in (steps, repeated_actions)):
        raise ValueError('Execution counters must be nonnegative integers')
    if (isinstance(elapsed_seconds, bool) or not isinstance(elapsed_seconds, (int, float))
            or not math.isfinite(elapsed_seconds) or elapsed_seconds < 0):
        raise ValueError('Elapsed time must be finite and nonnegative')
    if steps >= policy['maxSteps']:
        return 'step_limit'
    if repeated_actions >= policy['maxRepeatedActions']:
        return 'repeated_actions'
    if elapsed_seconds >= policy['maxSeconds']:
        return 'deadline'
    return None


def next_action(role: str, reason: str, *, fixer_enabled: bool,
                fixer_attempts: int = 0) -> str:
    """Choose a bounded failure route after the old attempt has actually stopped.

    Roles are executor or bug_fixer. Reasons implementation_error, step_limit,
    repeated_actions and deadline return bug_fixer only for executor, with an
    explicitly enabled fixer and zero previous fixer attempts; otherwise stop.
    Reasons api_error, rate_limit and setup_error always return blocked, without
    a model switch. Reasons paused and cancelled always return stop. Unknown role
    or reason raises ValueError. fixer_enabled must be bool; fixer_attempts must
    be a nonnegative int, not bool. Validate all arguments before deciding.
    No retries, key access, side effects or implicit model inheritance. There is
    at most one fixer attempt and no route back to executor. This decision never
    overrides task pause/cancel state or the existing global STOP guards.
    """
    implementation = ('implementation_error', 'step_limit', 'repeated_actions', 'deadline')
    infrastructure = ('api_error', 'rate_limit', 'setup_error')
    if (role not in ('executor', 'bug_fixer') or reason not in implementation + infrastructure + ('paused', 'cancelled')
            or type(fixer_enabled) is not bool or type(fixer_attempts) is not int or fixer_attempts < 0):
        raise ValueError('Invalid failure routing arguments')
    if reason in infrastructure:
        return 'blocked'
    if reason in implementation and role == 'executor' and fixer_enabled and fixer_attempts == 0:
        return 'bug_fixer'
    return 'stop'
