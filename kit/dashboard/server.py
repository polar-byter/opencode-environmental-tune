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
Later multi-project server. The first browser exercise uses simple.py instead.
Keep these contracts for later iterations; see README.ru.md.
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
    # ПОЗЖЕ, после простого сервера. Вход: метод и путь БЕЗ '?...'.
    # ('GET', '/api/projects/demo/tasks/t1') -> ('task_view', {'project': 'demo', 'task': 't1'}).
    # 1. Начни с точного совпадения метода/пути для '/api/meta'.
    # 2. Разбей путь и каждый шаблон на части по '/'; число частей должно совпасть.
    # 3. Обычная часть совпадает буквально, <name> захватывает одну НЕПУСТУЮ часть.
    # 4. Верни первое совпадение и словарь параметров; нет совпадений -> None.
    # '/api/meta/' не равен '/api/meta': последний пустой сегмент не отбрасывай.
    raise NotImplementedError('dashboard step 7.1: match_route')


def host_allowed(host: str | None, port: int) -> bool:
    """True only for "127.0.0.1:<port>" or "localhost:<port>" (case-insensitive host part).
    None, another port or any other name -> False."""
    # ПОЗЖЕ. Проверяем адрес, под которым браузер обратился к локальному серверу.
    # host='LOCALHOST:8765', port=8765 -> True; host=None или другой порт -> False.
    # Сравни с двумя допустимыми строками из описания, без учёта регистра имени.
    # Не принимай произвольный адрес только потому, что он содержит 'localhost'.
    raise NotImplementedError('dashboard step 7.2: host_allowed')


def post_allowed(headers: dict, token: str) -> str | None:
    """Why a POST is refused, or None if it is allowed.

    headers: lower-case header names -> values. Reasons, checked in this order:
      "missing token"         no x-dashboard-token
      "wrong token"           secrets.compare_digest(value, token) is False
      "json body required"    content-type does not start with "application/json"
    """
    # ПОЗЖЕ, перед записью настроек. None здесь значит «разрешено», строка - причина отказа.
    # headers уже имеет ключи в нижнем регистре; token - секрет текущего запуска сервера.
    # 1. Нет x-dashboard-token -> 'missing token'.
    # 2. Есть, но compare_digest не совпал -> 'wrong token'.
    # 3. Не JSON Content-Type -> 'json body required'. Проверяй в этом порядке.
    # Всё верно -> None. Эта проверка НЕ сохраняет форму и НЕ читает тело запроса.
    raise NotImplementedError('dashboard step 7.3: post_allowed')


