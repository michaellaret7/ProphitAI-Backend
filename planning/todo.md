### Goal
Make strict validation the only mode across the agent. Remove all non‑strict validation code paths and plumbing.

### Scope (files to touch)
- `backend/src/agentic_framework/base_agent/agent.py`
- `backend/src/agentic_framework/base_agent/tasks/execution_engine.py`
- `backend/src/agentic_framework/base_agent/tasks/validator.py`
- `backend/testing/calculations_vtwo_smoke_test.py` (and any other callers passing `strict_validation`)

### Deletion checklist (what to remove)
- `backend/src/agentic_framework/base_agent/agent.py`
  - [ ] Remove `strict_validation` param from `BaseAgent.__init__` signature.
  - [ ] Delete `self.strict_validation = strict_validation` assignment.
  - [ ] Update `TaskValidator(...)` construction to drop `strict_validation=...` (use `TaskValidator(verbose=verbose)`).
  - [ ] Update `PlanExecutionEngine(...)` construction to drop `strict_validation=...` (pass only `task_manager`, `event_manager`, `verbose`).

- `backend/src/agentic_framework/base_agent/tasks/execution_engine.py`
  - [ ] Remove `strict_validation` param from `__init__` signature and delete `self.strict_validation` property.
  - [ ] In `update_task_from_tool_result`:
    - [ ] Replace `is_relevant = ... if self.strict_validation else True` with unconditional relevance: `is_relevant = self._is_tool_relevant(...)`.
    - [ ] Replace `if self.current_subtask and (is_relevant or not self.strict_validation):` with `if self.current_subtask and is_relevant:`.
    - [ ] Make error‑evidence guard unconditional: keep `if self._looks_like_success_evidence(evidence) and is_error: continue` (remove the `self.strict_validation` check).
  - [ ] In `_should_auto_advance_subtask`:
    - [ ] Remove the `if self.strict_validation:` block and always require: `is_relevant and not is_error and has_tool_named_evidence`.
  - [ ] Remove any remaining references to `self.strict_validation`.

- `backend/src/agentic_framework/base_agent/tasks/validator.py`
  - [ ] Remove `strict_validation` param from `__init__` and delete `self.strict_validation`.
  - [ ] In `validate_main_task_completion`: make subtask completion requirement unconditional (if subtasks exist, all must be complete).
  - [ ] In `validate_subtask_completion`: make relevant tool‑named evidence and no‑error checks unconditional (were under `if self.strict_validation`).
  - [ ] In `validate_tool_result_for_completion`: make fail‑fast on error and relevance requirements unconditional (remove `self.strict_validation` guards).
  - [ ] Delete any unused imports/branches left over from removing the above.
  - [ ] Optional: If `_basic_main_task_validation` becomes unreachable, remove it; otherwise leave as fallback.

- Call sites
  - [ ] `backend/testing/calculations_vtwo_smoke_test.py`: remove `strict_validation=True` when constructing `BaseAgent`.
  - [ ] Grep repo for `strict_validation` and remove any other call‑site args/usages.

### Implementation TODOs
- [ ] Agent: remove param/wiring
  - [ ] `agent.py`: drop param; stop passing into `TaskValidator` and `PlanExecutionEngine`.
- [ ] Execution engine: enforce strict always
  - [ ] `execution_engine.py`: drop param/property; make relevance/error/evidence gates unconditional as listed above.
- [ ] Validator: enforce strict always
  - [ ] `validator.py`: drop param/property; make strict checks unconditional in the three validators listed above.
- [ ] Call sites/tests
  - [ ] Remove `strict_validation=` args (e.g., smoke test).
- [ ] Cleanup
  - [ ] Remove dead code/imports; run linters; fix any type hints or signatures affected.

### Non‑Goals
- No new files or folders
- No changes to tool APIs
- No changes to planning/task creation semantics beyond validation/gating

### Validation Plan (post‑change)
- [ ] Run core agent flows (CIO/CRO) and confirm:
  - Subtasks only complete when their required tools were executed successfully and referenced in evidence
  - Main tasks with subtasks only complete when all subtasks are complete
  - Error tool results never contribute positive evidence or auto‑advancement
- [ ] Ensure tests compile and run after removing constructor args

### Review (to fill after implementation)
- Summarize removed branches and confirm stricter gating improved correctness without regressions. Note any follow‑ups if additional lenient paths are discovered during testing.
