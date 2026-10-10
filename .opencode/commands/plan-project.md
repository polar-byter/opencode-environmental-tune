---
description: Plan a multi-module project — break it into modules, no code
agent: build
---

Plan the project `$ARGUMENTS`. Do NOT write any code and do NOT call any subagent.

Steps:
1. Resolve and read the work plan using the **Work plan (memory)** section of AGENTS.md. Create it if missing; use the same resolved file throughout this task.
2. Break the task into modules. For each module give: name, responsibility, public interface (functions/classes), and dependencies on other modules.
3. Write the module checklist into that work plan as `- [ ]` items.
4. Show me the plan and stop. Wait for my approval before any code. Explain that approval to implement the whole plan lets the Master Chief choose and build modules in dependency order without separate `/module` requests.

Output format:
- Modules: name — responsibility — interface — depends on
- Order of work: which module first and why
- Work plan: resolved path and checklist status
