---
description: Build a module master-chief-first — skeleton + tests, then delegate bodies to the executor
agent: build
---

Build module `$ARGUMENTS` using the mandatory build pipeline from AGENTS.md.

Steps:
1. Plan: resolve, read, and update the work plan using the **Work plan (memory)** section of AGENTS.md. Use the same resolved file throughout this task.
   Start task metrics according to **Task metrics** in AGENTS.md; keep the task ID in the plan.
2. Skeleton: create the module following the **Project layout** in AGENTS.md. Add a detailed spec comment inside every class and function/method (Javadoc for Java, XML doc comments for C#, docstring for Python). Leave each body as the placeholder the project's language uses — `throw new UnsupportedOperationException("TODO: executor")` for Java, `throw new NotImplementedException();` for C#, `raise NotImplementedError("TODO: executor")` for Python.
3. Tests: create tests following the **Project stack** in AGENTS.md. First run `task_metrics.py check` with the stack's test command: if it exits with 4, stop and ask the user to fix the setup. Then run `task_metrics.py test --scope <module> --phase baseline` — the initial skeleton tests should fail (red run; record no review for it).
4. Delegate: register each attempt with `task_metrics.py delegate` and frozen requirements, then call `executor` for one small complete class or cohesive file. Split a function only for an isolated fix or a justified large work item. Never delegate the whole module.
5. Review: immediately after each reply run task_metrics.py inspect before Master Chief edits or tests, then check file boundaries and every frozen requirement, add missing edge-case tests, run scoped tests through `task_metrics.py test --scope <work_item>`, and provide `--checks` when accepting. Act on its exit code exactly as in **Review loop and stop rules** in AGENTS.md: 0 accept, 1 rework or fix the test, 4 fix the setup or ask, 3 STOP and wait for the user.
6. Report: after a green module run and an unfiltered `test --scope full` with all registered attempts reviewed, run task_metrics.py finish and include its statistics as a separate section in the final answer. When a stop rule fires (exit code 3), do not run finish: say clearly that the module is not finished, why, and what decision you need, then wait for the user.
