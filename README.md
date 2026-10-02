# Multi-Agent AI Development Environment
# My private fine-tuned opencode system.

This repository contains the configuration for a custom multi-agent system, designed to automate development, architecture planning, and code execution.

## Getting started

- 🇷🇺 [QUICKSTART.ru.md](QUICKSTART.ru.md) — как подключить кит к своему проекту с нуля (пример: Java / Spring Boot).
- 🇬🇧 [QUICKSTART.en.md](QUICKSTART.en.md) — the same guide in English.

## Architecture Overview
The system uses a hierarchical agent structure defined in `opencode.jsonc`:

* **The Brain (`build` agent):** Acts as the project manager and architect. It uses a frontier model (`opencode-go/deepseek-v4.1-flash`) to generate task plans, design architecture, write test skeletons, and delegate specific tasks.
* **The Executor (`executor` agent):** A strict coding agent powered by a local model via LM Studio (Qwen3.8 27B). It implements code based on the detailed specifications provided by the Brain without altering the core architecture.
* **Fast Executor (`executor-fast`):** A lightweight local model (Spark X2.5 4B) dedicated to minor, rapid code adjustments and formatting.

## Features

* **Local Execution:** Integration with LM Studio (`http://127.0.0.1:1234/v1`) keeps coding tasks on local hardware, reducing API costs and preserving privacy.
* **Test-Driven Workflow:** The Brain agent is instructed to generate test skeletons first, and code is iterated upon until the tests pass.
* **Granular Permissions:** Subagents operate with restricted permissions (shell access denied, read/edit allowed) to ensure safe execution.

## Workflow explanation:
`My aim is to divide all tasks given the frontier model by user onto separate specific actions.`
**opencode.jsonc** is responsible for pointing out certain roles of each model.
**AGENTS.md** is responsible for the rules of the project — how the work is done, not who does it.

The rules created with that goals, say the brain must start with a skeleton: signatures plus a detailed spec comment inside every function, with the body left as like `raise NotImplementedError`.
Then the brain writes the tests right away, against that skeleton. 
Red tests are expected at this point.

Only after that does the brain delegate the implementation: one function per `executor` call, never a whole file.
The executor reads the file and fills in only the body. It never touches signatures, imports, or the skeleton.
When the executor replies, the brain reads the code and runs the tests. Green means done; red means fix it or send it back.
So the flow is always: plan → skeleton → tests → delegate → review → green.

Commands are just the trigger for this flow:
* `/plan-project <description>` — plan only: split a big task into modules and write the checklist to the Obsidian plan. No code.
* `/module <name>` — build one module end to end using the flow above.

In short: 
- `opencode.jsonc` in general means **who** works and with what;
- `AGENTS.md` says **how** the work is done; the commands **start** the work.

## Requirements

- OpenCode.
- LM Studio running at `http://127.0.0.1:1234/v1` with the executor model loaded.
- **Python** — needed only for the kit's own utility scripts in `kit/` (`find_vault.py`, `check_env.py`, `pipeline_smoke.py`), independent of the project's language. Run them with `py` from the project root.
- The project itself can use any language/toolchain — set it in the `# EDIT` → **Project stack** section of `AGENTS.md`.

## How to run
```powershell
py kit/check_env.py                          # check config + LM Studio
py -m unittest discover -s tests -v          # run the project's tests
py -m unittest discover -s kit/tests -v      # run the kit's tests
py kit/find_vault.py                         # locate an Obsidian vault (if any)
```

In OpenCode:

```
/plan-project <description>    # plan a multi-module task
/module <name>                 # build one module
```

## Utility scripts (when to use them)

Three small Python tools ship with the kit. Run them with `py`.

### `check_env.py` — "is my environment ready?"

```powershell
py kit/check_env.py
```

It checks three things:
- `opencode.jsonc` is valid and prints the configured agents and models;
- LM Studio answers at `http://127.0.0.1:1234/v1` and lists the loaded models;
- a live request to a local model returns an answer.

Use it when:
- you run the kit on a new machine for the first time;
- you get `Model not loaded` or an empty model list;
- you edited `opencode.jsonc` and want to confirm it still parses.

### `pipeline_smoke.py` — "can the local executor really implement?"

An offline smoke test of the brain → executor → review flow. It does **not** use OpenCode.

```powershell
py kit/pipeline_smoke.py
py kit/pipeline_smoke.py --model spark-x2.5-4b   # try another local model
py kit/pipeline_smoke.py --keep                  # keep the temp dir for inspection
```

What it does:
1. writes a skeleton with spec comments and its tests into a temp folder;
2. asks the executor model (taken from `opencode.jsonc`) to fill the bodies;
3. runs the tests and prints green or red.

Use it when:
- you want to check whether a local model is good enough before trusting it with real work;
- you want to compare two models;
- OpenCode misbehaves: if this test is green but OpenCode fails, the problem is in the kit config, not in the model.

### `find_vault.py` — "where is my Obsidian?"

```powershell
py kit/find_vault.py --no-scan    # fast: registry only
py kit/find_vault.py              # also scan the filesystem
```

Prints any Obsidian vault found. The brain uses it to decide where the work plan lives: inside the vault (`currentsteps.md`) or in the project when there is no vault.

## How to use this template

1. Copy into your project root: `opencode.jsonc`, `AGENTS.md`, the `kit/` folder, and the `.opencode/commands/` folder.
2. The kit is self-contained: all rules live in the project `AGENTS.md`. No machine-global config is needed.
3. Edit the sections marked `# EDIT` in `AGENTS.md`: **Stack** (language, interpreter, test command), **Layout**, **Memory** (name of the plan note).
4. Start in OpenCode: `/plan-project <description>` to plan, then `/module <name>` to build.

