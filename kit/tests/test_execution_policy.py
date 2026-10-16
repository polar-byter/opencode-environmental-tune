"""Contract tests for independent execution limits and failure routing."""
import math
import unittest

from kit.execution_policy import DEFAULT_POLICY, limit_reason, next_action, normalize_policy


class ExecutionPolicyTests(unittest.TestCase):
    def test_legacy_defaults_and_independent_copy(self):
        first = normalize_policy()
        self.assertEqual(first, DEFAULT_POLICY)
        self.assertEqual(first['maxExecutors'], 1)
        first['maxExecutors'] = 8
        self.assertEqual(normalize_policy()['maxExecutors'], 1)
        self.assertEqual(normalize_policy({}), DEFAULT_POLICY)

    def test_partial_input_is_not_mutated(self):
        value = {'maxExecutors': 2}
        result = normalize_policy(value)
        self.assertEqual(value, {'maxExecutors': 2})
        self.assertEqual(result['maxExecutors'], 2)
        self.assertEqual(result['maxSteps'], 24)

    def test_inclusive_bounds(self):
        bounds = {'maxExecutors': (1, 8), 'maxSteps': (1, 256),
                  'fixerMaxSteps': (1, 256), 'maxSeconds': (1, 3600),
                  'fixerMaxSeconds': (1, 3600), 'maxRepeatedActions': (2, 32),
                  'executorMaxAttempts': (1, 100), 'fixerMaxAttempts': (1, 100), 'maxAttempts': (1, 200)}
        for key, values in bounds.items():
            for number in values:
                with self.subTest(key=key, number=number):
                    self.assertEqual(normalize_policy({key: number})[key], number)
            for number in (values[0] - 1, values[1] + 1):
                with self.subTest(key=key, number=number), self.assertRaises(ValueError):
                    normalize_policy({key: number})

    def test_rejects_coercion_and_unknown_fields(self):
        for value in ([], '', False, 1, {'parallel': 2}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_policy(value)
        for key in DEFAULT_POLICY:
            for value in (True, False, 2.0, '2', None):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    normalize_policy({key: value})

    def test_limits_and_priority(self):
        self.assertIsNone(limit_reason(steps=0, repeated_actions=0, elapsed_seconds=0))
        self.assertIsNone(limit_reason(steps=23, repeated_actions=2, elapsed_seconds=599.9))
        self.assertEqual(limit_reason(steps=24, repeated_actions=3, elapsed_seconds=600), 'step_limit')
        self.assertEqual(limit_reason(steps=0, repeated_actions=3, elapsed_seconds=600), 'repeated_actions')
        self.assertEqual(limit_reason(steps=0, repeated_actions=0, elapsed_seconds=600), 'deadline')
        self.assertEqual(limit_reason(steps=2, repeated_actions=0, elapsed_seconds=0,
                                      policy={'maxSteps': 2}), 'step_limit')

    def test_invalid_counters_are_not_treated_as_zero(self):
        for field in ('steps', 'repeated_actions'):
            for value in (-1, True, '1', 1.5, None):
                args = dict(steps=0, repeated_actions=0, elapsed_seconds=0)
                args[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    limit_reason(**args)
        for value in (-1, True, '1', None, math.inf, -math.inf, math.nan):
            with self.subTest(value=value), self.assertRaises(ValueError):
                limit_reason(steps=0, repeated_actions=0, elapsed_seconds=value)

    def test_implementation_and_loop_transfer_once(self):
        for reason in ('implementation_error', 'step_limit', 'repeated_actions', 'deadline'):
            with self.subTest(reason=reason):
                self.assertEqual(next_action('executor', reason, fixer_enabled=True), 'bug_fixer')
                self.assertEqual(next_action('executor', reason, fixer_enabled=False), 'stop')
                self.assertEqual(next_action('executor', reason, fixer_enabled=True, fixer_attempts=1), 'stop')
                self.assertEqual(next_action('bug_fixer', reason, fixer_enabled=True), 'stop')

    def test_infrastructure_and_user_stop_never_escalate(self):
        for role in ('executor', 'bug_fixer'):
            for reason in ('api_error', 'rate_limit', 'setup_error'):
                with self.subTest(role=role, reason=reason):
                    self.assertEqual(next_action(role, reason, fixer_enabled=True), 'blocked')
            for reason in ('paused', 'cancelled'):
                with self.subTest(role=role, reason=reason):
                    self.assertEqual(next_action(role, reason, fixer_enabled=True), 'stop')

    def test_selected_fixer_budget_allows_same_role_corrections_only_until_limit(self):
        self.assertEqual(next_action('bug_fixer', 'implementation_error', fixer_enabled=True,
                                    fixer_attempts=5, max_fixer_attempts=6), 'bug_fixer')
        self.assertEqual(next_action('bug_fixer', 'implementation_error', fixer_enabled=True,
                                    fixer_attempts=6, max_fixer_attempts=6), 'stop')

    def test_resume_and_infrastructure_history_do_not_leak_into_new_role_budgets(self):
        from kit.execution_policy import attempt_counts
        events = [dict(kind='delegation', event_id='a', work_item='one', workspace='a', role='executor'),
                  dict(kind='attempt_end', delegation_id='a', reason='rate_limit'),
                  dict(kind='review', delegation_id='a', result='rework')]
        self.assertEqual(attempt_counts(events, 'one'), {'executor': 0, 'bug_fixer': 0})
        events[1]['reason'] = 'deadline'
        self.assertEqual(attempt_counts(events, 'one')['executor'], 1)
        self.assertEqual(attempt_counts(events, 'other')['executor'], 0)
        self.assertEqual(attempt_counts(events + [{'kind': 'resume'}], 'one')['executor'], 0)

    def test_route_validates_even_when_no_transfer_possible(self):
        for role in ('', 'master_chief', None):
            with self.subTest(role=role), self.assertRaises(ValueError):
                next_action(role, 'cancelled', fixer_enabled=True)
        for reason in ('', 'unknown', None):
            with self.subTest(reason=reason), self.assertRaises(ValueError):
                next_action('executor', reason, fixer_enabled=True)
        for value in (0, 1, 'yes', None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                next_action('executor', 'cancelled', fixer_enabled=value)
        for value in (-1, True, 1.0, '0', None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                next_action('executor', 'rate_limit', fixer_enabled=True, fixer_attempts=value)


if __name__ == '__main__':
    unittest.main()
