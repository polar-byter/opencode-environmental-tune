# Project instructions

> TEMPLATE KIT. Copy `opencode.jsonc`, `AGENTS.md`, `.opencode/commands/`, and `kit/`
> into a new project. The kit is language-agnostic: only the sections marked `# EDIT` are
> specific to a project. Edit those for each new project.

## Build pipeline (mandatory)
The Master Chief writes the blueprint; the executor only pours concrete.

### Task intake
- Accept the task either directly from the user's chat message or from `TASK.md` in the project root. The file is optional; a complete task in chat does not require creating or filling it.
- Read an existing `TASK.md` yourself. It describes product requirements and acceptance criteria, not the implementation plan. The user's current explicit request takes precedence; use compatible file requirements as context, and do not merge an unrelated old task into a new chat request. Ask only when a material conflict cannot be resolved from the current request.
- A short start request such as "Начинай" uses the requirements in `TASK.md`. Ask for requirements only when neither the chat nor the file describes the task; an absent, empty or unfilled template file must not block a task already described in chat. Do not ask the user to paste a file you can read.
- Discover and read the other relevant project documents yourself: applicable `AGENTS.md` files, the work plan resolved by Work plan (memory), `README.md` and existing architecture before planning, and the relevant setup/metrics/dashboard instructions before those operations. Read relevant sections as needed; do not require the user to enumerate Markdown files or restate the kit protocol in chat.
- Do not overwrite `TASK.md` with chat requirements unless the user asks. Record the accepted scope, source of requirements and current decisions in the resolved work plan.
- Create the architecture and dependency plan yourself. Do not require the user to name files, modules or executor calls.
- If the user authorizes the whole task and autonomous implementation, write the plan and proceed within that scope. Ask for plan approval only when it is still required by the user's request or a material unresolved decision.
- Keep temporary scripts, logs and review evidence in `.metrics/`; keep application source and tests in the project directories.
- Implementation requires the project's selected executor, from LM Studio, OpenCode or an explicitly configured API. If it is unavailable, report the blocker and leave the task unfinished. Do not implement bodies in the Master Chief without user authorization or silently substitute another model.

### Master Chief (primary agent)
1. Skeleton first: create the module with classes, functions, signatures, and every import the bodies will need (the executor may not add imports).
2. Spec comments: inside every function write a detailed spec — what it does, what it returns, edge cases.
3. Placeholder body: leave the language's "not implemented" statement, e.g. `raise NotImplementedError("TODO: executor")` in Python, `throw new UnsupportedOperationException("TODO: executor")` in Java, `throw new NotImplementedException();` in C#.
4. Tests now: write unit tests against the skeleton. Red tests are expected.
5. Never implement a function body yourself. You may fix your own skeleton and tests.
6. Delegate a small complete class or cohesive source file by default, including its constructors and related methods. Split only a large or unrelated work item, explaining why. Never send an entire multi-file module. Use the fast executor for a genuinely small isolated edit, not one call for every trivial method.
7. Before each executor call (including retries), write a JSON list of the work item's requirements to `.metrics/<ID>/<work_item>-requirements.json`. Include every spec edge case, validation order and invariant. Run `task_metrics.py delegate --task <ID> --work-item <work_item> --scope <test-scope> --files <source-file> --requirements <path>`. This freezes the requirements and hashes source files, including new and Git-ignored files. Do not change the plan, specs, tests or unrelated files while the executor is running. Keep generated test output under one of the excluded directories listed in Source snapshot boundaries.
8. Immediately after the executor returns, run `task_metrics.py inspect --task <ID> --work-item <work_item>` BEFORE any edits by the Master Chief or running tests. It freezes which changes came from this attempt; exit 1 means unexpected edits and requires a rework. Then review: read the entire work item and check every frozen requirement against actual code and tests. For each requirement record `requirement`, `code` (file/symbol or line), `test` (test name), and `verified: true` in a JSON list at `.metrics/<ID>/<work_item>-checks.json`. Do not mark it verified just because tests are green: check null/empty inputs, validation order, exceptions and state after rejection. After inspection, add missing edge-case tests yourself. Reviewer changes are recorded separately; never implement the delegated source after inspection. Run the work item's tests with `test --scope <test-scope>`; before accepting run `review --work-item <work_item> --result accepted --checks <path>`. The runner refuses acceptance without matching requirement evidence, a green scoped/full test and unchanged file boundaries. If project files change after that test, rerun it before accepting. For any incorrect implementation or unexpected edit, record `review --result rework`, inspect and restore only unintended edits, then register a fresh delegation. A snapshot detects changes but never restores files automatically. One return for corrections is one rework.
9. Done means green: a module is finished only when its module test command passes. Before finishing the whole task, run the full Project stack test command with `--scope full`; a scoped pass is not a full-project pass. If a stop rule fires first, the module is not finished: stop and ask the user.

