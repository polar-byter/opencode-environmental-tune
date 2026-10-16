"""Quota pauses and explicit live model changes preserve one task and its history."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from kit.provider_limits import quota_error
from kit import model_switch, run_opencode, task_control_state as state
from kit.task_metrics import TaskMetrics
from kit.execution_controller import ExecutionController
from kit.dashboard.controls import TaskControls
from kit.dashboard.quota_monitor import QuotaMonitor
from kit.dashboard.observations import observations
from kit.dashboard.session_control import SessionControl, ControlError
from kit.dashboard.tests import test_controls as control_tests


class QuotaClassification(unittest.TestCase):
    def test_structured_and_public_limit_errors(self):
        for error in ({'status':429}, {'type':'provider.quota'}, {'name':'FreeUsageLimitError'},
                      {'message':'Rate limit exceeded. Please try again later.'},
                      {'message':'Daily quota exhausted'}, {'message':'insufficient_quota'}):
            self.assertTrue(quota_error(error), error)
        for error in (None, '429', {'status':True}, {'status':401}, {'message':'Context token limit exceeded'},
                      {'message':'Permission denied'}, {'payload':'private 429'}):
            self.assertFalse(quota_error(error), error)

    def test_only_latest_assistant_error_is_exposed_without_private_payload(self):
        failed={'id':'msg_failed','type':'assistant','time':{'created':110000,'completed':111000},
                'model':{'providerID':'p','id':'m'},'error':{'type':'provider.quota','message':'429 private-key'},
                'content':[{'type':'reasoning','text':'private-thought'}]}
        export={'info':{'id':'ses_root'},'messages':[failed]}
        view=observations([export],'ses_root',100,200)
        self.assertEqual(view['quota_errors'][0]['message'],'msg_failed')
        self.assertNotIn('private-key',str(view)); self.assertNotIn('private-thought',str(view))
        export['messages'].append(dict(failed,id='msg_new',time={'created':120000},error=None,content=[]))
        self.assertEqual(observations([export],'ses_root',100,200)['quota_errors'],[])


class AutomaticPause(unittest.TestCase):
    setUp=control_tests.Controls.setUp

    def wait(self):
        with self.controls._lock:
            worker=self.controls._workers.get('task')
        if worker: worker.join(timeout=2)
        return self.controls.view('task')

    def signal(self):
        return {'session':'ses_root','message':'msg_quota','at':time.time(),'model':'p/m'}

    def test_limit_pauses_root_and_children_clears_queue_and_does_not_retry(self):
        signal=self.signal()
        self.controls.pause_for_limit('task',signal)
        value=self.wait()
        self.assertEqual(value['status'],'paused')
        self.assertEqual(value['reason'],'provider_limit')
        self.assertEqual(set(self.gateway.cleared),set(self.gateway.ids))
        self.assertEqual(self.gateway.prompts,[])
        count=len(self.gateway.interrupted)
        self.controls.pause_for_limit('task',signal)
        self.assertEqual(len(self.gateway.interrupted),count)

    def test_resume_ignores_old_failure_and_never_changes_journal(self):
        before=self.metrics.read('task')
        signal=self.signal()
        self.controls.pause_for_limit('task',signal); self.wait()
        self.controls.request('task','resume'); self.wait()
        self.assertEqual(self.controls.pause_for_limit('task',signal)['status'],'running')
        self.assertEqual(self.metrics.read('task'),before)
        self.assertEqual(len(self.gateway.prompts),1)

    def test_foreign_session_observation_is_rejected(self):
        signal=dict(self.signal(),session='ses_other')
        with self.assertRaises(ValueError): self.controls.pause_for_limit('task',signal)
        self.assertEqual(self.gateway.interrupted,[])

    def test_new_fast_quota_error_after_resume_admission_is_not_ignored(self):
        self.controls.pause_for_limit('task',self.signal()); self.wait()
        admitted=[]
        self.gateway.resume=lambda *args:admitted.append(time.time())
        self.controls.request('task','resume'); self.wait()
        signal=dict(self.signal(),at=admitted[0],message='msg_new_quota')
        self.controls.pause_for_limit('task',signal)
        self.assertEqual(self.wait()['status'],'paused')

    def test_monitor_works_without_http_and_observation_failure_is_not_a_pause(self):
        reader=Mock(); reader.view.return_value={'available':False,'quota_errors':[self.signal()]}
        monitor=QuotaMonitor(self.root,reader,self.controls)
        monitor.tick()
        self.assertEqual(self.gateway.interrupted,[])
        reader.view.return_value={'available':True,'quota_errors':[self.signal()]}
        monitor.tick()
        self.assertEqual(self.wait()['status'],'paused')


class ModelRevisions(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve(); (self.root/'.opencode').mkdir()
        config={'model':'p/chief','agents':{k:{'model':'p/worker'} for k in ('executor','executor-fast')}}
        config['agents']['build']={'model':'p/chief'}
        (self.root/'opencode.jsonc').write_text(json.dumps(config),encoding='utf-8')
        self.choices={'masterChief':{'source':'opencode','model':'p/chief'},
                      'executors':{'source':'opencode','model':'p/worker'},'execution':{'maxExecutors':2}}
        self.save()
        run_opencode.prepare(self.root)
        self.metrics=TaskMetrics(self.root); self.metrics.start('task','ses_root')
        self.controller=ExecutionController(self.root,'task',watcher=lambda x:None)
        self.controller.settings()
        self.frozen=(self.root/'.metrics/task/execution-settings.json').read_bytes()
        self.gateway=control_tests.Gateway(); self.gateway.active_ids.clear()
        self.gateway.prepare_models=Mock(); self.gateway.switch_model=Mock(); self.gateway.prepare_resume=Mock()
        self.controls=TaskControls(self.root,self.gateway)

    def save(self):
        (self.root/'.opencode/kit-models.json').write_text(json.dumps(self.choices),encoding='utf-8')

    def pause(self):
        state.write_state(self.root,'task',status='paused',session='ses_root',allow_execution=False)

    def test_running_task_blocks_preparation_before_overlay_changes(self):
        before=(self.root/'.opencode/opencode.jsonc').read_bytes()
        with self.assertRaisesRegex(ValueError,'pause'):run_opencode.prepare(self.root)
        self.assertEqual((self.root/'.opencode/opencode.jsonc').read_bytes(),before)

    def test_pause_draft_prepare_resume_uses_new_workers_without_rewriting_old_settings(self):
        self.pause()
        self.choices['masterChief']['model']='other/chief'
        self.choices['executors']['model']='other/worker'
        self.save()
        before=self.metrics.read('task')
        with patch('kit.dashboard.controls.TaskControls',return_value=self.controls):
            run_opencode.prepare(self.root)
        paused=state.read_state(self.root,'task')
        value=model_switch.verify_revision(self.root,'task',paused['settings_revision'])
        self.assertEqual(value['models']['masterChief'],'other/chief')
        self.assertEqual(paused['status'],'paused')
        self.controls.request('task','resume')
        with self.controls._lock:worker=self.controls._workers.get('task')
        if worker:worker.join(timeout=2)
        self.assertEqual(self.controller.settings()['executors']['model'],'other/worker')
        self.assertEqual((self.root/'.metrics/task/execution-settings.json').read_bytes(),self.frozen)
        self.assertEqual(self.metrics.read('task'),before)
        self.choices['executors']['model']='draft/not-applied'; self.save()
        self.assertEqual(self.controller.settings()['executors']['model'],'other/worker')

    def test_claimed_pause_with_active_session_is_rejected(self):
        self.pause(); self.gateway.active_ids.add('ses_root')
        with patch('kit.dashboard.controls.TaskControls',return_value=self.controls),self.assertRaisesRegex(ValueError,'still active'):
            run_opencode.prepare(self.root)
        self.gateway.switch_model.assert_not_called()

    def test_failed_live_preparation_keeps_pause_and_creates_no_revision(self):
        self.pause(); self.gateway.prepare_models.side_effect=ControlError('API unavailable')
        with patch('kit.dashboard.controls.TaskControls',return_value=self.controls),self.assertRaises(ControlError):
            run_opencode.prepare(self.root)
        self.assertEqual(state.read_state(self.root,'task')['status'],'paused')
        self.assertNotIn('settings_revision',state.read_state(self.root,'task'))

    def test_unsaved_preparation_mismatch_blocks_resume_before_a_prompt(self):
        self.pause()
        with patch('kit.dashboard.controls.TaskControls',return_value=self.controls):run_opencode.prepare(self.root)
        current=state.read_state(self.root,'task')
        self.choices['executors']['model']='p/not-prepared'; self.save()
        with self.assertRaisesRegex(ValueError,'Prepare'):model_switch.verify_revision(self.root,'task',current['settings_revision'])

    def test_concurrent_draft_save_does_not_become_a_prepared_revision(self):
        self.pause()
        with patch('kit.dashboard.controls.TaskControls',return_value=self.controls):
            with self.assertRaisesRegex(ValueError,'Prepare'):
                with model_switch.preparation(self.root):
                    self.choices['executors']['model']='p/concurrent-draft'; self.save()
        self.assertNotIn('settings_revision',state.read_state(self.root,'task'))
        self.gateway.switch_model.assert_not_called()

    def test_resume_preparation_error_keeps_pause_without_admitting_a_prompt(self):
        self.pause()
        with patch('kit.dashboard.controls.TaskControls',return_value=self.controls):run_opencode.prepare(self.root)
        self.gateway.prepare_resume.side_effect=ControlError('Selected model unavailable')
        self.controls.request('task','resume')
        with self.controls._lock:worker=self.controls._workers.get('task')
        if worker:worker.join(timeout=2)
        self.assertEqual(state.read_state(self.root,'task')['status'],'paused')
        self.assertEqual(self.gateway.prompts,[])


class NativeModelChange(unittest.TestCase):
    def test_switch_verifies_durable_session_model(self):
        service=SessionControl(Path.cwd())
        selected={'providerID':'openrouter','id':'p/m:free'}
        with patch.object(service,'call',side_effect=[None,{'data':{'model':selected}}]) as call:
            service.switch_model('ses_root','openrouter/p/m:free')
        self.assertEqual(call.call_args_list[0].args[0],'session.switchModel')
        with patch.object(service,'call',side_effect=[None,{'data':{'model':dict(selected,variant='default')}}]):
            service.switch_model('ses_root','openrouter/p/m:free')
        with patch.object(service,'call',side_effect=[None,{'data':{'model':dict(selected,variant='high')}}]):
            with self.assertRaises(ControlError):service.switch_model('ses_root','openrouter/p/m:free')
        with patch.object(service,'call',side_effect=[None,{'data':{'model':{'id':'old'}}}]):
            with self.assertRaises(ControlError):service.switch_model('ses_root','openrouter/p/m:free')
