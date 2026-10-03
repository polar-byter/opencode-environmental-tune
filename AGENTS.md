# Project instructions

> TEMPLATE KIT. Copy `opencode.jsonc`, `AGENTS.md`, `.opencode/commands/`, and `kit/`
> into a new project. The kit is language-agnostic: only the sections marked `# EDIT` are
> specific to a project. Edit those for each new project.

## Build pipeline (mandatory)
The brain writes the blueprint; the executor only pours concrete.

### Brain (primary agent)
1. Skeleton first: create the module with classes, functions, and signatures.
2. Spec comments: inside every function write a detailed spec — what it does, what it returns, edge cases.
3. Placeholder body: leave `raise NotImplementedError("TODO: executor")`.
4. Tests now: write unit tests against the skeleton. Red tests are expected.
5. Never implement a function body yourself.
6. Delegate one piece at a time: one function or class per executor call. Small edits go to the fast executor.
7. Review: after the executor replies, read the code and run the tests. Fix or send back.
8. Done means green: the task is finished only when the project's test command passes.

### Executor (subagent)
- Read the file before editing.
- Fill ONLY the function bodies.
- Never change signatures, imports, or the skeleton structure.
- No shell. Report briefly: what changed, what is left.

## Complex projects (many modules)
1. Plan first: split the task into modules and write the checklist to the work plan resolved below. No code before the plan is approved.
2. Interfaces first: for each module list its public functions/classes and its dependencies. Modules must fit together.
3. One module at a time: skeleton → tests → delegate bodies → review → green → mark it done in the plan.
4. Track progress in that work plan (`- [ ]` / `- [x]`). Read it at session start, update it after each module.
5. Never pass more than one module's context to a single executor call.
6. Done means green per module; the project is done when all modules are green.
7. After approval of the whole plan, autonomously choose the next unfinished module whose dependencies are ready. Explain the order in the plan. After review and passing tests, update the plan and continue without requiring the user to name modules or issue `/module` for each one. Ask only for missing access/tools or decisions that change the approved scope.
8. Keep one task metrics ID for the entire approved task. Finalize statistics after all planned modules are complete, not after each module. A request for just one module remains scoped to that module.

## Rules
- One subagent — one piece: a file, a function, or a class.
- Keep the brain for planning, architecture, marketing, and review. Routine code goes local.
- Code, comments, and identifiers: English. Human-facing docs: Russian is fine.

## Kit utilities (independent of the project's language)
These tools live in `kit/`. They belong to the kit, not to the project. They are written in
Python, so they need Python on the machine whatever language the project uses.
Run them with `py` from the project root.
- `kit/find_vault.py` — locate the Obsidian vault and the work plan: `py kit/find_vault.py`
- `kit/check_env.py` — check `opencode.jsonc` and the LM Studio connection: `py kit/check_env.py`
- `kit/pipeline_smoke.py` — offline smoke test of the brain → executor flow: `py kit/pipeline_smoke.py`
- Kit tests: `py -m unittest discover -s kit/tests -v`
- Task metrics: `py kit/task_metrics.py --help`; protocol below and details in `METRICS.ru.md`.

## Task metrics
- For each implementation task, choose a unique ASCII task ID and run `py kit/task_metrics.py start --task <ID> --session <current-session-ID> --title "<task title>"` before implementation. Keep this ID in the work plan. Do not reuse a finished task ID.
- Use the actual OpenCode session ID from context. If unavailable, inspect `opencode session list --format json` and match the current project and task; never guess or pick the latest automatically. If still unknown, omit `--session` and report missing token data.
- After each code review, run `py kit/task_metrics.py review --task <ID> --piece <function-or-class> --result accepted` or `--result rework`. One return for corrections is one rework, regardless of the number of comments.
- Run the project's test command through `py kit/task_metrics.py test --task <ID> -- <test command>`. A nonzero result during the initial red-test stage is expected. Read failures and fix them; do not hide them.
- The runner recognizes unittest summaries or one fresh JUnit XML file passed with `--junit <path>` before `--`. Unknown output, zero tests and skipped tests do not count as fully successful. For multiple XML files, configure the test tool to produce one combined report for the complete run; never pass one class's report as the full suite.
- At the end, after all executors have returned, run `py kit/task_metrics.py finish --task <ID>`. Insert its Markdown statistics in the final answer. If another agent writes the final answer, give it `.metrics/<ID>/report.md`; it must not invent or recompute counters.
- All `lmstudio` providers are local/free of API fees; every other known provider is paid by default. Missing usage must remain unknown. Token counts are a snapshot before the final answer, not a billing statement.
- These commands are required for ordinary text requests too, not only `/module`. Logging is instruction-driven, not an automatic plugin. Planning-only tasks may have no tests; never describe that as a successful test run.

## Project stack  # EDIT: language, build tool, test command
> The only language-specific part of the kit. Replace the example below for your language.
> Example — Python 3.13 (`C:\Python313\python.exe`), tests with `unittest` in `tests/`:
> `py -m unittest discover -s tests -v`. For Java use e.g. `mvn test`; for Go `go test ./...`.

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
