"""Start the dashboard: py -m kit.dashboard [--project PATH ...] [--port N] [--no-browser]

Status: SKELETON. main raises NotImplementedError until it is implemented.
This is the later multi-project entry point. Begin with console.py, then simple.py;
see README.ru.md for the new learning order.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import webbrowser

from .server import make_server

DEFAULT_PORT = 8765


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='py -m kit.dashboard', description=__doc__)
    parser.add_argument('--project', action='append', type=Path,
                        help='project folder with the kit; repeat for several (default: current folder)')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='0 picks a free port')
    parser.add_argument('--no-browser', action='store_true', help='do not open the page')
    return parser


def main(argv=None) -> int:
    """Parse arguments, make_server(port, projects or [Path.cwd()]), print
    "Dashboard: http://127.0.0.1:<port>/", open it with webbrowser unless --no-browser,
    serve_forever until Ctrl+C (then return 0). A ValueError from discover or an OSError
    (port busy) is printed as "ERROR: ..." to stderr and returns 1."""
    # ПОЗЖЕ, полный сервер. Сначала готовим console.py, затем simple.py.
    # Пример: --project D:/project --port 8766 --no-browser.
    # --project можно повторить; --no-browser - флаг без значения, даёт True.
    # 1. build_parser уже готов: parse_args(argv) даёт args.project/port/no_browser.
    #    Нет --project -> используй список [Path.cwd()] (текущая папка).
    # 2. Создай сервер make_server; напечатай URL с реальным портом сервера.
    # 3. Если no_browser=False, webbrowser.open открывает URL; затем serve_forever.
    # 4. Ctrl+C -> код 0; ValueError/OSError -> ERROR в stderr и код 1.
    # Закрытие сервера и try/finally разберём по образцу simple.main перед этапом.
    raise NotImplementedError('dashboard step 9.2: main')


if __name__ == '__main__':
    raise SystemExit(main())
