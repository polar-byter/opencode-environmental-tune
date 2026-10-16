"""Control the shared OpenCode Desktop service through its installed v2 CLI."""
import json
import hashlib
import os
from pathlib import Path
import subprocess

from ..opencode_cli import locate_opencode
from ..task_metrics import session_id


class ControlError(RuntimeError):
    pass


class SessionControl:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    def call(self, operation, params=None, data=None):
        executable = locate_opencode()
        if not executable:
            raise ControlError('OpenCode CLI не найден')
        args = [executable, 'api', operation]
        for key, value in (params or {}).items():
            args += ['--param', f'{key}={value}']
        if data is not None:
            args += ['--data', json.dumps(data, ensure_ascii=False)]
        options = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
        try:
            result = subprocess.run(args, cwd=self.root, stdin=subprocess.DEVNULL, capture_output=True,
                                    text=True, encoding='utf-8', errors='replace', timeout=20, **options)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ControlError('OpenCode не ответил вовремя; результат действия не подтверждён') from error
        if result.returncode:
            # Provider/CLI output can contain credentials; never forward it to a browser.
            raise ControlError(f'OpenCode: не выполнено действие {operation}; состояние не подтверждено')
        if not result.stdout.strip():
            return None
        try:
            return json.loads(result.stdout.lstrip('\ufeff'))
        except ValueError as error:
            raise ControlError('OpenCode вернул неизвестный формат ответа') from error

    def capabilities(self):
        spec = self.openapi()
        operations = {item.get('operationId') for path in spec.get('paths', {}).values()
                      for item in path.values() if isinstance(item, dict)}
        if not {'session.list', 'session.active', 'session.interrupt', 'session.prompt',
                'session.inbox.list', 'session.inbox.cancel', 'session.remove'} <= operations:
            raise ControlError('Эта версия OpenCode не поддерживает управление задачами')
        schemas = spec.get('components', {}).get('schemas', {})
        if schemas.get('SessionInterruptResponse', {}).get('properties', {}).get('interrupted', {}).get('type') != 'boolean':
            raise ControlError('Неизвестный протокол управления OpenCode')

    def openapi(self):
        # Raw path is needed because the document itself has no operation ID.
        executable = locate_opencode()
        if not executable:
            raise ControlError('OpenCode CLI не найден')
        options = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
        try:
            result = subprocess.run([executable, 'api', 'GET', '/openapi.json'], cwd=self.root,
                                    stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                    encoding='utf-8', errors='replace', timeout=20, **options)
            if result.returncode:
                raise ValueError()
            value = json.loads(result.stdout.lstrip('\ufeff'))
            if not isinstance(value, dict):
                raise ValueError()
            return value
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            raise ControlError('Не удалось проверить API общего сервера OpenCode Desktop') from error

    def sessions(self, parent=None):
        params = {'directory': str(self.root), 'parentID': 'null' if parent is None else session_id(parent), 'limit': '100'}
        rows, cursors = [], set()
        for _ in range(30):
            result = self.call('session.list', params)
            if not isinstance(result, dict) or not isinstance(result.get('data'), list):
                raise ControlError('Неизвестный список сессий OpenCode')
            for row in result['data']:
                if not isinstance(row, dict):
                    raise ControlError('Некорректная сессия OpenCode')
                session_id(row.get('id'))
                directory = row.get('location', {}).get('directory')
                if not isinstance(directory, str) or Path(directory).resolve() != self.root:
                    raise ControlError('Сессия принадлежит другой папке проекта')
                if row.get('parentID') != parent:
                    raise ControlError('Не подтверждена связь дочерней сессии')
                rows.append(row)
            cursor = result.get('cursor', {}).get('next')
            if not cursor:
                return rows
            if not isinstance(cursor, str) or cursor in cursors:
                raise ControlError('Повтор страницы сессий OpenCode')
            cursors.add(cursor)
            params['cursor'] = cursor
        raise ControlError('Слишком много страниц сессий; остановка не подтверждена')

    def tree(self, root_session):
        root_session = session_id(root_session)
        roots = self.sessions()
        if not any(row['id'] == root_session for row in roots):
            raise ControlError('Основная сессия не найдена в этом проекте на общем сервере Desktop')
        found = [root_session]
        for sid in found:
            for row in self.sessions(sid):
                if row['id'] in found or len(found) >= 200:
                    raise ControlError('Некорректное или слишком большое дерево сессий')
                found.append(row['id'])
        return found

    def active(self):
        response = self.call('session.active')
        if not isinstance(response, dict) or not isinstance(response.get('data'), dict):
            raise ControlError('Активность сессий не подтверждена')
        for sid, item in response['data'].items():
            session_id(sid)
            if item != {'type': 'running'}:
                raise ControlError('Неизвестное состояние активности сессии')
        return set(response['data'])

    def interrupt(self, sid):
        result = self.call('session.interrupt', {'sessionID': session_id(sid), 'resume': 'false'})
        if not isinstance(result, dict) or type(result.get('interrupted')) is not bool:
            raise ControlError('Прерывание сессии не подтверждено')

    def clear_inbox(self, sid):
        for _ in range(3):
            result = self.call('session.inbox.list', {'sessionID': session_id(sid)})
            if not isinstance(result, dict) or not isinstance(result.get('data'), list):
                raise ControlError('Очередь сессии не прочитана')
            if not result['data']:
                return
            for item in result['data']:
                if not isinstance(item, dict) or not isinstance(item.get('id'), str) or not item['id'].startswith('msg_'):
                    raise ControlError('Некорректный идентификатор сообщения очереди')
                self.call('session.inbox.cancel', {'sessionID': sid, 'inboxID': item['id']})
        raise ControlError('Очередь сессии не удалось очистить')

    def prepare_resume(self, sid, task):
        from ..task_control_state import read_state
        reference = read_state(self.root, task).get('settings_revision')
        if reference:
            from ..model_switch import verify_revision
            selected = verify_revision(self.root, task, reference)
            self.prepare_models(selected['choices'], selected['models'])
            self.switch_model(sid, selected['models']['masterChief'])

    def resume(self, sid, task, operation_id):
        text = (f'User resumed the paused task {task} from its dashboard. Continue this same task ID. '
                'Read the saved work plan and task journal. Inspect partial edits and interrupted executor attempts '
                'before continuing; do not assume an interrupted attempt passed review or tests. '
                'Do not reset loop guards or start a new task. Continue the next unfinished approved work item.')
        result = self.call('session.prompt', {'sessionID': session_id(sid)},
                           {'id': 'msg_' + operation_id, 'text': text, 'delivery': 'steer', 'resume': True})
        if not isinstance(result, dict) or not isinstance(result.get('data'), dict) or result['data'].get('id') != 'msg_' + operation_id:
            raise ControlError('Продолжение не подтверждено; проверьте сессию перед повторной попыткой')

    def prepare_models(self, choices, selected):
        """Verify live provider registration; credentials never enter task journals."""
        import time
        from ..configurator.workflow import existing_key
        wanted = {value.split('#', 1)[0] for value in selected.values()}
        for _ in range(15):
            rows = self.call('model.list').get('data', [])
            found = {row['providerID'] + '/' + row['id'] for row in rows if isinstance(row, dict)}
            if wanted <= found:
                break
            time.sleep(.2)
        else:
            raise ControlError('Selected models are not available in the running OpenCode service. The task remains paused.')
        for field, provider in (('masterChief', 'kit-master-chief-api'), ('executors', 'kit-executor-api'), ('bugFixer', 'kit-bug-fixer-api')):
            choice = choices.get(field)
            if not choice or choice['source'] != 'api':
                continue
            key = existing_key(choice['keyEnv'])
            if not key:
                raise ControlError('An API key is missing. Save it in Model settings and prepare again.')
            integrations = self.call('integration.list').get('data', [])
            if not any(isinstance(item, dict) and item.get('id') == provider for item in integrations):
                raise ControlError('The selected API integration is unavailable. The task remains paused.')
            # Native credential storage refreshes the service without restarting Desktop.
            identifier = 'cred_' + hashlib.sha256((str(self.root) + provider + key).encode()).hexdigest()[:24]
            credentials = self.call('credential.list').get('data', [])
            if any(isinstance(item, dict) and item.get('id') == identifier and item.get('integrationID') == provider for item in credentials):
                self.call('credential.activate', {'credentialID': identifier})
            else:
                self.call('credential.create', data={'id': identifier, 'integrationID': provider, 'label': 'OpenCode Kit',
                           'value': {'type': 'key', 'key': key}, 'activate': True})

    def switch_model(self, sid, reference):
        provider, model = reference.split('/', 1)
        selection = {'providerID': provider, 'id': model}
        if '#' in model:
            selection['id'], selection['variant'] = model.rsplit('#', 1)
        self.call('session.switchModel', {'sessionID': session_id(sid)}, {'model': selection})
        actual = self.call('session.get', {'sessionID': sid}).get('data', {}).get('model')
        if isinstance(actual, dict) and 'variant' not in selection and actual.get('variant') in (None, 'default'):
            actual = {key: value for key, value in actual.items() if key != 'variant'}
        if actual != selection:
            raise ControlError('OpenCode did not confirm the selected model. The task remains paused.')

    def remove(self, sid):
        self.call('session.remove', {'sessionID': session_id(sid)})
