# Project instructions

> TEMPLATE KIT. Copy `opencode.jsonc`, `AGENTS.md`, `.opencode/commands/`, and `kit/`
> into a new project. The kit is language-agnostic: only the sections marked `# EDIT` are
> specific to a project. Edit those for each new project.

## Build pipeline (mandatory)
The brain writes the blueprint; the executor only pours concrete.

### Brain (primary agent)
1. Skeleton first: create the module with classes, functions, signatures, and every import the bodies will need (the executor may not add imports).
2. Spec comments: inside every function write a detailed spec — what it does, what it returns, edge cases.
3. Placeholder body: leave the language's "not implemented" statement, e.g. `raise NotImplementedError("TODO: executor")` in Python, `throw new UnsupportedOperationException("TODO: executor")` in Java, `throw new NotImplementedException();` in C#.
4. Tests now: write unit tests against the skeleton. Red tests are expected.
5. Never implement a function body yourself. You may fix your own skeleton and tests.
6. Delegate a small complete class or cohesive source file by default, including its constructors and related methods. Split only a large or unrelated piece, explaining why. Never send an entire multi-file module. Use the fast executor for a genuinely small isolated edit, not one call for every trivial method.
7. Before each executor call (including retries), write a JSON list of the piece's requirements to `.metrics/<ID>/<piece>-requirements.json`. Include every spec edge case, validation order and invariant. Run `task_metrics.py delegate --task <ID> --piece <piece> --scope <test-scope> --files <source-file> --requirements <path>`. This freezes the requirements and hashes source files, including new and Git-ignored files. Do not change the plan, specs, tests or unrelated files while the executor is running. Keep generated test output under one of the excluded directories listed in Source snapshot boundaries.
8. Immediately after the executor returns, run `task_metrics.py inspect --task <ID> --piece <piece>` BEFORE any edits by the brain or running tests. It freezes which changes came from this attempt; exit 1 means unexpected edits and requires a rework. Then review: read the entire piece and check every frozen requirement against actual code and tests. For each requirement record `requirement`, `code` (file/symbol or line), `test` (test name), and `verified: true` in a JSON list at `.metrics/<ID>/<piece>-checks.json`. Do not mark it verified just because tests are green: check null/empty inputs, validation order, exceptions and state after rejection. After inspection, add missing edge-case tests yourself. Reviewer changes are recorded separately; never implement the delegated source after inspection. Run the piece's tests with `test --scope <test-scope>`; before accepting run `review --piece <piece> --result accepted --checks <path>`. The runner refuses acceptance without matching requirement evidence, a green scoped/full test and unchanged file boundaries. If project files change after that test, rerun it before accepting. For any incorrect implementation or unexpected edit, record `review --result rework`, inspect and restore only unintended edits, then register a fresh delegation. A snapshot detects changes but never restores files automatically. One return for corrections is one rework.
9. Done means green: a module is finished only when its module test command passes. Before finishing the whole task, run the full Project stack test command with `--scope full`; a scoped pass is not a full-project pass. If a stop rule fires first, the module is not finished: stop and ask the user.

### Review loop and stop rules (mandatory)
Every test run goes through `task_metrics.py test`. Its exit code decides the next step:

| Exit code | Meaning | What to do |
| --- | --- | --- |
| 0 | all selected tests passed | complete requirement evidence and record `review --result accepted --checks <path>`; continue. Run the full suite at task completion |
| 1 | selected tests ran, some failed | read failures and correct the reviewed piece or your own tests. Before implementation, one `test --scope <piece-or-module> --phase baseline` may establish expected red tests; it never counts as green or a rework. During implementation select tests for the current piece rather than repeatedly running unfinished modules. Never use baseline to hide a failure after work has started in that scope |
| 4 | no readable result: the project does not build, the test tool is missing or misconfigured, no tests found, or a timeout | not an executor mistake. Read the hints and the log. Record a rework only if the log shows a compile error in code the executor just wrote. Otherwise fix the setup (your skeleton, tests, test command) or ask the user. Never send the executor to "fix" the environment |
| 3 | STOP: a loop guard was reached | end the loop at once. Do not run tests, do not send reworks, do not start a new task ID to get around it. Tell the user what happened (the reason printed after `STOP:`) and suggest a decision: clarify the spec, fix the tests, fix the setup, or raise a limit. Wait. Do not run `finish` while waiting. After the user decides, run `task_metrics.py resume --task <ID> --reason "<decision>"` and continue; if the user decides to end the task, run `finish` |
| 2 | wrong usage or a broken journal | fix the command; never ignore it |

