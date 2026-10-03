---
description: Build a module brain-first — skeleton + tests, then delegate bodies to the executor
agent: build
---

Build module `$ARGUMENTS` using the mandatory build pipeline from AGENTS.md.

Steps:
1. Plan: resolve, read, and update the work plan using the **Work plan (memory)** section of AGENTS.md. Use the same resolved file throughout this task.
   Start task metrics according to **Task metrics** in AGENTS.md; keep the task ID in the plan.
2. Skeleton: create the module following the **Project layout** in AGENTS.md. Add a detailed spec comment inside every class and function/method (Javadoc for Java, docstring for Python). Leave each body as the placeholder the project's language uses — `throw new UnsupportedOperationException("TODO: executor")` for Java, `raise NotImplementedError("TODO: executor")` for Python.
3. Tests: create tests following the **Project stack** in AGENTS.md. Run the stack's test command — they must fail now.
4. Delegate: for each class or method, call the `executor` subagent with exactly one piece per call. Never delegate the whole module.
5. Review: after each reply, read the code, record accepted/rework through task_metrics.py, and run the stack's test command through its test wrapper. Use the same wrapper for the initial red-test run in step 3. Fix or send back.
6. Report: stop only when the test command is green. Run task_metrics.py finish and include its statistics as a separate section in the final answer.
