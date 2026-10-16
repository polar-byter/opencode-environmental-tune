# OpenCode: the Master Chief and executors

**First setup without manual copying:** install [OpenCode Desktop](https://opencode.ai/download)
and [Python with Tk](https://www.python.org/downloads/windows/), download and extract
this repository's ZIP, then double-click **install.cmd**. The wizard creates your
project folder, installs the kit, opens model/API settings, and launches Desktop
with a request to open the project. Follow the [beginner guide and sample prompt](OPENCODE_KIT.en.md)
for each step, model roles, and the manual folder-selection fallback.
[Installer architecture with diagrams (Russian)](docs/INSTALLER.ru.md).

The configurator includes an optional Bug Fixer role, worker concurrency and
bounded execution limits. New template defaults: OpenCode DeepSeek V4.1 Flash Free
for the Chief/fixer and MiMo V2.6 Flash Free for executors; concurrency defaults to one.
The controller isolates each attempt, binds tests and usage to its exact session,
and permits one correction handoff after a code defect or an execution limit.
API/429, setup failures and cancellation never trigger an automatic model switch.
Existing saved choices and sequential journals remain readable.

See the [developer guide with diagrams (Russian)](docs/EXECUTION_GUIDE.ru.md) and
[readable role prompts](kit/prompts/README.ru.md).

> Русская версия: [README.md](README.md) · Step-by-step start: [QUICKSTART.en.md](QUICKSTART.en.md) · [Быстрый старт (RU)](QUICKSTART.ru.md)

You describe a task in OpenCode. The main agent `build`, which we call the Master Chief, organizes the work: it makes a plan, hands implementation to the chosen executors, reviews the code and runs the tests. At the end it shows the result and the task statistics.

This repository contains the settings for that way of working. You can add them to your own project, for example a Java application. The Master Chief is responsible for decisions and review. Executors carry out small jobs through LM Studio, models connected in OpenCode, or your own OpenAI-compatible API.

**In short, it is like a building site.** The Master Chief is the foreman: it reads
the order, draws the plan, hands out work and accepts the result. Executors are the
workers: they carry out small, clear jobs exactly as drawn. A tracking journal records
every step, and a browser dashboard shows what is happening right now. Your part is to
say what you need, answer questions and accept the result.

## How it works — in five diagrams

The diagrams are animated; their data is sample data. A detailed guide with the
same diagrams is in the [quick start](QUICKSTART.en.md).

### 1. The Master Chief reads the documents and prepares a plan

When it gets a task, the Master Chief first gets oriented: it reads your requirements
(a chat message or a `TASK.md` file), the kit rules (`AGENTS.md`), the plan from
earlier sessions (`currentsteps.md`) and what already exists in the project. Then it
decides which parts the program needs and in what order. For each part it writes a
blank: function names and a detailed description of what each one must do. It writes
the tests right away — automatic checks. While the functions are empty the tests are
"red", and that is expected: they are waiting for the work to be done.

![How the Master Chief plans](readme_gif/en/01_master_chief_planning.gif)

### 2. The executor does the work, the Master Chief checks it

Before each job the Master Chief writes down the list of requirements and takes a
"snapshot" of all files. The executor gets one file and fills in the empty functions.
The script immediately compares the files with the snapshot: if anything else was
touched, the work goes back. Then the Master Chief checks every requirement against
the code and tests: something missing means a rework, everything right means the work
is accepted and the dashboard's count of finished functions grows. If the same job
keeps coming back, a `STOP` guard fires and the Master Chief waits for your decision,
so there is no endless loop.

![Handing off to the executor, review and the dashboard](readme_gif/en/02_delegation_review_dashboard.gif)

### 3. Preparing a project and giving a task

Once, you copy four things from this repository into your project and state in
`AGENTS.md` how to run the tests. Then, in the settings window, you choose models for
the Master Chief and the executors. You can give a task in two ways: write it straight
into chat, or fill in a `TASK.md` file and send one word, "Start". If they disagree,
the chat message wins. The Master Chief finds the other documents itself.

![Setting up a project for a new task](readme_gif/en/03_project_setup.gif)

### 4. Where models come from: LM Studio and OpenRouter

**LM Studio** runs a model on your own computer: free and offline, but it needs a
strong graphics card. You load the model yourself; the kit only uses it.
**OpenRouter** is a catalog of cloud models, including free ones (the name ends with
`:free`). In the settings window you can filter models for coding, click the one you
want and it fills in the chosen role. The key lives in a Windows user variable; if it
is already saved the window says "Key found", and "Check connection" confirms the
service accepted it.

![LM Studio and OpenRouter](readme_gif/en/04_lmstudio_openrouter.gif)

### 5. The dashboard: watch and control

The dashboard opens by itself when the Master Chief starts a task. It shows who is
working on what, how many parts are done, how often work was sent back, token usage
and every executor job. Buttons let you **pause** the task (everything is kept),
**resume** it, **stop** it (cancel) or **delete** the task journal — your application
code stays. At the end a summary appears with links to the project folder, the launch
file and the report. The dashboard supports English and Russian, initially follows
the browser language, and saves a manual Language selection for the project.

![Using the dashboard](readme_gif/en/05_dashboard_controls.gif)

Diagram files and how to rebuild them: [readme_gif/README.md](readme_gif/README.md).

## How to use it

You can write the requirements straight into chat, or save them in `TASK.md` and send
a short "Start". The file is optional when the task is already in chat. Your current
instructions take priority. The Master Chief reads the kit rules, the plan and other
needed documents itself; you do not have to list them.

After connecting the settings, open the project in OpenCode and describe what you
want. If the executors use LM Studio, the model must be loaded and its server running;
other executor sources do not need that. The Master Chief prepares the selected models
as described in AGENTS.md. `run_opencode.py` remains the configuration preparer and an
alternative way to launch OpenCode; an already open Desktop uses the preparation mode.
For example:

> Add expense tracking: amount, category and date. Negative amounts are not allowed. Show me the plan first.

The Master Chief proposes a solution. You discuss the requirements and approve the
plan. After that it assigns jobs, calls the needed scripts and checks the result. If
it lacks information or access, it explains what it needs from you.

Your role is to set the task, decide how the application should behave and judge the
result. Managing executors, recording reviews, running tests and collecting statistics
are the Master Chief's job.

In the dashboard you can pause the task with all its executors, resume it, cancel it,
or delete its sessions and metrics while keeping the source code.
Semantics and limits: [task controls](kit/dashboard/CONTROLS.ru.md) (Russian).

For the first setup there is a [quick start](QUICKSTART.en.md) ([Russian version](QUICKSTART.ru.md)).
Installing tools and setting up access are done once per computer; you do not repeat
them before each task.

To repeat our experiment from Desktop there is a [short guide](DESKTOP_EXPERIMENT.ru.md) (Russian).
Own API, the OpenRouter catalog with prices, role and language choice are described in
the [configurator guide](kit/configurator/UX.ru.md) (Russian).

## What the Master Chief does during the work

The Master Chief splits the task into small pieces so the local executor gets a clear
job. Usually one job is a small complete class: constructor and related methods. A
single function is handed out for a targeted fix or when a class is too large.

1. Reads the project plan and current code, clarifies requirements.
2. Opens task tracking so its statistics do not mix with earlier work. The start
   command automatically launches the project dashboard and opens this task's page.
3. Creates the code skeleton and writes tests. Until the functions are implemented,
   these tests are expected to fail.
4. Hands the executor a small class or related file with requirements written down in advance.
5. Reviews the returned code. If fixes are needed, records a rework and gives the
   executor a new job.
6. Runs tests through the tracking script and checks the results. Keeps working until
   the required checks pass.
7. Updates the plan, collects statistics and shows the outcome.

These steps are written into the agent's instructions. The full cycle was tested on
two Spring tic-tac-toe implementations. The repeat run passed 85 tests and 27 external
HTTP scenarios; token savings were not confirmed in it.

## What you get at the end

During the work the local dashboard shows task status, events, test runs, reworks and
executor failures. The page refreshes every 2 seconds; you can pick another task of
this project and open the final report. The server is reused between tasks. Details:
[dashboard](kit/dashboard/README.ru.md) (Russian). The dashboard shows the
architecture, the actual models, handoffs to executors, the current function, reported
and accepted progress, work details and available tokens during the task. The model
settings button opens the project's model configurator. After completion you see the
summary, a link to the folder and a launch-file viewer. Function progress needs a
published registry and executor messages; missing data and tokens are never replaced
with zeros.

The Master Chief explains what was done, which checks passed and what remains open.
A separate block shows:

- task time;
- tokens of paid models;
- tokens of free / local models — everything running through `lmstudio`;
- tokens of free cloud models — OpenRouter models ending in `:free`;
- the number of code reworks after review;
- how many full test runs succeeded and how the last one ended.

Tokens are units of text a model receives and generates. They help you see how work
was split between models. The script does not compute money cost or savings yet.

## How the Master Chief collects statistics

The Master Chief calls `kit/task_metrics.py` at the right moments itself. This is part
of its orchestration. In a normal task you do not type these commands.

1. **Task start.** The Master Chief passes the time and session ID (the current
   OpenCode conversation) to the script. This separates the new task from earlier work.
2. **Review.** After checking code, the Master Chief records whether it was accepted or
   sent back. One return counts as one rework, however many remarks it has.
3. **Tests.** The Master Chief runs them through the script, which saves the real
   command result. "3 of 5 green runs" means three successful test commands out of
   five. It also says how many runs covered the full suite and how many a selected
   class or module. An empty suite or skipped tests never count as full success.
4. **Tokens.** Before the final answer the Master Chief has the script read messages
   of the main and child OpenCode sessions. It picks completed messages within the task
   time and sums their counters per model.
5. **Model groups.** Every `lmstudio` model goes into the local group, OpenRouter models
   ending in `:free` and OpenCode models ending in `-free` into the free cloud group, other known providers into the paid
   group by default. New LM Studio models are counted without a manual list.
6. **Report.** The script saves `.metrics/<task ID>/report.md`. The Master Chief puts it
   into the final answer. If a planner writes the answer, it uses the same file.

If OpenCode returns no data, the report says "no data". Time includes waiting for your
answers, and tokens of messages after the report is built are not counted yet. Details
and debug commands: [statistics guide](METRICS.ru.md) (Russian).

## Continuing after a break

The Master Chief keeps `currentsteps.md`: completed steps, decisions and next tasks.
In a new conversation you can ask:

> Read the project plan and continue with the next task.

The Master Chief finds the plan by the rule in `AGENTS.md`. By default it lives in the
selected Obsidian vault, or in the project root without Obsidian.

## If something stops working

Start by describing the problem to the Master Chief. For example:

> The local executor stopped responding. Check the settings and the LM Studio connection and show the cause.

The Master Chief can read the config, run the connection check and a small example for
the local model. If the problem needs your action — for example loading a model in
LM Studio — it explains what to do. Diagnostic commands are for the agent and manual
debugging; you do not need to run them all before each task.

## Versions and updates

Data collection was tested on **OpenCode CLI 2.0.21** and **Python 3.13** on
October 3, 2026. The CLI is the OpenCode the script calls from a terminal; it must see
the same sessions you work with in Desktop. Model selection through
`.opencode/kit-models.json` was tested on **OpenCode 2.0.26** on October 10, 2026 by
exporting real sessions: the Master Chief via the top-level `model` key of the overlay,
executors via `agents.executor` and `agents.executor-fast`.

### Which OpenCode the kit uses

One computer often has several OpenCode installs: the Desktop app with its own CLI
inside and separately installed commands, e.g. via npm. Their versions can differ a lot.
An old CLI does not understand the settings the kit writes: it rejects the `providers`
and `agents` keys or silently keeps the old models for agents.

All kit scripts — launch, `--prepare-only`, the model settings window and statistics —
look for OpenCode in the same order (`kit/opencode_cli.py`):

1. The path or command from `--opencode`, if you gave one.
2. The CLI inside OpenCode Desktop: `%LOCALAPPDATA%\Programs\@opencodedesktop\resources\opencode-cli.exe`.
   You work in Desktop, so this CLI sees the same sessions and matches the version of
   the app that reads the settings.
3. The `opencode` command from `PATH` — for Linux, macOS and computers without Desktop.

`.cmd`/`.bat` wrappers (how npm installs commands) are not used for launching: they can
mangle arguments and often lead to another, older version. Only statistics use such a
wrapper as a last resort; it is enough for reading sessions.

How to set it up:

1. Check which OpenCode installs you have and their versions:

   ```powershell
   Get-Command opencode*
   & "$env:LOCALAPPDATA\Programs\@opencodedesktop\resources\opencode-cli.exe" --version
   ```

2. If Desktop is installed, the kit takes its CLI even when another `opencode` is on
   `PATH`. It is better to update or remove the old `PATH` command so you do not run it
   by mistake. Commands with other names (e.g. `opencode2`) are never called by the kit.
3. To use a specific CLI, pass the path explicitly:
   `py kit/run_opencode.py --opencode "C:\path\opencode-cli.exe"`, and for statistics
   `task_metrics.py finish --opencode ...`.
4. After changing models, check that OpenCode accepted them. `debug agents` is not
   enough: it shows agent models, while the main session runs on the top-level `model`
   key. A reliable check is a short real session and the model from its export:

   ```powershell
   $cli = "$env:LOCALAPPDATA\Programs\@opencodedesktop\resources\opencode-cli.exe"
   $out = py kit/run_opencode.py -- run --format json "Reply with the single word OK." | Out-String
   $session = [regex]::Match($out, '"sessionID":"(ses_[A-Za-z0-9]+)"').Groups[1].Value
   (& $cli session export $session | ConvertFrom-Json).messages.model | Select-Object -Unique providerID, id
   ```

   It should show the Master Chief's model. The executor model appears in the child
   session export after the first executor job. A config error means the CLI is too old.

After an update, ask the Master Chief to check compatibility:

> OpenCode was updated. Check the version, session access and statistics on a small task.

The Master Chief should check the available commands, run the kit tests and compare the
report with the message export. If the format changed, it shows which part of data
reading needs fixing. We mark a new version as verified after such a run.

## Where the settings live

Useful for the first setup or if you want to change how the system works.

| File | Responsible for |
|---|---|
| `opencode.jsonc` | Models, connections and agent permissions |
| `AGENTS.md` | Workflow, application test command and plan location |
| `.opencode/commands/` | Optional `/plan-project` and `/module` prompt templates |
| `kit/` | Scripts the Master Chief calls, and their tests |
| `.metrics/` | Task journals and reports; not pushed to Git |

`build` currently uses `opencode-go/deepseek-v4.1-flash`. When launched through
`kit/run_opencode.py`, both executors use the already loaded LM Studio instance. With
several models the script picks the loaded model from the `executor` setting or asks for
an ID. Launching OpenCode directly without preparation uses the fixed aliases from the
original config. Details, including launching in an already open app:
[model selection](LOCAL_MODELS.ru.md) (Russian). The `/plan-project` command also calls `build`.

For another project, copy the kit files and set its language, folders and test command
in `AGENTS.md`. Step-by-step setup is in the quick start. After that you can give tasks
in plain text.

## Adding your language

The kit fits any language, but the statistics script must **read the test results**:
how many there were and how many failed. It understands two formats:

- the Python `unittest` summary line;
- **JUnit XML** — a common test report format that almost every build system can produce.

If the result cannot be read, failed tests still count as failed, but green ones get the
status "unknown", and the Master Chief treats the run as a setup problem. So write the
test command in the `Project stack` section of `AGENTS.md` together with the report flags.

| Language | Install once | Test command for `Project stack` |
| --- | --- | --- |
| Python (unittest) | nothing | `py kit/task_metrics.py test --task <ID> -- py -m unittest discover -s tests -v` |
| Python (pytest) | `pip install pytest` | `py kit/task_metrics.py test --task <ID> --junit .metrics/<ID>/run-NN.xml -- py -m pytest --junitxml=.metrics/<ID>/run-NN.xml` |
| Java, Kotlin (Maven) | nothing | `py kit/task_metrics.py test --task <ID> --junit-dir target/surefire-reports -- mvn -q test` |
| Java, Kotlin (Gradle) | nothing | `py kit/task_metrics.py test --task <ID> --junit-dir build/test-results/test -- gradlew test` (macOS and Linux: `./gradlew test`) |
| C# (.NET) | `dotnet add <TestProject> package JunitXml.TestLogger` | `py kit/task_metrics.py test --task <ID> --junit .metrics/<ID>/run-NN.xml -- dotnet test --results-directory .metrics/<ID> --logger "junit;LogFileName=run-NN.xml"` |
| JS, TS, React, Vue (Vitest) | nothing | `py kit/task_metrics.py test --task <ID> --junit .metrics/<ID>/run-NN.xml -- npx vitest run --reporter=junit --outputFile=.metrics/<ID>/run-NN.xml` |
| JS, TS, React (Jest) | `npm i -D jest-junit cross-env` | `py kit/task_metrics.py test --task <ID> --junit .metrics/<ID>/run-NN.xml -- npx cross-env JEST_JUNIT_OUTPUT_FILE=.metrics/<ID>/run-NN.xml jest --ci --reporters=default --reporters=jest-junit` |
| Go | `go install gotest.tools/gotestsum@latest` | `py kit/task_metrics.py test --task <ID> --junit .metrics/<ID>/run-NN.xml -- gotestsum --junitfile .metrics/<ID>/run-NN.xml` |
| Rust | `cargo install cargo-nextest` and a profile with `junit` in `.config/nextest.toml` | `py kit/task_metrics.py test --task <ID> --junit-dir target/nextest -- cargo nextest run` |
| PHP (PHPUnit) | nothing | `py kit/task_metrics.py test --task <ID> --junit .metrics/<ID>/run-NN.xml -- vendor/bin/phpunit --log-junit .metrics/<ID>/run-NN.xml` |

Rules not to break:

1. **`--junit <file>`** — for tools that write one file. The file must not exist before
   the run, so the Master Chief numbers runs: `run-01.xml`, `run-02.xml` and so on.
   `AGENTS.md` says `run-NN`; the Master Chief fills in the number.
2. **`--junit-dir <folder>`** — for tools that write a file per class or project: Maven,
   Gradle, several .NET test projects (use `LogFilePath=<folder>/{assembly}.xml` in the
   logger). The script reads only files from this run.
3. **No watch mode.** Jest and Vitest wait for file changes by default and never exit.
   Use `vitest run` and `jest --ci`, or the run ends on a timeout.
4. **Windows and `.cmd`.** The script finds `npx`, `npm`, `mvn`, `gradlew` itself; no
   need to add `.cmd`.

After writing the command, check it once:

```bash
py kit/task_metrics.py check <same report flags> -- <same test command>
```

`CHECK OK` — ready to work. `CHECK FAILED` — hints appear below the line. Details:
`METRICS.ru.md`, section 3 (Russian).

## What changed after real testing

On tic-tac-toe the setup completed every module and collected statistics, but the first
review missed a null bug. Now the Master Chief saves the requirements before calling the
executor and, on acceptance, names the code location and test for each item. The script
refuses an incomplete check table and notices changes to other files, including new
files Git does not track yet.

During work the current class or module is tested. The initial red run is recorded
separately; failures of different modules do not add up to one limit. A full test suite
is required at the end. A small class is implemented in one call instead of one call per
short method.

You do not type these commands; the Master Chief runs them. A detailed null example and
the statistics explanation: [how executor review works](PIPELINE.ru.md) (Russian).

## License

[MIT](LICENSE).