Loop guards (defaults; set others at `start` with `--max-reworks`, `--max-no-result`, `--max-failed-runs`, `--max-runs` only when the user asks):
- the same piece is sent back 3 times;
- 3 test runs in a row give no readable result;
- 12 work-phase test runs in a row in the same test scope are not green (initial baseline excluded);
- 60 test runs since start/resume, including baselines and scoped runs. Baseline build failures still count toward the global no-result limit. A green full run resets all scope failure streaks. Do not rename scopes to evade guards.

### Executor (subagent)
- Read the file before editing.
- Fill ONLY the function bodies.
- Never change signatures, imports, or the skeleton structure.
- Never edit tests or files other than the one you were given. If a test looks wrong or an import is missing, say so in the report.
- No shell. Report briefly: what changed, what is left.

## Complex projects (many modules)
1. Plan first: split the task into modules and write the checklist to the work plan resolved below. No code before the plan is approved.
2. Interfaces first: for each module list its public functions/classes and its dependencies. Modules must fit together.
3. One module at a time: skeleton → requirement and edge-case tests → baseline → delegate small complete classes → evidence-based review → green module tests → mark done. Do not write all future modules' tests up front and run them after every trivial edit.
4. Track progress in that work plan (`- [ ]` / `- [x]`). Read it at session start, update it after each module.
5. Never pass more than one module's context to a single executor call.
6. Done means green per module; the project is done when all modules and the unfiltered full suite are green.
7. After approval of the whole plan, autonomously choose the next unfinished module whose dependencies are ready. Explain the order in the plan. After review and passing tests, update the plan and continue without requiring the user to name modules or issue `/module` for each one. Ask only for missing access/tools or decisions that change the approved scope.
8. Keep one task metrics ID for the entire approved task. Finalize statistics after all planned modules are complete, not after each module. A request for just one module remains scoped to that module.

## Rules
- One subagent — one small complete class or cohesive source file; a function is appropriate for an isolated correction or a justified split.
- Keep the brain for planning, architecture, marketing, and review. Routine code goes local.
- Code, comments, and identifiers: English. Human-facing docs: Russian is fine.

## Kit utilities (independent of the project's language)
These tools live in `kit/`. They belong to the kit, not to the project. They are written in
Python, so they need Python on the machine whatever language the project uses.
Run them from the project root with the Python launcher: `py` on Windows, `python3` on macOS and Linux.
Commands in this file are written with `py`; on macOS and Linux replace `py` with `python3`.
- `kit/find_vault.py` — locate the Obsidian vault and the work plan: `py kit/find_vault.py`
- `kit/check_env.py` — check `opencode.jsonc` and the LM Studio connection: `py kit/check_env.py`
- `kit/pipeline_smoke.py` — offline smoke test of the brain → executor flow: `py kit/pipeline_smoke.py`
- Kit tests: `py -m unittest discover -s kit/tests -v`
- Task metrics: `py kit/task_metrics.py --help`; protocol below and details in `METRICS.ru.md`.

