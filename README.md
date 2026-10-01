# Multi-Agent AI Development Environment
# My private fine-tuned opencode system.
This repository contains the configuration for a custom multi-agent system 
, designed to automate development, architecture planning, and code execution.

## Architecture Overview
The system uses a hierarchical agent structure 
defined in `opencode.jsonc`:

**Major prompt template like following:**

* **The Brain (`build` agent):** Acts as the project manager and architect[cite: 3]. It utilizes a frontier model (`opencode-go/deepseek-v4.1-flash`) to generate task plans, design architecture, write test skeletons, and delegate specific tasks[cite: 3].
* **The Executor (`executor` agent):** A strict coding agent powered by a local model via LM Studio (e.g., Qwen3.8 27B)[cite: 3]. It implements code based on detailed specifications provided by the Brain without altering the core architecture[cite: 3].
* **Fast Executor (`executor-fast`):** A lightweight local model (e.g., Spark X2.5 4B) dedicated to minor, rapid code adjustments and formatting[cite: 3].

## Features

* **Local Execution:** An integration with LM Studio (`http://127.0.0.1:1234/v1`) for executing coding tasks on local hardware is reducing API costs and ensuring privacy.
* **Test-Driven Workflow:** The Brain agent is instructed to generate test skeletons first, and code is iterated upon until tests pass.
* **Granular Permissions:** Subagents operate with restricted permissions (e.g., shell access denied, read/edit allowed) to ensure safe execution.