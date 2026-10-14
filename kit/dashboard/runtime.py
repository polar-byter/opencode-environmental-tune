"""Read-only operational dashboard for a project's registered metrics tasks."""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import sys
import threading
from urllib.parse import parse_qs, urlsplit
import uuid

from . import journal
from .launcher import SERVICE, VERSION, project_id, read_state, runtime_folder, write_state
from ..task_metrics import TaskMetrics

PAGE = Path(__file__).resolve().parent / 'static' / 'runtime.html'


def task_directory(root: Path, task: str) -> Path:
    directory = TaskMetrics(root).task_dir(task)
    if directory.resolve().parent != (root / '.metrics').resolve():
        raise ValueError('Task directory is outside the project journal folder')
    if not (directory / 'events.jsonl').is_file():
        raise FileNotFoundError('Task not found')
    if (directory / 'events.jsonl').resolve().parent != directory.resolve():
        raise ValueError('Journal is outside the task directory')
    return directory


def task_view(root: Path, task: str) -> dict:
    events = journal.read_events(task_directory(root, task) / 'events.jsonl')
    result = journal.brief_summary(events)
    result.update(task=task, started_at=events[0]['at'], session=events[0].get('session'))
    result['activity'] = [
        {key: event[key] for key in ('kind', 'at', 'work_item', 'result', 'scope', 'status', 'reason')
         if key in event}
        for event in events[-30:]
    ]
    return result


def task_list(root: Path) -> list[dict]:
    folder = root / '.metrics'
    if not folder.is_dir():
        return []
    rows = []
    for directory in folder.iterdir():
        if not directory.is_dir() or directory.name.startswith('.'):
            continue
        try:
            view = task_view(root, directory.name)
            rows.append({key: view[key] for key in ('task', 'title', 'status', 'started_at')})
        except (OSError, ValueError):
            continue
    return sorted(rows, key=lambda row: (row['started_at'], row['task']), reverse=True)


class DashboardServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, root: Path, port: int = 0, instance: str | None = None):
        self.root = Path(root).resolve()
        self.instance = instance or uuid.uuid4().hex
        self.control_token = secrets.token_urlsafe(32)
        super().__init__(('127.0.0.1', port), Handler)

    def state(self) -> dict:
        return {'service': SERVICE, 'version': VERSION, 'instance_id': self.instance,
                'pid': os.getpid(), 'project_root': str(self.root),
                'base_url': f'http://127.0.0.1:{self.server_port}',
                'control_token': self.control_token}

    def health(self) -> dict:
        result = self.state()
        del result['control_token']
        result['project'] = {'id': project_id(self.root), 'name': self.root.name}
        result['poll_interval_ms'] = 2000
        return result


class Handler(BaseHTTPRequestHandler):
    server: DashboardServer

    def log_request(self, code='-', size='-'):
        if str(code).isdigit() and int(code) >= 400:
            super().log_request(code, size)

    def host_allowed(self) -> bool:
        host = self.headers.get('Host', '').lower()
        return host in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}')

    def send_body(self, status: int, body: bytes, content_type='application/json; charset=utf-8'):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status: int, data: dict | list):
        self.send_body(status, json.dumps(data, ensure_ascii=False, allow_nan=False).encode('utf-8'))

    def selected_task(self, query: dict) -> str:
        values = query.get('task', [])
        if len(values) != 1 or not values[0]:
            raise ValueError('One task ID is required')
        project = query.get('project', [])
        if project and project != [project_id(self.server.root)]:
            raise ValueError('This server belongs to a different project')
        return values[0]

    def do_GET(self):
        if not self.host_allowed():
            self.send_json(403, {'error': 'Forbidden Host'})
            return
        parts = urlsplit(self.path)
        query = parse_qs(parts.query, keep_blank_values=True)
        try:
            if parts.path == '/':
                body = PAGE.read_bytes()
                status, content_type = 200, 'text/html; charset=utf-8'
            elif parts.path == '/api/health':
                body = json.dumps(self.server.health(), ensure_ascii=False).encode('utf-8')
                status, content_type = 200, 'application/json; charset=utf-8'
            elif parts.path == '/api/tasks':
                body = json.dumps(task_list(self.server.root), ensure_ascii=False).encode('utf-8')
                status, content_type = 200, 'application/json; charset=utf-8'
            elif parts.path == '/api/task':
                data = task_view(self.server.root, self.selected_task(query))
                body = json.dumps(data, ensure_ascii=False, allow_nan=False).encode('utf-8')
                status, content_type = 200, 'application/json; charset=utf-8'
            elif parts.path == '/api/report':
                folder = task_directory(self.server.root, self.selected_task(query))
                report = folder / 'report.md'
                if report.resolve().parent != folder.resolve():
                    raise ValueError('Report is outside the task directory')
                if report.stat().st_size > 2 * 1024 * 1024:
                    raise ValueError('Report exceeds 2 MiB')
                body = report.read_text(encoding='utf-8-sig').encode('utf-8')
                status, content_type = 200, 'text/plain; charset=utf-8'
            else:
                body = b'{"error":"Not found"}'
                status, content_type = 404, 'application/json; charset=utf-8'
        except FileNotFoundError as error:
            body = json.dumps({'error': str(error)}, ensure_ascii=False).encode('utf-8')
            status, content_type = 404, 'application/json; charset=utf-8'
        except ValueError as error:
            body = json.dumps({'error': str(error)}, ensure_ascii=False).encode('utf-8')
            status, content_type = 400, 'application/json; charset=utf-8'
        except OSError as error:
            print(f'Dashboard read failed: {error}', file=sys.stderr, flush=True)
            body = b'{"error":"Cannot read dashboard data"}'
            status, content_type = 500, 'application/json; charset=utf-8'
        self.send_body(status, body, content_type)

    def do_POST(self):
        if not self.host_allowed():
            self.send_json(403, {'error': 'Forbidden Host'})
            return
        if urlsplit(self.path).path != '/api/stop':
            self.send_json(404, {'error': 'Not found'})
            return
        supplied = self.headers.get('X-Dashboard-Token', '')
        if not supplied or not secrets.compare_digest(supplied, self.server.control_token):
            self.send_json(403, {'error': 'Invalid dashboard token'})
            return
        self.send_json(200, {'stopping': True})
        threading.Thread(target=self.server.shutdown, daemon=True).start()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path.cwd())
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--instance', default=None)
    args = parser.parse_args(argv)
    if not args.project.is_dir():
        parser.error('Project directory does not exist')
    server = None
    try:
        server = DashboardServer(args.project, args.port, args.instance)
        write_state(server.root, server.state())
        print('Dashboard: ' + server.state()['base_url'], flush=True)
        server.serve_forever(poll_interval=0.1)
        return 0
    except KeyboardInterrupt:
        return 0
    except (OSError, ValueError) as error:
        print('Dashboard: ' + str(error), file=sys.stderr, flush=True)
        return 1
    finally:
        if server is not None:
            server.server_close()
            state = read_state(server.root)
            if state and state.get('instance_id') == server.instance and state.get('pid') == os.getpid():
                (runtime_folder(server.root) / 'runtime.json').unlink(missing_ok=True)


if __name__ == '__main__':
    raise SystemExit(main())
