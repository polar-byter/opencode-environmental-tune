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
    """Reads the configured file again on every call; 
    returns brief_summary(events).
    Empty/missing journal -> ValueError("no events yet"). 
    A bad journal propagates
    ValueError, disk errors propagate OSError. 
    Does not return raw journal events:
    Our goal: only the fields documented by brief_summary.
    """
    path = Path(path).resolve()
    event_list = journal.read_events(path)
    if not event_list:
        raise ValueError("no events yet")
    return journal.brief_summary(event_list)

class Handler(BaseHTTPRequestHandler):
    """One GET request. 
    creates Handler objects.
    make_server stores the path chosen as httpd.journal_path.
    It is not supplied by a browser, so a URL cannot select arbitrary files on the computer.
    """

    def send_bytes(self, status: int, content_type: str, body: bytes) -> None:
        """Sends 
        status, 
        Content-Type, 
        Content-Length, 
        Cache-Control: no-store and body.
        """
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)


    def do_GET(self) -> None:
        """Serve only two paths (use urlsplit(self.path).path to discard the query).

        allows Host only if it is 127.0.0.1:<actual port>, localhost:<actual port>;
        otherwise send plain-text 403.

        route "/" -> PAGE.read_bytes(), 
            status 200, text/html; charset=utf-8.
        route "/api/task" -> task_view(self.server.journal_path), 
            JSON encoded as UTF-8, status 200, application/json; charset=utf-8.
        
        Other path -> plain-text 404.
        ValueError -> JSON {"error": str(error)} with 400.
        OSError -> JSON {"error": "cannot read journal or page"} with 500.
        Sends error responses through send_bytes too. 
        Does not enable CORS.
        POST retains BaseHTTPRequestHandler's default 501 response.
        """
        host = self.headers.get('Host', '').lower()
        port = self.server.server_port
        if host not in (f'127.0.0.1:{port}', f'localhost:{port}'):
            self.send_bytes(403, 'text/plain; charset=utf-8', b'Forbidden')
            return
        path = urlsplit(self.path).path
        try:
            if path == '/':
                body = PAGE.read_bytes()
                status = 200
                content_type = 'text/html; charset=utf-8'
            elif path == '/api/task':
                data = task_view(self.server.journal_path)
                body = json.dumps(data).encode('utf-8')
                status = 200
                content_type = 'application/json; charset=utf-8'
            else:
                body = b'Not Found'
                status = 404
                content_type = 'text/plain; charset=utf-8'
        except ValueError as e:
            error_body = json.dumps({"error": str(e)}).encode('utf-8')
            body = error_body
            status = 400
            content_type = 'application/json; charset=utf-8'
            
        except OSError:
            error_body = json.dumps({"error": "cannot read journal or page"}).encode('utf-8')
            body = error_body
            status = 500
            content_type = 'application/json; charset=utf-8'

        self.send_bytes(status, content_type, body)
        return


def make_server(port: int, path: Path) -> HTTPServer:
    """Creates HTTPServer(('127.0.0.1', port), Handler), store journal_path, return it.
    The stored path is Path(path).resolve(). Port 0 chooses a free port for checks.
    """
    server = HTTPServer(('127.0.0.1', port), Handler)
    server.journal_path = Path(path).resolve()
    return server

def main(argv: list[str] | None = None) -> int:
    """Parses positional path (Path), --port (int, default 8765), calls make_server.
    Print "Dashboard: http://127.0.0.1:<actual port>/", then serve_forever.
    Ctrl+C returns 0; ValueError/OSError -> "ERROR: <message>" on stderr and return 1.
    Always close a successfully created server in finally. No automatic browser launch.
    """
    arg_parser = argparse.ArgumentParser(description='Learning iteration 3: simple dashboard')
    arg_parser.add_argument('path', type=Path, help='Path to the journal file')
    arg_parser.add_argument('--port', type=int, default=8765, help='Port to serve on (default: 8765)')
    args = arg_parser.parse_args(argv)
    try:
        server = make_server(args.port, args.path)
        print(f'Dashboard: http://127.0.0.1:{server.server_port}/')
        server.serve_forever()
    except (ValueError, OSError) as e:
        print(f'ERROR: {e}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt received, exiting.")
        return 0
    finally:
        if 'server' in locals():
            server.server_close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