def read_json_body(raw: bytes) -> dict:
    """Decode a request body: UTF-8 JSON object. Longer than MAX_BODY, invalid JSON or not
    a dict -> ValueError with a short reason."""
    # ПОЗЖЕ. raw - байты тела POST; результат - dict, как у parse_event, но без kind/at.
    # b'{"port":"8765"}' -> {'port': '8765'}; b'[]' -> ValueError.
    # 1. Проверь len(raw) относительно MAX_BODY до разбора.
    # 2. decode('utf-8') превратит байты в текст; json.loads - текст в Python-значение.
    # 3. Неверная кодировка/JSON или не dict -> ValueError с коротким сообщением.
    # Не вызывай journal.parse_event: у формы другой набор допустимых полей.
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
        # ПОЗЖЕ, после match_route/host_allowed/send_json и простого do_GET.
        # Цель: проверить запрос и вызвать нужный обработчик; бизнес-правила уже в модулях.
        # 1. Host не разрешён -> JSON-ошибка 403 и выход.
        # 2. urlsplit(self.path) отделит path от query; parse_qs разбирает query.
        #    Пример '?source=api' -> {'source': ['api']} (значения - СПИСКИ строк).
        # 3. match_route('GET', path) -> имя метода и params; нет совпадения -> 404.
        # 4. Найди метод Handler по имени и вызови с params/query. Он сам отправит ответ.
        # 5. ValueError -> 400; прочая ошибка -> 500 без traceback в ответе.
        # Механизм вызова метода по имени разберём отдельно, когда дойдём до этапа.
        raise NotImplementedError('dashboard step 7.5: Handler.do_GET')

    def do_POST(self):
        # ПОЗЖЕ, только перед функциями записи. GET эту форму не сохраняет.
        # 1. Как в do_GET, проверь Host. Затем post_allowed с заголовками
        #    в нижнем регистре и self.server.token; отказ -> 403.
        # 2. Найди POST-маршрут. Нет маршрута -> 404, сохранение не вызывать.
        # 3. Прочитай ограниченное тело из self.rfile по Content-Length,
        #    проверь размер и передай read_json_body.
        # 4. Вызови обработчик с params/body. ValueError -> 400, прочая ошибка -> 500.
        # До упражнения подготовим отдельные проверки неверного размера/заголовков
        # и подтвердим, что при отказе настройки не меняются.
        raise NotImplementedError('dashboard step 7.6: Handler.do_POST')

    def send_json(self, status: int, data) -> None:
        """Compact UTF-8 JSON with Content-Type application/json and Cache-Control no-store."""
        # ПОЗЖЕ. Аналог send_bytes простого сервера: аргументы status и Python-данные.
        # Пример status=200, data={'ok': True} -> браузер получит JSON, не Python repr.
        # 1. json.dumps с ensure_ascii=False и separators=(',', ':') -> компактный текст.
        # 2. encode('utf-8') -> байты. Отправь status и заголовки Content-Type,
        #    Cache-Control: no-store; завершение заголовков, затем wfile.write.
        # Это отправка ответа, не return data.
        raise NotImplementedError('dashboard step 7.7: Handler.send_json')

    def project(self, key: str) -> projects.Project:
        """The watched project by key; unknown key -> ValueError("unknown project")."""
        # ПОЗЖЕ. key='demo' -> объект из self.server.projects['demo'].
        # Словарь server.projects уже создан конструктором сервера.
        # Нет такого ключа -> ValueError('unknown project'), не случайный KeyError.
        # Проверяй ключ здесь, чтобы остальные обработчики не повторяли проверку.
        raise NotImplementedError('dashboard step 7.8: Handler.project')

    # --- route handlers: each returns nothing and sends one response ---------------------

    def page(self, params, query):
        """index.html from STATIC_DIR."""
        # ПОЗЖЕ. params/query здесь не нужны; ответ - HTML главной страницы.
        # Прочитай STATIC_DIR / 'index.html' как байты и отправь 200 с типом HTML.
        # Используй порядок заголовки -> тело, изученный в простом сервере.
        raise NotImplementedError('dashboard step 8.1: page')

    def static(self, params, query):
        """A file from STATIC_FILES with its content type; any other name -> 404."""
        # ПОЗЖЕ. params['file'] содержит имя, например 'app.js'.
        # Сначала проверь наличие имени в STATIC_FILES; неизвестное -> 404 и выход.
        # Только разрешённое имя соедини с STATIC_DIR, прочитай байты и отправь
        # с Content-Type из STATIC_FILES. '../secret' не должен попасть на диск.
        raise NotImplementedError('dashboard step 8.2: static')

    def meta(self, params, query):
        """{"token": server token, "projects": [{"key", "name"}]}."""
        # ПОЗЖЕ. Данные уже в self.server: token и словарь projects.
        # Собери список {'key': ..., 'name': ...} из объектов проектов, затем
        # send_json(200, {'token': ..., 'projects': ...}). params/query не нужны.
        # token - защита POST, не API-ключ модели; API-ключи сюда не добавляй.
        raise NotImplementedError('dashboard step 8.3: meta')

    def project_list(self, params, query):
        """[{"key", "name", "root", "models": projects.model_choice, "tasks": projects.list_tasks}]."""
        # ПОЗЖЕ, после projects.list_tasks/model_choice.
        # Перебери self.server.projects: для каждого объекта создай одну строку
        # key/name/root (root строкой), models и tasks через готовые функции projects.
        # Два проекта -> две строки. Отправь список через send_json(200, ...).
        raise NotImplementedError('dashboard step 8.4: project_list')

    def task_view(self, params, query):
        """{"summary", "work_items", "tests", "guards"} from journal functions of the task's events."""
        # ПОЗЖЕ, после полной summary/work_items/guard_status.
        # 1. params содержит project/task: найди проект через self.project.
        # 2. projects.task_dir проверит имя задачи; оттуда прочитай events.jsonl.
        # 3. Вызови четыре готовые функции journal и собери summary/work_items/tests/guards.
        # 4. Отправь словарь через send_json. Не копируй подсчёты в HTTP-обработчик.
        raise NotImplementedError('dashboard step 8.5: task_view')

    def task_sessions(self, params, query):
        """sessions.task_sessions(server cache, root, events, time.time())."""
        # ПОЗЖЕ, после sessions.task_sessions.
        # Найди проект и проверенную папку задачи, прочитай её журнал.
        # Передай self.server.cache, root, events и time.time() в готовую функцию
        # sessions.task_sessions. Её словарь отправь через send_json(200, ...).
        raise NotImplementedError('dashboard step 8.6: task_sessions')

    def task_report(self, params, query):
        """{"markdown": text of .metrics/<task>/report.md} or {"markdown": None} if absent."""
        # ПОЗЖЕ. project/task -> проверенная папка задачи -> report.md.
        # Если файл есть, прочитай UTF-8 и отправь {'markdown': текст}.
        # Нет файла -> {'markdown': None}. Это нормальный ответ 200, не ошибка:
        # итоговый отчёт ещё не создан. Путь из URL сначала проверяет task_dir.
        raise NotImplementedError('dashboard step 8.7: task_report')

    def settings_get(self, params, query):
        """settings.get_settings(project root)."""
        # ПОЗЖЕ, после settings.get_settings.
        # Найди проект по params['project']; его root передай get_settings.
        # Отправь её ответ через send_json(200, ...). Маски ключей уже готовит settings.
        raise NotImplementedError('dashboard step 8.8: settings_get')

    def models(self, params, query):
        """settings.model_list(source, base_url, key_env) from the query string."""
        # ПОЗЖЕ. query - словарь СПИСКОВ от parse_qs, не сама строка '?...'.
        # Начни с примера {'source': ['lmstudio']}: нужна первая строка списка.
        # Получи source/base_url/key_env, передай в settings.model_list;
        # список моделей отправь через send_json. Не возвращай значение API-ключа.
        raise NotImplementedError('dashboard step 8.9: models')

    def settings_save(self, params, body):
        """settings.save_settings(project root, body)."""
        # ПОЗЖЕ, после защиты POST и settings.save_settings.
        # body - уже проверенный JSON-словарь. Найди root через self.project,
        # вызови save_settings(root, body), отправь её результат через send_json.
        # В этой функции не повторяй проверку формы и не сохраняй секреты второй раз.
        raise NotImplementedError('dashboard step 8.10: settings_save')

    def settings_apply(self, params, body):
        """settings.apply_settings(project root, body)."""
        # ПОЗЖЕ, после защиты POST и settings.apply_settings.
        # Найди root выбранного проекта; вызови apply_settings(root, body).
        # Отправь её словарь с кодом/выводом применения, не запускай OpenCode отдельно.
        raise NotImplementedError('dashboard step 8.11: settings_apply')

    def settings_reset(self, params, body):
        """settings.reset_settings(project root)."""
        # ПОЗЖЕ, после защиты POST и settings.reset_settings.
        # Найди root выбранного проекта, вызови reset_settings(root), отправь ответ.
        # body здесь не используется. Проверка token уже выполнена в do_POST.
        raise NotImplementedError('dashboard step 8.12: settings_reset')

    def stream(self, params, query):
        """Server-Sent Events until the client disconnects: every live.POLL_SECONDS poll a
        live.ChangeWatcher over live.watched_files and send live.sse_message("change", row)
        for each change; send a ": ping" comment line every live.HEARTBEAT_SECONDS."""
        # ПОЗЖЕ, необязательное SSE, после ручного обновления и готового live.py.
        # Здесь ответ остаётся открытым: это поток уведомлений, не один JSON-объект.
        # 1. Отправь заголовки text/event-stream и создай ChangeWatcher.
        # 2. Раз в POLL_SECONDS обновляй watched_files, вызывай watcher.poll.
        # 3. Каждую строку изменения преврати в sse_message('change', row),
        #    запиши в wfile и flush(), чтобы браузер получил её сразу.
        # 4. Без изменений раз в HEARTBEAT_SECONDS отправляй комментарий ': ping'
        #    с пустой строкой после него. Клиент отключился -> закончи цикл.
        # Перед этапом отдельно разберём цикл, sleep и ошибки разрыва соединения.
        raise NotImplementedError('dashboard step 8.13: stream')


def make_server(port: int, paths: list[Path]) -> DashboardServer:
    """DashboardServer for projects.discover(paths). port 0 picks a free port."""
    # ПОЗЖЕ, после discover и DashboardServer. paths - явные папки проектов.
    # 1. Получи project_list через projects.discover(paths).
    # 2. Создай DashboardServer(port, project_list) и верни объект.
    # port=0 выбирает свободный порт. Здесь не открывай браузер и не вызывай serve_forever.
    # Неверный проект/занятый порт: ошибка передаётся вызывающей main.
    raise NotImplementedError('dashboard step 9.1: make_server')
