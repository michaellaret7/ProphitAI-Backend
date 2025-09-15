### Goal
Remove dead/unused code in `backend/src/agentic_framework/**` to simplify maintenance, reduce surface area, and adhere to DRY and simplicity principles.

### Scope (files to touch)
- `backend/src/agentic_framework/base_agent/base_tools/calculator.py`
- `backend/src/agentic_framework/base_agent/memory/episodic_memory.py`
- `backend/src/agentic_framework/base_agent/tasks/manager.py`
- `backend/src/agentic_framework/base_agent/tasks/execution_engine.py`
- `backend/src/agentic_framework/base_agent/events/manager.py`
- `backend/src/agentic_framework/base_agent/memory/error_memory.py` (duplicate entry cleanup)

### Deletion checklist (what to remove)

- `base_tools/calculator.py`
  - [ ] Remove the unused "operation"/`**kwargs` branch (advanced ops: add/subtract/multiply/divide/etc.)
  - [ ] Keep only the `expression` evaluation path used by the tool registration
  - Rationale: Tool schema only passes `expression`; wrapper lambda is `calculator(expression)`. No callsites use `operation`.

- `memory/episodic_memory.py`
  - [ ] Remove `get_latest(...)`
  - [ ] Remove `summarize_older(...)`
  - Rationale: Not referenced anywhere; tool surface only exposes `append` (episodic_remember) and `recall`.

- `tasks/manager.py`
  - [ ] Remove `modify_task_in_plan(...)`
  - [ ] Remove `add_subtask_to_plan(...)`
  - [ ] Remove `reorder_main_tasks(...)`
  - [ ] Remove `get_task_status_prompt(...)`
  - Rationale: No usages found; plan editing is exposed via `add_main_task_to_plan` and `remove_main_task_from_plan` only.

- `tasks/execution_engine.py`
  - [ ] Remove `force_advance_task(...)`
  - Rationale: No usages found; advancement is handled by `advance_task_progression` and intelligent validation.

- `events/manager.py`
  - [ ] Remove `get_event_history(...)`
  - [ ] Remove `get_listener_count(...)`
  - Rationale: Not used anywhere; event consumption is direct via `on(...)` and `emit(...)`.

- `memory/error_memory.py`
  - [ ] Remove duplicated `add_known_solution` block for `stress_test` (duplicate appears twice)
  - Rationale: Exact duplicate entry provides no value and risks confusion.

### Implementation TODOs
- Search/confirm unused status
  - [ ] Grep repo for each symbol above to confirm zero references (beyond their own file definitions)

- Minimal, surgical deletions
  - [ ] Prune the `operation` branch from `calculator.py` while preserving expression evaluation
  - [ ] Delete `get_latest` and `summarize_older` from `episodic_memory.py`
  - [ ] Remove unused plan-edit helpers from `tasks/manager.py` (modify/reorder/add_subtask/status_prompt)
  - [ ] Delete `force_advance_task` from `tasks/execution_engine.py`
  - [ ] Remove `get_event_history` and `get_listener_count` from `events/manager.py`
  - [ ] Remove duplicate `add_known_solution` entry in `error_memory.py`

- Cleanups
  - [ ] Remove now-unused imports in modified files
  - [ ] Ensure any `__all__` or package `__init__` do not reference deleted symbols

### Non‑Goals
- No behavior changes to active tools, task execution, or memory APIs actually used by the agent
- No new files or folders
- No public API additions

### Validation Plan (post‑change)
- Safety/usage validation
  - [ ] For each deleted symbol, `rg` the workspace to confirm no remaining references

- Build/lint/tests
  - [ ] Run linters to catch unused imports after deletion
  - [ ] Run existing agent flows (e.g., CIO/CRO) to ensure no runtime errors
  - [ ] Execute `backend/testing/calculations_vtwo_smoke_test.py` to verify core agent path still functions

- Runtime smoke
  - [ ] Exercise `free_search` tool to confirm `perplexity_free_search` still works
  - [ ] Confirm episodic memory tools (`episodic_remember`, `episodic_recall`) operate normally
  - [ ] Confirm task management tools function (advance, add/remove task, analytics)

### Review (to fill after implementation)
- Summarize removals, any incidental cleanups, and validation outcomes. Note any follow-ups if additional dead code surfaces during linting.
