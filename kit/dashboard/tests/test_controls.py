"""Task controls: descendants, durable gating, failures and source preservation."""
import http.client
import json
import os
from pathlib import Path
import subprocess
import shutil
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from kit import task_control_state as state
from kit.dashboard.controls import TaskControls
from kit.dashboard.session_control import ControlError, SessionControl
from kit.dashboard.runtime import task_view
from kit.dashboard.tests import test_runtime
from kit.dashboard.tests.test_simple_page import InlineScripts
from kit.task_metrics import TaskHalted, TaskMetrics


class Gateway:
    def __init__(self):
        self.ids = ['ses_root', 'ses_child', 'ses_grandchild']
        self.active_ids = set(self.ids)
        self.interrupted, self.cleared, self.prompts, self.removed = [], [], [], []

    def capabilities(self):
        pass

    def tree(self, sid):
        if sid not in self.ids:
            raise ControlError('Сессия не найдена')
        return self.ids[:]

    def active(self):
        return self.active_ids.copy()

    def interrupt(self, sid):
        self.interrupted.append(sid)
        self.active_ids.discard(sid)

    def clear_inbox(self, sid):
        self.cleared.append(sid)

    def resume(self, *args):
        self.prompts.append(args)

    def remove(self, sid):
        self.removed.append(sid)
        self.ids.clear()

    def sessions(self):
        return [{'id': self.ids[0]}] if self.ids else []


