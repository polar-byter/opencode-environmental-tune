"""HTTP server of the dashboard: JSON API, static page and the live event stream.

Standard library only: http.server.ThreadingHTTPServer + BaseHTTPRequestHandler.

Security (the server can save API keys and rebuild the OpenCode config):
- It listens on 127.0.0.1 only.
- Every request must carry Host "127.0.0.1:<port>" or "localhost:<port>". This blocks
  DNS rebinding: a foreign site cannot reach the server under its own host name.
- Every POST must carry the header X-Dashboard-Token with the random token of this server
  run and Content-Type application/json. A foreign page cannot read the token (it is only
  served to same-origin GET /api/meta), so it cannot forge a request.
- Static files come only from the STATIC_FILES allowlist; task names are validated by
  projects.task_dir.

Routes (ROUTES below): method, pattern with <name> parts, handler method name.

Status: SKELETON. Every function raises NotImplementedError until it is implemented.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import time
from urllib.parse import parse_qs, urlsplit

from . import journal, live, projects, sessions, settings

STATIC_DIR = Path(__file__).resolve().parent / 'static'
STATIC_FILES = {'index.html': 'text/html; charset=utf-8', 'app.js': 'text/javascript; charset=utf-8',
                'style.css': 'text/css; charset=utf-8'}
MAX_BODY = 64 * 1024

ROUTES = [
    ('GET', '/', 'page'),
    ('GET', '/static/<file>', 'static'),
    ('GET', '/api/meta', 'meta'),
    ('GET', '/api/projects', 'project_list'),
    ('GET', '/api/projects/<project>/tasks/<task>', 'task_view'),
    ('GET', '/api/projects/<project>/tasks/<task>/sessions', 'task_sessions'),
    ('GET', '/api/projects/<project>/tasks/<task>/report', 'task_report'),
    ('GET', '/api/projects/<project>/settings', 'settings_get'),
    ('GET', '/api/models', 'models'),
    ('POST', '/api/projects/<project>/settings/save', 'settings_save'),
    ('POST', '/api/projects/<project>/settings/apply', 'settings_apply'),
    ('POST', '/api/projects/<project>/settings/reset', 'settings_reset'),
    ('GET', '/api/stream', 'stream'),
]


def match_route(method: str, path: str) -> tuple[str, dict] | None:
    """Find the handler for a request.

    path is the URL path without the query. A pattern part "<name>" matches exactly one
    non-empty path segment and is returned in the params dict; other parts must be equal.
    Trailing "/" is not ignored ("/api/meta/" does not match "/api/meta").
    Returns (handler name, params) for the first matching (method, pattern) in ROUTES,
    or None.
    """
    raise NotImplementedError('dashboard step 7.1: match_route')


def host_allowed(host: str | None, port: int) -> bool:
    """True only for "127.0.0.1:<port>" or "localhost:<port>" (case-insensitive host part).
    None, another port or any other name -> False."""
    raise NotImplementedError('dashboard step 7.2: host_allowed')


def post_allowed(headers: dict, token: str) -> str | None:
    """Why a POST is refused, or None if it is allowed.

    headers: lower-case header names -> values. Reasons, checked in this order:
      "missing token"         no x-dashboard-token
      "wrong token"           secrets.compare_digest(value, token) is False
      "json body required"    content-type does not start with "application/json"
    """
    raise NotImplementedError('dashboard step 7.3: post_allowed')


def read_json_body(raw: bytes) -> dict:
    """Decode a request body: UTF-8 JSON object. Longer than MAX_BODY, invalid JSON or not
    a dict -> ValueError with a short reason."""
    raise NotImplementedError('dashboard step 7.4: read_json_body')


class DashboardServer(ThreadingHTTPServer):
    """Server state shared by the request threads."""
    daemon_threads = True

    def __init__(self, port: int, project_list: list[projects.Project]):
        super().__init__(('127.0.0.1', port), Handler)
        self.port = self.server_address[1]
        self.token = secrets.token_urlsafe(32)
        self.projects = {p.key: p for p in project_list}
        self.cache = sessions.SessionCache()


class Handler(BaseHTTPRequestHandler):
    """One request. do_GET/do_POST check the host (and the token for POST), find the route
    and call the handler method; errors become JSON {"error": "..."} with a status code:
    unknown route 404, bad host 403, refused POST 403, ValueError from the logic 400,
    anything else 500 (the traceback is printed to the console, never sent)."""

    server: DashboardServer

    def do_GET(self):
        raise NotImplementedError('dashboard step 7.5: Handler.do_GET')

    def do_POST(self):
        raise NotImplementedError('dashboard step 7.6: Handler.do_POST')

    def send_json(self, status: int, data) -> None:
        """Compact UTF-8 JSON with Content-Type application/json and Cache-Control no-store."""
        raise NotImplementedError('dashboard step 7.7: Handler.send_json')

    def project(self, key: str) -> projects.Project:
        """The watched project by key; unknown key -> ValueError("unknown project")."""
        raise NotImplementedError('dashboard step 7.8: Handler.project')

    # --- route handlers: each returns nothing and sends one response ---------------------

    def page(self, params, query):
        """index.html from STATIC_DIR."""
        raise NotImplementedError('dashboard step 8.1: page')

    def static(self, params, query):
        """A file from STATIC_FILES with its content type; any other name -> 404."""
        raise NotImplementedError('dashboard step 8.2: static')

    def meta(self, params, query):
        """{"token": server token, "projects": [{"key", "name"}]}."""
        raise NotImplementedError('dashboard step 8.3: meta')

    def project_list(self, params, query):
        """[{"key", "name", "root", "models": projects.model_choice, "tasks": projects.list_tasks}]."""
        raise NotImplementedError('dashboard step 8.4: project_list')

    def task_view(self, params, query):
        """{"summary", "pieces", "tests", "guards"} from journal functions of the task's events."""
        raise NotImplementedError('dashboard step 8.5: task_view')

    def task_sessions(self, params, query):
        """sessions.task_sessions(server cache, root, events, time.time())."""
        raise NotImplementedError('dashboard step 8.6: task_sessions')

    def task_report(self, params, query):
        """{"markdown": text of .metrics/<task>/report.md} or {"markdown": None} if absent."""
        raise NotImplementedError('dashboard step 8.7: task_report')

    def settings_get(self, params, query):
        """settings.get_settings(project root)."""
        raise NotImplementedError('dashboard step 8.8: settings_get')

    def models(self, params, query):
        """settings.model_list(source, base_url, key_env) from the query string."""
        raise NotImplementedError('dashboard step 8.9: models')

    def settings_save(self, params, body):
        """settings.save_settings(project root, body)."""
        raise NotImplementedError('dashboard step 8.10: settings_save')

    def settings_apply(self, params, body):
        """settings.apply_settings(project root, body)."""
        raise NotImplementedError('dashboard step 8.11: settings_apply')

    def settings_reset(self, params, body):
        """settings.reset_settings(project root)."""
        raise NotImplementedError('dashboard step 8.12: settings_reset')

    def stream(self, params, query):
        """Server-Sent Events until the client disconnects: every live.POLL_SECONDS poll a
        live.ChangeWatcher over live.watched_files and send live.sse_message("change", row)
        for each change; send a ": ping" comment line every live.HEARTBEAT_SECONDS."""
        raise NotImplementedError('dashboard step 8.13: stream')


def make_server(port: int, paths: list[Path]) -> DashboardServer:
    """DashboardServer for projects.discover(paths). port 0 picks a free port."""
    raise NotImplementedError('dashboard step 9.1: make_server')