### Review loop and stop rules (mandatory)
Every test run goes through `task_metrics.py test`. Its exit code decides the next step:

| Exit code | Meaning | What to do |
| --- | --- | --- |
| 0 | all selected tests passed | complete requirement evidence and record `review --result accepted --checks <path>`; continue. Run the full suite at task completion |
| 1 | selected tests ran, some failed | read failures and correct the reviewed work item or your own tests. Before implementation, one `test --scope <work_item-or-module> --phase baseline` may establish expected red tests; it never counts as green or a rework. During implementation select tests for the current work item rather than repeatedly running unfinished modules. Never use baseline to hide a failure after work has started in that scope |
| 4 | no readable result: the project does not build, the test tool is missing or misconfigured, no tests found, or a timeout | not an executor mistake. Read the hints and the log. Record a rework only if the log shows a compile error in code the executor just wrote. Otherwise fix the setup (your skeleton, tests, test command) or ask the user. Never send the executor to "fix" the environment |
| 3 | STOP: a loop guard was reached | end the loop at once. Do not run tests, do not send reworks, do not start a new task ID to get around it. Tell the user what happened (the reason printed after `STOP:`) and suggest a decision: clarify the spec, fix the tests, fix the setup, or raise a limit. Wait. Do not run `finish` while waiting. After the user decides, run `task_metrics.py resume --task <ID> --reason "<decision>"` and continue; if the user decides to end the task, run `finish` |
| 2 | wrong usage or a broken journal | fix the command; never ignore it |

Loop guards (defaults; set others at `start` with `--max-reworks`, `--max-no-result`, `--max-failed-runs`, `--max-runs` only when the user asks):
- Legacy sequential work: the same work item is sent back 3 times, or fails 3 times without changes. Isolated controller attempts use the configured per-role budgets instead: executorMaxAttempts=3, fixerMaxAttempts=6, maxAttempts=9 per work item. API/setup interruptions do not consume code-repair budgets. The first code defect or execution limit transfers to the configured fixer immediately; additional corrections stay with that role. Never reset counters on handoff; stop at the repair/total limit and await a user decision.
- 3 test runs in a row give no readable result;
- 12 work-phase test runs in a row in the same test scope are not green (initial baseline excluded);
- 60 test runs since start/resume, including baselines and scoped runs. Baseline build failures still count toward the global no-result limit. A green full run resets all scope failure streaks. Do not rename scopes to evade guards.

### Executor (subagent)
- Read the file before editing.
- Fill ONLY the function bodies.
- Never change signatures, imports, or the skeleton structure.
- Never edit tests or files other than the source file and the exact progress file assigned to this attempt below. If a test looks wrong or an import is missing, say so in the report.
- No shell. Report briefly: what changed, what is left.

