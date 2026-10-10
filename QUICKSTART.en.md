# Quick start (EN): OpenCode kit, example — Java / Spring Boot

> A from-scratch guide: how to plug this kit into your project and start working in OpenCode.
> Русская версия: [QUICKSTART.ru.md](QUICKSTART.ru.md)

---

## 1. What this is

This kit turns OpenCode into a **"Master Chief + executors"** setup:

- 🪖 **Master Chief** (`build`, cloud model) — plans the task, writes a **code skeleton with specs**, writes **tests**, and reviews the result.
- 🛠 **Executor** (`executor`, local LM Studio model) — fills in **method bodies only**, strictly following the specs. It touches nothing else.

The cycle is always the same:

```
you:  Build a task-list API. Show me the plan first.
Master Chief: proposes a plan and explains the module order
you:  The plan looks good. Implement the whole plan.
Master Chief: skeleton + specs + tests (tests are red for now — that is normal)
       └─ delegates to the executor, one method at a time
executor: fills in the body per spec
Master Chief: reviews code and tests → marks the module done → starts the next module
       at the end — results and statistics for the whole task
```

The example below is a **Java (Spring Boot)** project. The same flow works for any language — only the test command changes.

---

## 2. What you need

| What | Why | Check |
| --- | --- | --- |
| OpenCode | the agent itself | — |
| LM Studio | local executor model | `py kit/check_env.py` |
| Python 3.13 | **only** the kit's utilities | `py --version` (macOS, Linux: `python3 --version`) |
| JDK 21 | compile Java | `java -version` |
| Maven | build and test Java | `mvn -v` |

> Python is needed by the kit (Obsidian lookup and checks), not by your Java project.
>
> Commands in this guide are written for Windows, where Python starts with `py`. On macOS and Linux use `python3` instead of `py`. The Master Chief learns this from `AGENTS.md` and picks the right command itself.

In LM Studio you must **load a model** (the **Load** button) and start the server: **Developer → Start Server**.

---

## 3. Step 1. Create a Java project

