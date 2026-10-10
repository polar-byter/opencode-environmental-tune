"""Tests for kit/dashboard/activity.py on exports shaped like OpenCode 2.0.26."""
import unittest

from kit.dashboard import activity


def tool(name, status='completed', created=1000, **inp):
    return {'type': 'tool', 'name': name, 'state': {'status': status, 'input': inp},
            'time': {'created': created}}


def message(parts, created=1000, completed=2000, mtype='assistant', agent='build'):
    stamp = {'created': created}
    if completed is not None:
        stamp['completed'] = completed
    return {'id': f'msg_{created}', 'type': mtype, 'agent': agent,
            'model': {'providerID': 'openai', 'id': 'gpt-6.1-sol'}, 'time': stamp, 'content': parts}


def export(messages, sid='ses_root'):
    return {'info': {'id': sid}, 'messages': messages}


class Step2Text(unittest.TestCase):
    def test_shorten(self):
        self.assertEqual(activity.shorten('  a \n\t b  '), 'a b')
        cut = activity.shorten('x' * 200, 10)
        self.assertEqual((cut, len(cut)), ('x' * 9 + '…', 10))
        self.assertEqual(activity.shorten('x' * 10, 10), 'x' * 10)

    def test_tool_target(self):
        self.assertEqual(activity.tool_target(tool('read', path='TASK.md', command='ignored')), 'TASK.md')
        self.assertEqual(activity.tool_target(tool('bash', command='mvn  -q\ntest')), 'mvn -q test')
        self.assertEqual(activity.tool_target(tool('task', path='', description='Implement Game')), 'Implement Game')
        self.assertEqual(activity.tool_target({'type': 'tool', 'name': 'x'}), '')
        self.assertEqual(activity.tool_target({'type': 'tool', 'state': {'input': 'oops'}}), '')


class Step2Feed(unittest.TestCase):
    def test_items(self):
        data = export([
            {'type': 'user', 'content': [{'type': 'text', 'text': 'hello'}], 'time': {'created': 500}},
            message([{'type': 'reasoning', 'text': 'secret thoughts'},
                     {'type': 'text', 'text': '  '},
                     {'type': 'text', 'text': 'Reading the task'},
                     tool('read', created=1500, path='TASK.md'),
                     {'type': 'step-finish'}], created=1000)])
        rows = activity.feed_items(data, 'master_chief')
        self.assertEqual([r['kind'] for r in rows], ['text', 'tool'])
        text, call = rows
        self.assertEqual((text['text'], text['at'], text['role']), ('Reading the task', 1.0, 'master_chief'))
        self.assertEqual((call['tool'], call['target'], call['status'], call['at']), ('read', 'TASK.md', 'completed', 1.5))
        self.assertEqual((call['session'], call['agent'], call['model']), ('ses_root', 'build', 'openai/gpt-6.1-sol'))
        self.assertNotIn('secret', str(rows))

    def test_unknown_model(self):
        msg = message([{'type': 'text', 'text': 'hi'}])
        del msg['model']
        self.assertEqual(activity.feed_items(export([msg]), 'executor')[0]['model'], 'unknown')

    def test_merge(self):
        a = [{'at': 1, 'n': 'a1'}, {'at': 3, 'n': 'a3'}]
        b = [{'at': 2, 'n': 'b2'}, {'at': 3, 'n': 'b3'}]
        self.assertEqual([r['n'] for r in activity.merge_feeds([a, b])], ['a1', 'b2', 'a3', 'b3'])
        self.assertEqual([r['n'] for r in activity.merge_feeds([a, b], limit=2)], ['a3', 'b3'])


class Step2Now(unittest.TestCase):
    def test_idle_and_busy(self):
        self.assertIsNone(activity.current_step(export([])))
        self.assertIsNone(activity.current_step(export([message([tool('read')])])))
        busy = export([message([tool('read'), tool('bash', status='running', created=3000, command='mvn test')],
                               created=2500, completed=None)])
        self.assertEqual(activity.current_step(busy), {'tool': 'bash', 'target': 'mvn test', 'since': 3.0})
        thinking = export([message([{'type': 'text', 'text': '...'}], created=4000, completed=None)])
        self.assertEqual(activity.current_step(thinking), {'tool': None, 'target': '', 'since': 4.0})


if __name__ == '__main__':
    unittest.main()