## Complex projects (many modules)
1. Plan first: split the task into modules and write the checklist to the work plan resolved below. Resolve approval as described in Task intake before writing code.
2. Interfaces first: for each module list its public functions/classes and its dependencies. Modules must fit together.
3. Sequential by default: skeleton → requirement and edge-case tests → baseline → delegate small complete classes → evidence-based review → green module tests → mark done. With an explicitly configured concurrency above one, use the isolated controller protocol below for independent modules. Never remove the legacy guard to run several editors in the main checkout.
4. Track progress in that work plan (`- [ ]` / `- [x]`). Read it at session start, update it after each module.
5. Never pass more than one module's context to a single executor call.
6. Done means green per module; the project is done when all modules and the unfiltered full suite are green.
7. After approval of the whole plan, autonomously choose the next unfinished module whose dependencies are ready. Explain the order in the plan. After review and passing tests, update the plan and continue without requiring the user to name modules or issue `/module` for each one. Ask only for missing access/tools or decisions that change the approved scope.
8. Keep one task metrics ID for the entire approved task. Finalize statistics after all planned modules are complete, not after each module. A request for just one module remains scoped to that module.

## Rules
- One subagent — one small complete class or cohesive source file; a function is appropriate for an isolated correction or a justified split.
- Keep the Master Chief for planning, architecture, marketing, and review. Routine code goes to the selected executor.
- Code, comments, and identifiers: English. Human-facing docs: Russian is fine.

## Isolated workers and bounded correction

This section refines the sequential snapshot protocol only for attempts created
by `kit\python.cmd -m kit.execution_controller`. The ordinary delegate/subagent path stays
sequential. Setting a number in the configurator does not isolate direct edits.

- Freeze applicable public contracts first: interfaces, `.h`/`.hpp`, shared types,
  API/database formats, units, errors, ownership and threading rules. Record each
  module's dependencies. Publish the complete named function plan before workers start.
- Read the selected policy and models. Launch each ready work item with
  `kit\python.cmd -m kit.execution_controller --task <ID> launch --work-item <item> --file <file> --requirements .metrics/<ID>/<item>-requirements.json --contracts <shared-contract-file> --dependencies <accepted-item> ...`.
  Omit dependencies when none. The controller registers the delegation, copies a
  plain isolated source snapshot, creates the exact child session with restricted
  file permissions, and verifies its bounded watcher is ready before admitting
  model input. This requires the shared Desktop service; never rebind a private
  standalone session. Do not also call a subagent for
  that same attempt. Its exact session/worker/attempt identities go into the journal.
- The controller owns `.metrics/<ID>/workspaces/`; workers never edit the main
  project. Their prompts authorize one exact source file and one progress file.
  Shared contracts remain read-only. Do not edit a contract while dependent work
  is active. No file-by-file merging by executors.
- Before inspection require an `attempt_end` with `stopped: true`. Read/inspect
  the attempt's workspace, add review tests there if needed, and run the wrapper
  with `--attempt <delegation-ID> --scope <item>`. Root tests or another attempt's
  green result cannot satisfy acceptance. Review evidence remains task-local.
- After accepted review run `kit\python.cmd -m kit.execution_controller --task <ID> integrate --attempt <ID>`.
  It checks original source/shared-contract hashes and applies one accepted file
  sequentially. A conflicting main file is a decision to rebase/review, not a
  reason to overwrite user work. Run final unfiltered tests on the integrated root.
- A selected Bug Fixer has its own model/API and a separate bounded correction budget. After a
  reviewed code defect use the same launch command with `--role bug_fixer
  --previous <rejected-attempt-ID>`, preserving the frozen requirements/contracts.
  A watchdog step/repetition/deadline signal can trigger the handoff after
  confirmed interruption and rework. Read events before dispatching a duplicate.
- Do not escalate API errors, 429, setup errors, pause or cancel to a different
  model. Missing progress alone is not a loop. Never inspect private reasoning.
  If stop is unconfirmed, block replacement. The fixer cannot delegate back.
  Global STOP guards remain in force; do not reset them automatically. Further
  fixer corrections use the failed fixer's ID as --previous, with remaining
  fixer/total budget. Never retry a predecessor that already has a successor.
- Canonical role text is in `kit/prompts/*.md`; `prepare` loads only the four
  named role documents. Russian human explanations live in `kit/prompts/README.ru.md`.
  HTML comments inside a prompt are still visible to a model.

