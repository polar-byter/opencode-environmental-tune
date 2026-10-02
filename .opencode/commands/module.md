---
description: Build a module brain-first — skeleton + tests, then delegate bodies to the executor
agent: build
---

Build module `$ARGUMENTS` using the mandatory build pipeline from AGENTS.md.

Steps:
1. Plan: update the work plan in the Obsidian vault.
2. Skeleton: create the module following the **Project layout** in AGENTS.md. Add a detailed spec comment inside every class and function/method (Javadoc for Java, docstring for Python). Leave each body as the placeholder the project's language uses — `throw new UnsupportedOperationException("TODO: executor")` for Java, `raise NotImplementedError("TODO: executor")` for Python.
3. Tests: create tests following the **Project stack** in AGENTS.md. Run the stack's test command — they must fail now.
4. Delegate: for each class or method, call the `executor` subagent with exactly one piece per call. Never delegate the whole module.
5. Review: after each reply, read the code and run the stack's test command. Fix or send back.
6. Report: stop only when the test command is green.