## Task metrics
- For each implementation task, choose a unique ASCII task ID and run `py kit/task_metrics.py start --task <ID> --session <current-session-ID> --title "<task title>"` as soon as the actual session ID is known, before environment setup, planning work and implementation. Add `--track-delegations` for implementation tasks. Keep this ID in the work plan. Do not reuse a finished task ID.
- Use the actual OpenCode session ID from context. If unavailable, inspect `opencode session list --format json` and match the current project and task; never guess or pick the latest automatically. If still unknown, omit `--session` and report missing token data.
- Before each executor call register it with `delegate` as described above. The script reports registered attempts without a matching review. It cannot detect calls that bypass this protocol.
- After each code review, run `py kit/task_metrics.py review --task <ID> --piece <function-or-class> --result accepted` with `--checks <path>` for acceptance, or `--result rework`. One return for corrections is one rework, regardless of the number of comments.
- Before the first implementation step of every task, run the test command once through `py kit/task_metrics.py check [--junit <file> | --junit-dir <folder>] -- <test command>`. Exit code 0 means the runner can read the results (failing tests are fine at this point). Exit code 4 means it cannot: do not write code; show the user the hints and ask them to fix the setup.
- During work use a documented piece/module test filter and stable `--scope <piece-or-module>`; store reports inside generated directories. Once per scope before delegation, an initial red run may use `--phase baseline`. At completion run the unfiltered project command with `--scope full`.
- Run the project's test command through `py kit/task_metrics.py test --task <ID> [--junit <file> | --junit-dir <folder>] -- <test command>`, using the **Project stack** tool and a filter for the current scope; the final full run uses the unfiltered command. React to its exit code as described in **Review loop and stop rules**.
- The runner recognizes unittest summaries and JUnit XML. `--junit <file>`: one report file; it must not exist before the run, so use a new name for every run (run-01.xml, run-02.xml, ...). `--junit-dir <folder>`: a folder where the tool writes one file per test class or project (Maven `target/surefire-reports`, Gradle `build/test-results/test`); only files written during the run are read. Unknown output, zero tests and skipped tests do not count as fully successful.
- Do not claim completion with pending delegated attempts or a missing/failing full suite. Resolve the warning first.
- At the end, after all executors have returned, run `py kit/task_metrics.py finish --task <ID>`. Insert its Markdown statistics in the final answer. If another agent writes the final answer, give it `.metrics/<ID>/report.md`; it must not invent or recompute counters.
- All `lmstudio` providers are local/free of API fees; every other known provider is paid by default. Missing usage must remain unknown. Token counts are a snapshot before the final answer, not a billing statement.
- These commands are required for ordinary text requests too, not only `/module`. Logging is instruction-driven, not an automatic plugin. Planning-only tasks may have no tests; never describe that as a successful test run.

## Project stack  # EDIT: language, build tool, test command
> The only language-specific part of the kit. Replace the example below for your language.
> The test command must give the runner a readable result: Python unittest output, or JUnit XML
> through `--junit` / `--junit-dir`. Check it once with `py kit/task_metrics.py check ...`.
> Examples (see the table "Подключение своего языка" in README.md for more):
> - Python unittest: `py kit/task_metrics.py test --task <ID> -- py -m unittest discover -s tests -v`
> - Java, Maven: `py kit/task_metrics.py test --task <ID> --junit-dir target/surefire-reports -- mvn -q test`
> - C#: `py kit/task_metrics.py test --task <ID> --junit .metrics/<ID>/run-NN.xml -- dotnet test --results-directory .metrics/<ID> --logger "junit;LogFileName=run-NN.xml"`
>   (needs the NuGet package `JunitXml.TestLogger` in the test project)

## Project layout  # EDIT: folders and files of this project
- `app/` — application code.
- `tests/` — unit tests of the project (separate dependent project).
- `kit/` — the kit's own tools and their tests (do not mix with project code).
- `.vscode/` — editor settings.

## Work plan (memory)  # EDIT: plan file name
- Plan file name: `currentsteps.md`.
- Locate the vault: run `py kit/find_vault.py --no-scan` (fast) or `py kit/find_vault.py` (with filesystem scan).
  - If it prints a vault: keep the plan at `<vault>/currentsteps.md` (create it if missing).
  - If no vault is found: use `currentsteps.md` in the project root.
- This section is the single source of truth for the plan location; agent prompts and commands must refer here rather than hard-code another note.
- If several vaults are found, use the project's explicitly selected vault; otherwise ask which vault to use before writing.
- Read the plan at the start of a session and update the same resolved file after major steps. Existing knowledge-base notes are background/history, not alternative active plans.

## Source snapshot boundaries
`delegate` reads all project files except generated directories `.git`, `.metrics`, `__pycache__`, `.venv`, `node_modules`, `target`, `build`, `dist`, `bin`, `obj`. Do not store application source in excluded directories. Symlinks/junctions outside excluded directories cause an error instead of being followed. Keep review evidence and transient logs in `.metrics/`; do not edit unrelated files before inspect. After inspect, the brain may add requirement tests; all changes after the latest green test require another run before acceptance.
