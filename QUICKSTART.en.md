# Quick start (EN): OpenCode kit, example — Java / Spring Boot

> A from-scratch guide: how to plug this kit into your project and start working in OpenCode.
> Русская версия: [QUICKSTART.ru.md](QUICKSTART.ru.md)

---

## 1. What this is

This kit turns OpenCode into a **"brain + executors"** setup:

- 🧠 **Brain** (`build`, cloud model) — plans the task, writes a **code skeleton with specs**, writes **tests**, and reviews the result.
- 🛠 **Executor** (`executor`, local LM Studio model) — fills in **method bodies only**, strictly following the specs. It touches nothing else.

The cycle is always the same:

```
you:  /module task
brain: skeleton + specs + tests (tests are red for now — that is normal)
       └─ delegates to the executor, one method at a time
executor: fills in the body per spec
brain: runs the tests → green → module done
```

The example below is a **Java (Spring Boot)** project. The same flow works for any language — only the test command changes.

---

## 2. What you need

| What | Why | Check |
| --- | --- | --- |
| OpenCode | the agent itself | — |
| LM Studio | local executor model | `py kit/check_env.py` |
| Python 3.13 | **only** the kit's utilities | `py --version` |
| JDK 21 | compile Java | `java -version` |
| Maven | build and test Java | `mvn -v` |

> Python is needed by the kit (Obsidian lookup and checks), not by your Java project.

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
- Tests: JUnit 5. Run: `mvn -q test`.
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

Open a terminal in the project folder and run:

```powershell
py kit/check_env.py
```

Expected: `Result: ready for use`.

If it is red, see **10. Troubleshooting**.

---

## 7. Step 5. Start OpenCode

Open OpenCode **in the `task-api` folder** (where `opencode.jsonc` lives).

Make sure everything is visible:
- type `/` — you should see `/plan-project` and `/module`;
- ask: "Read the work plan" — the brain finds Obsidian via `kit/find_vault.py` (or falls back to `currentsteps.md`).

---

## 8. Step 6. Plan the project

Type in the OpenCode chat:

```text
/plan-project Task REST API on Spring Boot: model, service, controller
```

The brain **only plans** (splits the task into modules and writes a checklist) — it writes no code.

Example result:

```md
## Modules
- [ ] model      — Task + store
- [ ] service    — list / create / complete / delete
- [ ] controller — REST endpoints
```

Review the plan and say "ok, go".

---

## 9. Step 7. Build module by module

For each module in the plan:

```text
/module model
```

What happens automatically:

1. The brain creates a **skeleton** `Task.java` with Javadoc specs and a placeholder:
   ```java
   public Task create(String title) {
       throw new UnsupportedOperationException("TODO: executor");
   }
   ```
2. The brain creates **tests** `TaskServiceTest.java` and runs `mvn -q test` — they are **red** (that is expected).
3. The brain asks the **executor** to fill the method body per spec.
4. The executor fills **only the body**.
5. The brain runs `mvn -q test` again → **green** → module done, move on.

Repeat:

```text
/module service
/module controller
```

> Rule: **one piece per executor**. Never ask for "the whole project at once".

---

## 10. Step 8. Verify and run

```powershell
mvn -q test             # tests
mvn spring-boot:run     # start the app
```

In another window:

```powershell
curl http://localhost:8080/tasks
```

---

## 11. Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `Result: test failed` in `check_env` | LM Studio not running / model not loaded | Developer → Start Server; press Load on the model |
| `/module` not visible | `.opencode/` not copied, or OpenCode opened outside the project root | Check the project folder |
| `mvn` not found | Maven not installed / not on PATH | Install Maven, restart the terminal |
| Tests do not compile | Executor forgot an import | Tell the brain: "review and fix it" |
| The brain does everything itself | It is not reading `AGENTS.md` | Make sure `AGENTS.md` is in the project root |
| `currentsteps.md` is not created | Obsidian not found | Normal: the plan stays in the project |

---

## 12. Next steps

- `README.md` — project overview.
- In Obsidian (the "Мультиагенты. Opencode" knowledge base): detailed tutorials, code walkthroughs, and the full Java case.

---

> Short version: **copy the kit into the project → edit two sections in `AGENTS.md` → `/plan-project` → `/module` one by one → tests green.**