## Kit utilities (independent of the project's language)
Before using a local executor, select an already loaded LM Studio instance. Start OpenCode through `kit\python.cmd kit/run_opencode.py`. At task startup inspect the launcher environment: `OPENCODE_KIT_ROOT`, `OPENCODE_KIT_INSTANCE`, and `OPENCODE_KIT_SERVER_MODE`. If the root matches this project and the mode is `standalone`, the launcher selected the instance and wrote the overlay before this private server started. Verify the loaded instance and connection with `check_env.py`; do not run `--reload` or restart that session. Reloading the background service does not reload a private server. For an existing desktop/background-service session without these launch facts, run `kit\python.cmd kit/run_opencode.py --prepare-only --reload` before the first executor call. See LOCAL_MODELS.ru.md. Never load/unload a model or change its load settings automatically. If selection is ambiguous, show the loaded instance IDs and ask the user to choose; if none is loaded, ask them to load one. Both executor roles use the selected instance. Rerun preparation before a new task after the user changes the loaded model. If `OPENCODE_KIT_EXECUTORS` is `opencode` or `api`, the executors use a model that OpenCode already knows (for example a model connected with `/connect`) or an own API chosen in `.opencode/kit-models.json`: skip the LM Studio checks and do not ask the user to load a model.

These tools live in `kit/` and use the pinned version from `kit/runtime/python.lock`.
Run from the project root with `.\kit\python.cmd` on Windows, or `sh kit/python.sh`
on Debian/Ubuntu/Mint. Replace `kit\python.cmd` in examples with `sh kit/python.sh`
on Linux. The native bootstrap works without an existing Python installation,
downloads only the locked version, verifies SHA256 and prepares a private runtime.
Never use `py`, a generic `python`/`python3`, or install another Python for kit commands.
Child processes must use `sys.executable`, which inherits this exact runtime.
For a Python application, provide mouse launchers that invoke this wrapper; do not
require the user to install Python or rely on PATH. Install application dependencies
in a project virtual environment created with this runtime, never in the shared
runtime. Pin them in the application's requirements/lock file. Other application
languages still require their own documented runtime or packaged distribution.
See docs/PYTHON_RUNTIME.ru.md for bootstrap architecture and supported systems.
- `kit/find_vault.py` — locate the Obsidian vault and the work plan: `kit\python.cmd kit/find_vault.py`
- `kit/check_env.py` — check `opencode.jsonc` and the LM Studio connection: `kit\python.cmd kit/check_env.py`
- `kit/pipeline_smoke.py` — offline smoke test of the Master Chief → executor flow: `kit\python.cmd kit/pipeline_smoke.py`
- Kit tests: `kit\python.cmd -m unittest discover -s kit/tests -v`
- Task metrics: `kit\python.cmd kit/task_metrics.py --help`; protocol below and details in `METRICS.ru.md`.