1. Open [start.spring.io](https://start.spring.io)
2. Fill in:
   - **Project:** Maven
   - **Language:** Java
   - **Spring Boot:** latest stable 3.x
   - **Java:** 21
   - **Dependencies:** `Spring Web`, `Validation`
3. Click **Generate** → a zip downloads.
4. Unzip it, e.g. to `D:\PROJECTS\task-api`.

You get roughly:

```
task-api/
├── pom.xml
└── src/
    ├── main/java/com/example/taskapi/
    └── test/java/com/example/taskapi/
```

---

## 4. Step 2. Copy the kit into the project

Copy four things into the root of `task-api/`:

```
opencode.jsonc        ← agents and models
AGENTS.md             ← working rules
kit/                  ← utilities (Obsidian lookup, environment check)
.opencode/            ← commands /plan-project and /module
```

Your project root should end up like this:

```
task-api/
├── opencode.jsonc
├── AGENTS.md
├── kit/
├── .opencode/
├── pom.xml
└── src/
```

---

## 5. Step 3. Adapt `AGENTS.md` for Java

Open `AGENTS.md` and edit the **two sections** marked `# EDIT`.

**Section `Project stack`:**

```md
## Project stack  # EDIT: language, build tool, test command
- Language: Java 21 (`java -version`). Build tool: Maven (`mvn`).
- Tests: JUnit 5. Maven writes one JUnit XML file per test class into `target/surefire-reports`.
- Test command (always through task_metrics):
  `py kit/task_metrics.py test --task <ID> --junit-dir target/surefire-reports -- mvn -q test`
- Compile only: `mvn -q compile`.
- Run the app: `mvn spring-boot:run`.
```

**Section `Project layout`:**

```md
## Project layout  # EDIT: folders and files of this project
- `src/main/java/com/example/taskapi/` — application code.
- `src/test/java/com/example/taskapi/` — tests.
- `pom.xml` — Maven build file.
```

> Nothing else in `AGENTS.md` needs changing. The `/module` and `/plan-project` commands are already language-agnostic.

---

## 6. Step 4. Check the environment

This check confirms whether the Master Chief can reach the local executor. After opening the project, ask the Master Chief:

```text
Check the environment using kit/check_env.py. Read the result of the
trial model request and explain what needs configuring if it fails.
```

The Master Chief runs the check. The final `ready for use` line appears only when the config is valid, LM Studio responds and the trial model request succeeded. See **11. Troubleshooting** for possible issues.

### Check that statistics can read test results

The statistics script must understand how many tests passed and failed. Check it once yourself, in a terminal in the project root:

```bash
py kit/task_metrics.py check --junit-dir target/surefire-reports -- mvn -q test
```

- `CHECK OK` — everything is set up. Failing tests do not matter at this step.
- `CHECK FAILED` — the script cannot read the result. Hints follow: for example, Maven not found, the project does not build, or no reports were written.

Other languages need their own command — see the table "Подключение своего языка" in `README.md`. The Master Chief also runs this check before every task and does not write code until it passes.

---

## 7. Step 5. Start OpenCode

Load the model in LM Studio with your preferred settings and start its server. In a terminal in the **`task-api` folder** (where `opencode.jsonc` lives), run:

```powershell
py kit/run_opencode.py
```

The launcher connects both executors to the already loaded instance and opens OpenCode. If several models are loaded, it uses the configured executor when unambiguous or asks for an instance ID. For an open desktop session, the Master Chief can prepare the selection and reload the background service with `--prepare-only --reload`. Details: [loaded-model selection](LOCAL_MODELS.ru.md).

Make sure everything is visible:
- type `/` — you should see `/plan-project` and `/module`;
- ask: "Read the work plan" — the Master Chief finds Obsidian via `kit/find_vault.py` (or falls back to `currentsteps.md`).

---

## 8. Step 6. Plan the project

Type in the OpenCode chat:

```text
Build a task-list REST API on Spring Boot: create, list, complete, and
delete tasks. Keep data in memory for now.
Show me the plan first and explain the order of work.
```

The Master Chief first splits the task into modules and records the work plan. It writes no code before approval.

Example result:

```md
## Modules
- [ ] model      — Task + store
- [ ] service    — list / create / complete / delete
- [ ] controller — REST endpoints
```

The Master Chief chooses the modules and their order. Here, task data (`model`) comes first, operations on that data (`service`) come next, and HTTP endpoints (`controller`) depend on those operations. You do not need to know these names in advance.

Check that the plan matches your requirements, then reply: "The plan looks good. Implement the whole plan, verify it, and show task statistics."

---

## 9. Step 7. The Master Chief implements the approved plan

After approval, the Master Chief starts the first module according to the dependencies in the plan. You do not need to choose or start each module separately.

What happens automatically:

1. The Master Chief creates a **method skeleton** with Javadoc specs and a placeholder:
   ```java
   public Task create(String title) {
       throw new UnsupportedOperationException("TODO: executor");
   }
   ```
2. The Master Chief creates **tests** `TaskServiceTest.java` and runs them through `kit/task_metrics.py` — they are **red** (that is expected).
3. The Master Chief asks the **executor** to fill the method body per spec.
4. The executor fills **only the body**.
5. The Master Chief reviews the code and runs tests again. A failing test goes back to the executor as a rework. A build or setup problem is fixed by the Master Chief or brought to you; the executor is not asked to fix it. After successful verification the Master Chief marks the module complete and starts the next module whose dependencies are ready.
6. If one piece has been sent back 3 times, or 3 test runs in a row gave no result, the statistics script stops the task (`STOP`). The Master Chief explains what happened and waits for your decision: clarify the spec, fix the tests, or fix the setup. This way the test-and-rework loop cannot run forever.

The Master Chief continues until the approved plan is complete. It asks for your input when access or tools are missing, or when a decision would change the task. Ordinary module transitions need no further approval.

You can request the whole project in one task. The Master Chief splits it into small executor assignments. `/module` remains useful when you want to limit a task to one module.

---

## 10. Step 8. Verify and run

The Master Chief checks that the modules work together and explains the result. A separate section contains statistics from `kit/task_metrics.py`: tokens for LM Studio and other providers, code returns for rework, and fully successful test runs. Statistics cover the whole task.

To check the running API, ask:

```text
Start the application and check creating, listing, completing, and
deleting a task through the API. Show the results and explain how
to stop the application.
```

The Master Chief starts the application and sends the requests. It must identify any checks it could not complete.

---

## 11. Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `Result: test failed` in `check_env` | LM Studio not running / model not loaded | Developer → Start Server; press Load on the model |
| `/module` not visible | `.opencode/` not copied, or OpenCode opened outside the project root | Check the project folder |
| `mvn` not found | Maven not installed / not on PATH | Install Maven, restart the terminal |
| OpenCode rejects `providers`/`agents`, or agents keep their old models | An old CLI runs: the `opencode` on `PATH` is not the one inside Desktop | Compare versions (`opencode --version` and `%LOCALAPPDATA%\Programs\@opencodedesktop\resources\opencode-cli.exe --version`), then remove the old one or pass the right CLI with `--opencode`. Check the model in the export of a short real session, see "Какой OpenCode использует кит" in README.md (`debug agents` alone is not enough) |
| Tests do not compile | An import is missing in the skeleton (the executor does not add imports) | Tell the Master Chief: "add the missing import to the skeleton" |
| `CHECK FAILED` | The script cannot read test results | Read the hints below that line; check the test command in `AGENTS.md` |
| The Master Chief writes `STOP` and waits | A loop guard fired: reworks or build | Read the reason, decide, and tell the Master Chief to continue |
| The Master Chief does everything itself | It is not reading `AGENTS.md` | Make sure `AGENTS.md` is in the project root |
| `currentsteps.md` is not created | Obsidian not found | Normal: the plan stays in the project |

---

## 12. Next steps

- `README.md` — project overview.
- In Obsidian (the "Мультиагенты. Opencode" knowledge base): detailed tutorials, code walkthroughs, and the full Java case.

---

After the one-time setup, describe your task and approve the plan. The Master Chief manages module order, executors, checks, and statistics.

## Executor verification after the first real run

The Master Chief delegates a small complete class by default and registers its allowed file and requirements before the call. Acceptance requires a recorded check for every requirement, green scoped tests and unchanged file boundaries, including untracked files. Run piece/module tests during implementation and the unfiltered full suite at task completion. One initial red baseline is excluded from the per-scope failure streak; build failures still count. Start metrics before environment setup. Registered attempts missing a review are shown in the report; actions outside the protocol cannot be detected automatically. The user does not run these steps manually.
