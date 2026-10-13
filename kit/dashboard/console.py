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

    argv = None lets argparse read the real command line; tests pass a list of strings.
    Output: first "Events: <count>", then "<kind> @ <at>" for each event in file order.
    Missing/empty file: print "Events: 0" and return 0.
    ValueError or OSError from reading: print "ERROR: <message>" to stderr, return 1.
    Success returns 0. Argument errors and --help keep argparse's normal behavior.
    Never write to the journal or start OpenCode.

    Уже реализовано. В команде ...console demo.jsonl путь demo.jsonl - позиционный
    аргумент: значение без метки --path на оговорённом месте команды.
    argv=None читает команду терминала; argv=['demo.jsonl'] удобно передать в тесте.
    read_events даёт список, print показывает его; return 0/1 сообщает успех/ошибку
    вызывающему коду, а не печатает число. Подробный разбор - в уроке этапа 1.
    """
    param_parser = argparse.ArgumentParser(description="Inspect a journal file.")
    param_parser.add_argument('path', type=Path, help='Path to the journal file')
    args = param_parser.parse_args(argv)
    args_path = Path(args.path)
    try:
        result = read_events(args_path)
    except (ValueError, OSError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        return 1
    print(f'Events: {len(result)}')
    for event in result:
        print(f'{event["kind"]} @ {event["at"]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