## Task metrics
- Publish dashboard architecture and the function registry before delegation: write `ARCHITECTURE.md` and a JSON array with `id`, `name`, project-relative `file`, and `work_item` for every planned function. Run `kit\python.cmd -m kit.dashboard.tracking --task <ID> --architecture ARCHITECTURE.md --functions .metrics/<ID>/functions.json`. The kit stores an immutable document snapshot per revision; do not publish while an executor attempt awaits review. Existing function IDs must keep their identity; additions receive new IDs. A missing registry means an unknown total, not zero.
- After `delegate`, use its actual event ID to assign the executor exactly one auxiliary file `.metrics/<ID>/progress/<delegation_id>.json` plus the function IDs for this work item. Create its parent directory before the call. In the executor prompt explicitly authorize this one file and give the current Unix time. Via its file tool, the executor reports `{ "delegation_id": "<actual-id>", "implemented_ids": ["<function-id>"], "current_id": "<function-id-or-null>", "updated_at": 1234567890 }` before work and after completing a function. Use `null` (not the string) when finished. No shell, metrics journal edits, other progress files or tests. If no fresh time is available, keep the supplied time; the dashboard expires current-function claims after 90 seconds. Reported implementation is provisional; only an accepted work-item review marks its functions accepted. A rework clears completion from the rejected attempt. Do not fabricate progress records retroactively for completed tasks.
- The dashboard's Settings button starts the existing project-local configurator, without saving or applying settings automatically. Actual session models come from OpenCode exports; configured choices are labeled as such. Settings affect preparation for the next task/server; an existing session is not silently reloaded.
- Honor dashboard task controls in `.metrics/.task-controls/<ID>.json`. Pausing/paused/cancelling/cancelled/deleting/error block new execution; do not bypass them by starting another ID. A user pause interrupts the root and its descendant sessions. Resume uses the same task and requires inspection of partial edits before proceeding; it does not reset protective loop guards. Cancel is not successful completion. See `kit/dashboard/CONTROLS.ru.md`.
- At completion, provide a usable launch file in the project. Conventional root names (`run.ps1`, `start.ps1`, `run.sh`, `start.sh`, `run.cmd`, `start.cmd`, `run.bat`, `start.bat`, `run.py`, `start.py`) are discovered automatically. For a different file, write `{ "launcher": "tools/start.py" }` to `.metrics/<ID>/progress/result.json` before finish, creating its parent if needed. Only a real project-relative script is accepted. The dashboard opens the project folder and provides a read-only launch-file viewer; it never executes the script automatically. Token details use the frozen finish usage snapshot, or completed-message exports while work continues; missing usage stays unknown.
- In a project with `opencode.jsonc` and `kit/`, the CLI `start` automatically starts/reuses the local dashboard and opens that task. The user does not run dashboard commands. Read the returned `dashboard` status: `ready` confirms the server, and `opened` confirms the browser request. Report an unavailable dashboard or a failed browser opening with the returned address/error. The journal remains saved; never repeat `start` with the same ID to retry the viewer. Use `kit\python.cmd -m kit.dashboard.launcher --task <ID>` to retry viewing. `--no-dashboard`, `--no-browser`, and `OPENCODE_KIT_DASHBOARD=off` are for tests/headless diagnostics, not the normal local user workflow. The viewer does not prepare models or reload OpenCode.
- For each implementation task, choose a unique ASCII task ID and run `kit\python.cmd kit/task_metrics.py start --task <ID> --session <current-session-ID> --title "<task title>"` as soon as the actual session ID is known, before environment setup, planning work and implementation. Add `--track-delegations` for implementation tasks. Keep this ID in the work plan. Do not reuse a finished task ID.
- Use the actual OpenCode session ID from context. If unavailable, inspect `opencode session list --format json` and match the current project and task; never guess or pick the latest automatically. If still unknown, omit `--session` and report missing token data.
- Before each executor call register it with `delegate` as described above. The script reports registered attempts without a matching review. It cannot detect calls that bypass this protocol.
- After each code review, run `kit\python.cmd kit/task_metrics.py review --task <ID> --work-item <function-or-class> --result accepted` with `--checks <path>` for acceptance, or `--result rework`. One return for corrections is one rework, regardless of the number of comments.
- For isolated API/setup interruptions, record `review --result blocked` after a confirmed infrastructure attempt_end; partial source is allowed and retained. Explicit continuation uses the same role and `--previous <attempt-ID>` after the blocker is resolved. Never reclassify a code failure as blocked. For legacy sequential attempts, if the executor returned no work and changed no files (an error, a rate limit, an unavailable model), record `--result failed` instead: it is not a rework, and the runner refuses it when files changed. Then follow Task intake: report the blocker to the user instead of retrying an unavailable executor or implementing the work item yourself.
- Before the first implementation step of every task, run the test command once through `kit\python.cmd kit/task_metrics.py check [--junit <file> | --junit-dir <folder>] -- <test command>`. Exit code 0 means the runner can read the results (failing tests are fine at this point). Exit code 4 means it cannot: do not write code; show the user the hints and ask them to fix the setup.
- During work use a documented work-item/module test filter and stable `--scope <work_item-or-module>`; store reports inside generated directories. Once per scope before delegation, an initial red run may use `--phase baseline`. At completion run the unfiltered project command with `--scope full`.
- Run the project's test command through `kit\python.cmd kit/task_metrics.py test --task <ID> [--junit <file> | --junit-dir <folder>] -- <test command>`, using the **Project stack** tool and a filter for the current scope; the final full run uses the unfiltered command. React to its exit code as described in **Review loop and stop rules**.
- The runner recognizes unittest summaries and JUnit XML. `--junit <file>`: one report file; it must not exist before the run, so use a new name for every run (run-01.xml, run-02.xml, ...). `--junit-dir <folder>`: a folder where the tool writes one file per test class or project (Maven `target/surefire-reports`, Gradle `build/test-results/test`); only files written during the run are read. Unknown output, zero tests and skipped tests do not count as fully successful.
- Do not claim completion with pending delegated attempts or a missing/failing full suite. Resolve the warning first.
- At the end, after all executors have returned, run `kit\python.cmd kit/task_metrics.py finish --task <ID>`. Insert its Markdown statistics in the final answer. If another agent writes the final answer, give it `.metrics/<ID>/report.md`; it must not invent or recompute counters.
- All `lmstudio` providers are local/free of API fees; `openrouter` models ending in `:free` and `opencode` models ending in `-free` are free cloud models; every other known provider is paid by default. Missing usage must remain unknown. Token counts are a snapshot before the final answer, not a billing statement.
- These commands are required for ordinary text requests too, not only `/module`. Logging is instruction-driven, not an automatic plugin. Planning-only tasks may have no tests; never describe that as a successful test run.

