"""Start the dashboard: py -m kit.dashboard [--project PATH ...] [--port N] [--no-browser]

Status: SKELETON. main raises NotImplementedError until it is implemented.
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
    raise NotImplementedError('dashboard step 9.2: main')


if __name__ == '__main__':
    raise SystemExit(main())
