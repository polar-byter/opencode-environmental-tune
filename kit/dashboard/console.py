"""Learning iteration 1: inspect a journal without an HTTP server.

Run from the repository root after implementing parse_event, read_events and main:
    py -m kit.dashboard.console kit/dashboard/examples/events.jsonl

This entry point deliberately imports only the journal reader.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .journal import read_events


def main(argv: list[str] | None = None) -> int:
    """Read a positional journal path with argparse, then print each event.

    argv=None lets argparse read the real command line; tests pass a list of strings.
    Output: first "Events: <count>", then "<kind> @ <at>" for each event in file order.
    Missing/empty file: print "Events: 0" and return 0.
    ValueError or OSError from reading: print "ERROR: <message>" to stderr, return 1.
    Success returns 0. Argument errors and --help keep argparse's normal behavior.
    Never write to the journal or start OpenCode.
    """
    # ПОДСКАЗКА: argparse.ArgumentParser описывает параметры команды. Добавь один
    #   позиционный аргумент 'path' с type=Path, затем вызови parse_args(argv).
    #   Пример независимой команды смотри в kit/dashboard/__main__.py: build_parser.
    # ПОДСКАЗКА: вызови уже готовую read_events(args.path). len даёт число событий.
    #   f-строка позволяет вставить значение переменной в вывод print.
    # ПОДСКАЗКА: try/except нужен вокруг чтения. У print есть аргумент file=sys.stderr.
    raise NotImplementedError('learning iteration 1: console.main')


if __name__ == '__main__':
    raise SystemExit(main())