## Project stack  # EDIT: language, build tool, test command
> The only language-specific part of the kit. Replace the example below for your language.
> The test command must give the runner a readable result: Python unittest output, or JUnit XML
> through `--junit` / `--junit-dir`. Check it once with `kit\python.cmd kit/task_metrics.py check ...`.
> Examples (see the table "Подключение своего языка" in README.md for more):
> - Python unittest: `kit\python.cmd kit/task_metrics.py test --task <ID> -- kit\python.cmd -m unittest discover -s tests -v`
> - Java, Maven: `kit\python.cmd kit/task_metrics.py test --task <ID> --junit-dir target/surefire-reports -- mvn -q test`
> - C#: `kit\python.cmd kit/task_metrics.py test --task <ID> --junit .metrics/<ID>/run-NN.xml -- dotnet test --results-directory .metrics/<ID> --logger "junit;LogFileName=run-NN.xml"`
>   (needs the NuGet package `JunitXml.TestLogger` in the test project)

## Project layout  # EDIT: folders and files of this project
- `app/` — application code.
- `tests/` — unit tests of the project (separate dependent project).
- `kit/` — the kit's own tools and their tests (do not mix with project code).
- `.vscode/` — editor settings.

## Work plan (memory)  # EDIT: plan file name
- Plan file name: `currentsteps.md`.
- Locate the vault: run `kit\python.cmd kit/find_vault.py --no-scan` (fast) or `kit\python.cmd kit/find_vault.py` (with filesystem scan).
  - If it prints a vault: keep the plan at `<vault>/currentsteps.md` (create it if missing).
  - If no vault is found: use `currentsteps.md` in the project root.
- This section is the single source of truth for the plan location; agent prompts and commands must refer here rather than hard-code another note.
- If several vaults are found, use the project's explicitly selected vault; otherwise ask which vault to use before writing.
- Read the plan at the start of a session and update the same resolved file after major steps. Existing knowledge-base notes are background/history, not alternative active plans.

## Source snapshot boundaries
`delegate` reads all project files except generated directories `.git`, `.metrics`, `__pycache__`, `.venv`, `node_modules`, `target`, `build`, `dist`, `bin`, `obj`. Do not store application source in excluded directories. Symlinks/junctions outside excluded directories cause an error instead of being followed. Keep review evidence and transient logs in `.metrics/`; do not edit unrelated files before inspect. After inspect, the Master Chief may add requirement tests; all changes after the latest green test require another run before acceptance.
