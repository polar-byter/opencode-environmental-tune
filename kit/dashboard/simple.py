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
        raise NotImplementedError('learning iteration 3: Handler.do_GET')


def make_server(port: int, path: Path) -> HTTPServer:
    """Create HTTPServer(('127.0.0.1', port), Handler), store journal_path, return it.

    The stored path is Path(path).resolve(). Port 0 chooses a free port for checks.
    Do not start serving here: the caller owns serve_forever and server_close.
    Do not require an existing journal: it may appear after startup.
    """
    raise NotImplementedError('learning iteration 3: make_server')


def main(argv: list[str] | None = None) -> int:
    """Parse positional path (Path), --port (int, default 8765), call make_server.

    Print "Dashboard: http://127.0.0.1:<actual port>/", then serve_forever.
    Ctrl+C returns 0; ValueError/OSError -> "ERROR: <message>" on stderr and return 1.
    Always close a successfully created server in finally. No automatic browser launch.
    """
    raise NotImplementedError('learning iteration 3: simple.main')


if __name__ == '__main__':
    raise SystemExit(main())
