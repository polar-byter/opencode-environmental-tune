"""Tests for kit/dashboard/sessions.py. The OpenCode CLI is replaced by a fake collector."""
from pathlib import Path
import unittest

from kit.dashboard import sessions


def row(group, **values):
    base = dict(provider='p', model='m', group=group, messages=1, missing_usage=0,
                input=10, output=5, reasoning=2, cache_read=1, cache_write=0)
    base.update(values)
    return base


def assistant(created, completed, text='work', provider='openai', model='gpt-6.1-sol'):
    return {'id': f'm{created}', 'type': 'assistant', 'agent': 'build',
            'model': {'providerID': provider, 'id': model},
            'time': {'created': created, 'completed': completed},
            'tokens': {'input': 10, 'output': 5, 'reasoning': 0, 'cache': {'read': 0, 'write': 0}},
            'content': [{'type': 'text', 'text': text}]}


class Step5Totals(unittest.TestCase):
    def test_group_totals(self):
        usage = {'models': [row('paid'), row('paid', input=None), row('free', output=7)]}
        totals = sessions.group_totals(usage)
        self.assertEqual(set(totals), set(sessions.GROUPS))
        self.assertIsNone(totals['paid']['input'])
        self.assertEqual(totals['paid']['output'], 10)
        self.assertEqual(totals['free']['output'], 7)
        self.assertEqual(totals['local'], dict.fromkeys(sessions.TOKEN_FIELDS, 0))

    def test_roles(self):
        exports = [{'info': {'id': 'ses_root'}}, {'info': {'id': 'ses_child'}}]
        self.assertEqual(sessions.session_roles(exports, 'ses_root'),
                         {'ses_root': 'master_chief', 'ses_child': 'executor'})


class Step5Cache(unittest.TestCase):
    def test_cache_ttl_and_errors(self):
        now = [0.0]
        calls = []

        def collect(root, session):
            calls.append(session)
            if session == 'ses_bad':
                raise ValueError('cli failed')
            return [{'info': {'id': session}}]

        cache = sessions.SessionCache(clock=lambda: now[0], collect=collect)
        cache.fetch(Path('.'), 'ses_a')
        now[0] = sessions.CACHE_SECONDS - 1
        cache.fetch(Path('.'), 'ses_a')
        self.assertEqual(calls, ['ses_a'])
        now[0] = sessions.CACHE_SECONDS + 1
        cache.fetch(Path('.'), 'ses_a')
        self.assertEqual(calls, ['ses_a', 'ses_a'])
        for _ in range(2):
            with self.assertRaises(ValueError):
                cache.fetch(Path('.'), 'ses_bad')
        self.assertEqual(calls.count('ses_bad'), 2)


class Step5TaskSessions(unittest.TestCase):
    def test_without_session(self):
        events = [{'kind': 'start', 'at': 1, 'session': None}]
        result = sessions.task_sessions(sessions.SessionCache(collect=None), Path('.'), events, 10)
        self.assertEqual(result['available'], False)

    def test_usage_feed_and_now(self):
        root_export = {'info': {'id': 'ses_root'}, 'messages': [assistant(1500, 1600, 'planning')]}
        child = {'info': {'id': 'ses_child', 'parentID': 'ses_root'},
                 'messages': [assistant(1700, None, 'coding', 'opencode-go', 'mimo-v2.6-pro')]}
        cache = sessions.SessionCache(collect=lambda root, session: [root_export, child])
        events = [{'kind': 'start', 'at': 1, 'session': 'ses_root'}]
        result = sessions.task_sessions(cache, Path('.'), events, now=10)
        self.assertTrue(result['available'])
        self.assertEqual(result['groups']['paid']['input'], 10)
        self.assertEqual([r['role'] for r in result['feed']], ['master_chief', 'executor'])
        self.assertEqual(list(result['now']), ['ses_child'])

    def test_errors_become_unavailable(self):
        def broken(root, session):
            raise ValueError('OpenCode session.list failed')
        events = [{'kind': 'start', 'at': 1, 'session': 'ses_root'}]
        result = sessions.task_sessions(sessions.SessionCache(collect=broken), Path('.'), events, now=10)
        self.assertEqual(result, {'available': False, 'reason': 'OpenCode session.list failed'})


if __name__ == '__main__':
    unittest.main()