class Controls(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(); self.addCleanup(folder.cleanup)
        self.root = Path(folder.name).resolve()
        self.metrics = TaskMetrics(self.root)
        self.metrics.start('task', session='ses_root')
        self.gateway = Gateway()
        self.controls = TaskControls(self.root, self.gateway)

    def perform(self, action):
        self.controls.request('task', action)
        with self.controls._lock:
            worker = self.controls._workers.get('task')
        if worker:
            worker.join(4)
            self.assertFalse(worker.is_alive())
        return self.controls.view('task')

    def test_pause_stops_entire_tree_preserves_queue_and_gates_metrics(self):
        result = self.perform('pause')
        self.assertEqual(result['status'], 'paused')
        self.assertEqual(set(self.gateway.interrupted), set(self.gateway.ids))
        self.assertFalse(self.gateway.active_ids)
        self.assertFalse(self.gateway.cleared)
        self.assertEqual(len(self.metrics.read('task')), 1)
        with self.assertRaises(TaskHalted): self.metrics.running('task')
        with self.assertRaises(TaskHalted): self.metrics.finish('task')
        self.assertTrue(self.metrics.task_dir('task').exists())

    def test_resume_uses_same_session_and_task_once_and_preserves_journal(self):
        self.perform('pause'); before = self.metrics.read('task')
        result = self.perform('resume')
        self.assertEqual(result['status'], 'running')
        self.assertEqual(self.gateway.prompts[0][:2], ('ses_root', 'task'))
        self.assertEqual(self.metrics.running('task'), before)
        self.perform('resume')
        self.assertEqual(len(self.gateway.prompts), 1)

    def test_pause_cannot_clear_protective_halt(self):
        self.metrics.append('task', 'halt', reason='test guard')
        self.perform('pause')
        with self.assertRaisesRegex(ValueError, 'лимит'): self.controls.request('task', 'resume')
        self.assertEqual(self.metrics.read('task')[-1]['kind'], 'halt')

    def test_cancel_clears_all_queues_and_has_no_success_finish(self):
        result = self.perform('cancel')
        self.assertEqual(result['status'], 'cancelled')
        self.assertEqual(set(self.gateway.cleared), set(self.gateway.ids))
        self.assertFalse(any(e['kind'] == 'finish' for e in self.metrics.read('task')))
        with self.assertRaises(TaskHalted): self.metrics.running('task')
        with self.assertRaises(ValueError): self.controls.request('task', 'resume')

    def test_delete_preserves_source_and_unrelated_task(self):
        (self.root / 'app.py').write_text('source', encoding='utf-8')
        self.metrics.start('other', session='ses_other')
        result = self.perform('delete')
        self.assertEqual(result['status'], 'deleted')
        self.assertEqual(self.gateway.removed, ['ses_root'])
        self.assertFalse(self.metrics.task_dir('task').exists())
        self.assertTrue(self.metrics.task_dir('other').exists())
        self.assertEqual((self.root / 'app.py').read_text(), 'source')
        self.assertEqual(self.perform('delete')['status'], 'deleted')
        self.assertEqual(len(self.gateway.removed), 1)

    def test_shared_session_and_missing_session_cannot_be_controlled(self):
        self.metrics.start('other', session='ses_root')
        for action in ('pause', 'cancel', 'delete'):
            with self.assertRaisesRegex(ValueError, 'другой задачей'): self.controls.request('task', action)
        self.assertFalse(self.gateway.interrupted)
        self.metrics.start('no-session')
        with self.assertRaises(ValueError): self.controls.request('no-session', 'pause')

    def test_finished_without_session_can_delete_metrics_only(self):
        self.metrics.start('offline'); self.metrics.finish('offline')
        result = self.controls.request('offline', 'delete')
        worker = self.controls._workers.get('offline')
        if worker: worker.join(4)
        self.assertEqual(self.controls.view('offline')['status'], 'deleted')
        self.assertFalse(self.gateway.removed)

    def test_failure_keeps_task_blocked_and_does_not_claim_pause(self):
        self.gateway.interrupt = Mock(side_effect=ControlError('Unavailable'))
        result = self.perform('pause')
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['error'], 'Unavailable')
        with self.assertRaises(TaskHalted): self.metrics.running('task')
        self.assertFalse(self.gateway.removed)

    def test_still_active_refuses_delete_and_retry_can_complete(self):
        self.gateway.active = lambda: {'ses_grandchild'}
        self.assertEqual(self.perform('delete')['status'], 'error')
        self.assertTrue(self.metrics.task_dir('task').exists())
        self.assertFalse(self.gateway.removed)
        self.gateway.active = lambda: set()
        self.assertEqual(self.perform('delete')['status'], 'deleted')

    def test_new_child_during_stop_is_discovered(self):
        original = self.gateway.interrupt
        def interrupt(sid):
            if sid == 'ses_root' and 'ses_late' not in self.gateway.ids:
                self.gateway.ids.append('ses_late'); self.gateway.active_ids.add('ses_late')
            original(sid)
        self.gateway.interrupt = interrupt
        self.assertEqual(self.perform('pause')['status'], 'paused')
        self.assertIn('ses_late', self.gateway.interrupted)

    def test_duplicate_clicks_and_competing_actions(self):
        started, release = threading.Event(), threading.Event()
        def capabilities(): started.set(); release.wait(4)
        self.gateway.capabilities = capabilities
        first = self.controls.request('task', 'pause')
        self.assertTrue(started.wait(2))
        try:
            second = self.controls.request('task', 'pause')
            self.assertEqual(first['operation_id'], second['operation_id'])
            with self.assertRaises(ValueError): self.controls.request('task', 'cancel')
            other = TaskControls(self.root, self.gateway)
            self.assertEqual(other.view('task')['status'], 'pausing')
            with self.assertRaises(ValueError): other.request('task', 'cancel')
        finally:
            release.set()
            with self.controls._lock: worker = self.controls._workers.get('task')
            if worker: worker.join(4)

    def test_restart_marks_pending_operation_uncertain_without_resending(self):
        state.write_state(self.root, 'task', status='resuming', action='resume', allow_execution=True)
        other = TaskControls(self.root, self.gateway)
        self.assertEqual(other.view('task')['status'], 'error')
        self.assertFalse(self.gateway.prompts)
        with self.assertRaises(TaskHalted): self.metrics.running('task')

    def test_resume_failure_blocks_work_without_resetting_guard(self):
        self.perform('pause')
        self.gateway.resume = Mock(side_effect=ControlError('No confirmation'))
        self.assertEqual(self.perform('resume')['status'], 'error')
        with self.assertRaises(TaskHalted): self.metrics.running('task')
        self.assertEqual([e['kind'] for e in self.metrics.read('task')], ['start'])

    def test_crash_during_admission_blocks_metrics_before_dashboard_recovery(self):
        state.write_state(self.root, 'task', status='resuming', allow_execution=True)
        with self.assertRaises(TaskHalted): self.metrics.running('task')

    def test_known_private_server_is_not_controlled_through_shared_api(self):
        self.metrics.append('task', 'test', scope='work', status='passed')
        events = self.metrics.read('task'); events[0]['server_mode'] = 'standalone'
        (self.metrics.task_dir('task')/'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
        with self.assertRaisesRegex(ValueError, 'общий сервер'): self.controls.request('task', 'pause')
        self.assertFalse(self.gateway.interrupted)

    def test_delete_locked_journal_can_retry_after_native_tree_removed(self):
        lock = self.metrics.task_dir('task') / '.lock'; lock.write_text('busy')
        self.assertEqual(self.perform('delete')['status'], 'error')
        self.assertTrue(self.controls.view('task')['session_removed'])
        lock.unlink()
        self.assertEqual(self.perform('delete')['status'], 'deleted')
        self.assertEqual(self.gateway.removed, ['ses_root'])

    def test_traversal_and_redirected_state_are_rejected(self):
        for task in ('../app', '/app', 'CON'):
            with self.assertRaises(ValueError): self.controls.request(task, 'pause')
        path = state.state_path(self.root, 'task'); path.parent.mkdir()
        path.write_text('{')
        with self.assertRaises(ValueError): self.metrics.running('task')

    def test_redirected_child_prevents_recursive_delete(self):
        link = self.metrics.task_dir('task') / 'linked'
        target = self.root / 'app'; target.mkdir(); (target / 'keep').write_text('keep')
        try: link.symlink_to(target, target_is_directory=True)
        except OSError:
            # Windows without symlink privilege: exercise the same preflight path check.
            with patch('kit.dashboard.controls.state.plain_path', side_effect=ValueError('link')):
                with self.assertRaises(ValueError): self.controls.delete_metrics('task')
        else:
            with self.assertRaises(ValueError): self.controls.delete_metrics('task')
            link.unlink()
        self.assertTrue((target / 'keep').exists())


class NativeContract(unittest.TestCase):
    def setUp(self):
        self.root = Path.cwd().resolve(); self.gateway = SessionControl(self.root)

    def row(self, sid, parent=None):
        value = {'id': sid, 'location': {'directory': str(self.root)}}
        if parent: value['parentID'] = parent
        return value

    def test_tree_paginates_and_validates_parents_and_project(self):
        responses = [
            {'data': [self.row('ses_root')], 'cursor': {'next': 'next'}}, {'data': []},
            {'data': [self.row('ses_child', 'ses_root')]}, {'data': []}]
        with patch.object(self.gateway, 'call', side_effect=responses) as call:
            self.assertEqual(self.gateway.tree('ses_root'), ['ses_root', 'ses_child'])
            self.assertEqual(call.call_args_list[1].args[1]['cursor'], 'next')
        for row in (self.row('ses_bad', 'ses_wrong'), dict(self.row('ses_root'), location={'directory':str(self.root.parent)})):
            with patch.object(self.gateway, 'call', return_value={'data': [row]}):
                with self.assertRaises(ControlError): self.gateway.tree('ses_root')

    def test_missing_root_cycle_and_repeated_page_fail_closed(self):
        with patch.object(self.gateway, 'sessions', return_value=[]):
            with self.assertRaises(ControlError): self.gateway.tree('ses_absent')
        with patch.object(self.gateway, 'sessions', side_effect=[[self.row('ses_root')], [self.row('ses_root', 'ses_root')]]):
            with self.assertRaises(ControlError): self.gateway.tree('ses_root')
        with patch.object(self.gateway, 'call', return_value={'data': [], 'cursor': {'next':'same'}}):
            with self.assertRaises(ControlError): self.gateway.sessions()

    def test_interrupt_uses_query_false_and_checks_confirmation(self):
        with patch.object(self.gateway, 'call', return_value={'interrupted': False}) as call:
            self.gateway.interrupt('ses_root')
            self.assertEqual(call.call_args.args, ('session.interrupt', {'sessionID':'ses_root', 'resume':'false'}))
        with patch.object(self.gateway, 'call', return_value={}):
            with self.assertRaises(ControlError): self.gateway.interrupt('ses_root')

    def test_resume_uses_v2_text_in_same_session_with_stable_id(self):
        with patch.object(self.gateway, 'call', return_value={'data':{'id':'msg_operation'}}) as call:
            self.gateway.resume('ses_root', 'task', 'operation')
            self.assertEqual(call.call_args.args[1], {'sessionID':'ses_root'})
            body = call.call_args.args[2]
            self.assertTrue(body['resume']); self.assertEqual(body['delivery'], 'steer')
            self.assertIn('task', body['text']); self.assertNotIn('parts', body)

    def test_cancel_checks_queue_empty_and_unknown_active_fails_closed(self):
        with patch.object(self.gateway, 'call', side_effect=[{'data':[{'id':'msg_one'}]}, None, {'data':[]}]) as call:
            self.gateway.clear_inbox('ses_root')
            self.assertEqual(call.call_args_list[1].args[0], 'session.inbox.cancel')
        for response in ({}, {'data':{'ses_root':{'type':'unknown'}}}):
            with patch.object(self.gateway, 'call', return_value=response):
                with self.assertRaises(ControlError): self.gateway.active()

    def test_timeout_and_cli_errors_do_not_leak_output(self):
        with patch('kit.dashboard.session_control.locate_opencode', return_value='opencode'):
            for result in (Mock(returncode=1, stdout='secret-key', stderr='secret-key'), Mock(returncode=0, stdout='secret-key')):
                with patch('kit.dashboard.session_control.subprocess.run', return_value=result):
                    with self.assertRaises(ControlError) as caught: self.gateway.active()
                    self.assertNotIn('secret-key', str(caught.exception))
            with patch('kit.dashboard.session_control.subprocess.run', side_effect=subprocess.TimeoutExpired('opencode',20)):
                with self.assertRaises(ControlError): self.gateway.active()


class Resilience(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(); self.addCleanup(folder.cleanup)
        self.root=Path(folder.name).resolve(); TaskMetrics(self.root).start('task')
        self.reader = Mock(); self.reader.view.return_value = {'available':False}

    def test_model_display_does_not_require_api_key(self):
        folder=self.root/'.opencode';folder.mkdir()
        (folder/'kit-models.json').write_text(json.dumps({'executors':{'source':'api','model':'qwen/test','keyEnv':'MISSING_TEST_KEY','baseURL':'https://example.invalid/v1'}}))
        with patch.dict('os.environ', {}, clear=True): value=task_view(self.root,'task',self.reader)
        self.assertEqual(value['work']['configured_models']['executor'], 'qwen/test')
        self.assertNotIn('error',value['work'])

    def test_config_failure_preserves_items_architecture_and_progress(self):
        with patch('kit.dashboard.runtime.observations.display_models', side_effect=ValueError('secret')), \
             patch('kit.dashboard.runtime.tracking.work_items', return_value=[{'id':'item','attempts':[{'at':0}]}]), \
             patch('kit.dashboard.runtime.tracking.architecture', return_value={'document':'ARCHITECTURE.md','text':'body'}), \
             patch('kit.dashboard.runtime.tracking.function_progress', return_value={'available':True,'total':4}):
            value=task_view(self.root,'task',self.reader)
        self.assertEqual(value['work']['progress']['total'],4)
        self.assertEqual(value['work']['items'][0]['id'],'item')
        self.assertEqual(value['work']['architecture'],{'document':'ARCHITECTURE.md'})
        self.assertNotIn('secret',json.dumps(value))

    def test_session_failure_preserves_other_sources(self):
        self.reader.view.side_effect=ValueError('offline')
        value=task_view(self.root,'task',self.reader)
        self.assertEqual(value['event_count'],1)
        self.assertFalse(value['work']['sessions']['available'])
        self.assertIn('configured_models',value['work'])


class ControlHTTP(unittest.TestCase):
    setUp=test_runtime.RuntimeHTTP.setUp
    close=test_runtime.RuntimeHTTP.close

    def post(self, data, headers=None, raw=None, path='/api/task/control'):
        connection=http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=2)
        try:
            connection.request('POST',path,body=raw if raw is not None else json.dumps(data),headers=headers or {})
            response=connection.getresponse();return response.status,json.loads(response.read())
        finally:connection.close()

    def headers(self):
        return {'Content-Type':'application/json','Origin':f'http://127.0.0.1:{self.server.server_port}','X-Dashboard-UI-Token':self.server.ui_token}

    def test_mutations_require_both_origin_and_ui_token(self):
        with patch.object(self.server.controls,'request') as request:
            for headers in ({},dict(self.headers(),Origin='https://foreign'),dict(self.headers(),**{'X-Dashboard-UI-Token':self.server.control_token})):
                self.assertEqual(self.post({'task':'first','action':'pause'},headers)[0],403)
            request.assert_not_called()

    def test_valid_post_dispatches_only_task_and_action(self):
        with patch.object(self.server.controls,'request',return_value={'status':'pausing'}) as request:
            self.assertEqual(self.post({'task':'first','action':'pause'},self.headers())[0],202)
            request.assert_called_once_with('first','pause')

    def test_invalid_body_and_arbitrary_parameters_are_rejected(self):
        with patch.object(self.server.controls,'request') as request:
            for data in ({'task':'first','action':'pause','session':'ses_other'},[],{'task':1,'action':'pause'}):
                self.assertEqual(self.post(data,self.headers())[0],400)
            for raw in ('{','x'*1025):
                self.assertEqual(self.post(None,self.headers(),raw=raw)[0],400)
            self.assertEqual(self.post({'task':'first','action':'pause'},self.headers(),path='/api/task/control?root=other')[0],400)
            request.assert_not_called()
        for task,action in (('../app','delete'),('missing','pause'),('first','shell')):
            self.assertEqual(self.post({'task':task,'action':action},self.headers())[0],400)


class ControlPage(unittest.TestCase):
    def test_buttons_requests_errors_stale_selection_and_delete_cleanup(self):
        node=os.environ.get('DASHBOARD_TEST_NODE') or shutil.which('node')
        self.assertIsNotNone(node, 'Node is required for dashboard JavaScript checks')
        folder=Path(__file__).resolve().parent
        page=InlineScripts();page.feed((folder.parent/'static/runtime.html').read_text(encoding='utf-8'))
        result=subprocess.run([node,str(folder/'controls_page_checks.js')],
                              input=json.dumps({'source':''.join(page.parts),'ids':page.ids}),
                              text=True,encoding='utf-8',capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)


if __name__=='__main__':
    unittest.main()
