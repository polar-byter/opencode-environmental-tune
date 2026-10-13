"""Learning iteration 3: a read-only page for one explicitly selected journal.

Future command, usable only after implementing the skeleton:
    py -m kit.dashboard.simple kit/dashboard/examples/events.jsonl --port 8765

No model settings, CLI exports, threads, caching or event streams in this iteration.
The later multi-project server reuses the journal logic learned here.
"""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

from . import journal

PAGE = Path(__file__).resolve().parent / 'static' / 'simple.html'


def task_view(path: Path) -> dict:
    """Read the configured file again on every call; return brief_summary(events).

    Empty/missing journal -> ValueError("no events yet"). A bad journal propagates
    ValueError, disk errors propagate OSError. Do not return raw journal events:
    the page needs only the fields documented by brief_summary.
    """
    # ЭТАП 3, после brief_summary: путь к файлу -> словарь сводки.
    # 1. Вызови journal.read_events(path), сохрани список.
    # 2. Пустой список -> ValueError('no events yet'), включая отсутствующий файл.
    # 3. Непустой список передай journal.brief_summary и верни её результат.
    # Файл с одним start -> event_count=1 в сводке. При повторном вызове читай
    # файл заново, чтобы увидеть изменения. Ошибки чтения не скрывай.
    raise NotImplementedError('learning iteration 3: task_view')


class Handler(BaseHTTPRequestHandler):
    """One GET request. The standard library creates Handler objects for us.

    make_server stores the chosen path as httpd.journal_path. It is not supplied by
    a browser, so a URL cannot select arbitrary files on the computer.
    """

    def send_bytes(self, status: int, content_type: str, body: bytes) -> None:
        """Send status, Content-Type, Content-Length, Cache-Control: no-store and body.

        Use send_response, send_header, end_headers, then wfile.write(body).
        len(body) counts bytes; headers must be sent before the body.
        """
        # ЭТАП 3. self - объект одного запроса, который создала библиотека.
        # send_bytes отправляет ответ браузеру; return со словарём этого не делает.
        # Пример аргументов: 200, 'text/plain; charset=utf-8', b'OK'.
        # 1. self.send_response(status) отправляет код результата.
        # 2. self.send_header(name, value) вызови для трёх заголовков из описания.
        #    Content-Length - строковое число БАЙТОВ: для b'OK' это '2'.
        #    Cache-Control: no-store запрещает хранить устаревший ответ.
        # 3. self.end_headers() отмечает конец заголовков.
        # 4. self.wfile.write(body) пишет байты ответа. Возвращать их не нужно.
        raise NotImplementedError('learning iteration 3: Handler.send_bytes')

    def do_GET(self) -> None:
        """Serve only two paths (use urlsplit(self.path).path to discard the query).

        Before routing, allow Host only if it is 127.0.0.1:<actual port> or
        localhost:<actual port> (case-insensitive); otherwise send plain-text 403.
        / -> PAGE.read_bytes(), status 200, text/html; charset=utf-8.
        /api/task -> task_view(self.server.journal_path), JSON encoded as UTF-8,
                     status 200, application/json; charset=utf-8.
        Other path -> plain-text 404. Never derive a disk path from the URL.
        ValueError -> JSON {"error": str(error)} with 400.
        OSError -> JSON {"error": "cannot read journal or page"} with 500.
        Send error responses through send_bytes too. Do not enable CORS.
        POST retains BaseHTTPRequestHandler's default 501 response.
        """
        # ЭТАП 3, после send_bytes. Библиотека вызывает do_GET при запросе браузера.
        # self.path - адрес, self.headers - заголовки, self.server - объект сервера.
        # Пример: '/api/task?x=1' -> urlsplit(self.path).path даёт '/api/task'.
        # 1. Проверь Host из self.headers.get('Host'): только localhost или
        #    127.0.0.1 с портом self.server.server_address[1], без учёта регистра.
        #    Чужой Host -> 403 через send_bytes и выход. Это защита от чужих сайтов.
        # 2. Для '/' прочитай PAGE.read_bytes(), отправь HTML с кодом 200.
        # 3. Для '/api/task' вызови task_view(self.server.journal_path).
        #    json.dumps(data, ensure_ascii=False) превращает словарь в текст JSON;
        #    .encode('utf-8') превращает текст в байты для send_bytes.
        # 4. Другой адрес -> 404. Не превращай адрес браузера в путь файла на диске.
        # 5. try/except при чтении: ValueError -> 400 с {'error': str(error)};
        #    OSError -> 500 с фиксированным сообщением из описания (не путями диска).
        # Все ответы отправляй один раз через send_bytes с нужным Content-Type.
        raise NotImplementedError('learning iteration 3: Handler.do_GET')


def make_server(port: int, path: Path) -> HTTPServer:
    """Create HTTPServer(('127.0.0.1', port), Handler), store journal_path, return it.

    The stored path is Path(path).resolve(). Port 0 chooses a free port for checks.
    Do not start serving here: the caller owns serve_forever and server_close.
    Do not require an existing journal: it may appear after startup.
    """
    # ЭТАП 3: создаём объект, но ещё не ждём запросов.
    # Пример: port=0 -> система выберет свободный порт; он будет в server_address[1].
    # 1. HTTPServer получает ('127.0.0.1', port) и класс Handler.
    # 2. Сохрани Path(path).resolve() в server.journal_path. Это новый атрибут:
    #    обработчик позже найдёт по нему заранее выбранный журнал.
    # 3. Верни server. serve_forever и закрытие будут в main, не здесь.
    # Отсутствующий журнал допустим; занятый порт вызывает OSError.
    raise NotImplementedError('learning iteration 3: make_server')


def main(argv: list[str] | None = None) -> int:
    """Parse positional path (Path), --port (int, default 8765), call make_server.

    Print "Dashboard: http://127.0.0.1:<actual port>/", then serve_forever.
    Ctrl+C returns 0; ValueError/OSError -> "ERROR: <message>" on stderr and return 1.
    Always close a successfully created server in finally. No automatic browser launch.
    """
    # ЭТАП 3, после make_server. main связывает команду в терминале с сервером.
    # ...simple events.jsonl --port 8765: путь - позиционный аргумент, его имя
    # не пишут, он стоит на оговорённом месте. --port - именованная опция.
    # 1. Как в console.main, создай ArgumentParser: 'path' с type=Path,
    #    '--port' с type=int и default=8765. Разбери argv.
    # 2. Создай сервер через make_server, напечатай URL с его РЕАЛЬНЫМ портом.
    #    args.port=0 не означает, что сервер слушает порт 0.
    # 3. server.serve_forever() ждёт запросов до Ctrl+C (KeyboardInterrupt).
    #    Ctrl+C -> возврат 0; ValueError/OSError -> stderr и возврат 1.
    # 4. finally выполнится и при ошибке: server_close освобождает порт.
    #    Закрывай только успешно созданный сервер. Перед подшагом разберём
    #    try/finally отдельно. Автоматически браузер пока не открываем.
    raise NotImplementedError('learning iteration 3: simple.main')


if __name__ == '__main__':
    raise SystemExit(main())
