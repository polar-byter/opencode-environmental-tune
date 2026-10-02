---
description: Build a module brain-first — skeleton + tests, then delegate bodies to the executor
agent: build
---

Build module `$ARGUMENTS` using the mandatory build pipeline from AGENTS.md.

Steps:
1. Plan: update the work plan in the Obsidian vault.
2. Skeleton: create `app/$ARGUMENTS.py` with classes, functions, and signatures. Add a detailed spec comment inside each function. Leave `raise NotImplementedError("TODO: executor")` as the body.
3. Tests: create `tests/test_$ARGUMENTS.py` against the skeleton. Run them — they must fail now.
4. Delegate: for each function, call the `executor` subagent with exactly one function per call. Never delegate the whole file.
5. Review: after each reply, read the code and run `py -m unittest discover -s tests -v`. Fix or send back.
6. Report: stop only when all tests are green.
