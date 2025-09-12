### Goal
Make strict validation the only mode across the agent. Remove all non‑strict validation code paths and plumbing.

### Scope (files to touch)
- `backend/src/agentic_framework/base_agent/agent.py`
- `backend/src/agentic_framework/base_agent/tasks/execution_engine.py`
- `backend/src/agentic_framework/base_agent/tasks/validator.py`
- `backend/testing/calculations_vtwo_smoke_test.py` (and any other callers passing `strict_validation`)

### Deletions and Simplifications
- Remove the `strict_validation` parameter and attribute everywhere:
  - `BaseAgent.__init__(..., strict_validation: bool = True, ...)` → remove param; stop storing/passing it
  - `TaskValidator.__init__(..., strict_validation: bool = False)` → remove param; always strict
  - `PlanExecutionEngine.__init__(..., strict_validation: bool = True)` → remove param; always strict
- Delete all non‑strict branches and fallbacks:
  - In `execution_engine.py`: remove conditions like `if self.strict_validation ... else ...`; enforce strict gating always (tool relevance required, error results block progress, evidence must be tool‑named)
  - In `validator.py`: enforce strict rules unconditionally:
    - Main task completes only when all subtasks complete (if subtasks exist)
    - Subtask requires relevant tool‑named evidence and no error evidence
    - Tool result must be successful and relevant; error → fail fast
  - Remove permissive/heuristic fallback validators (e.g., "basic" completion and lenient evidence thresholds) that allow completion without strict criteria
- Remove unused code after simplification (imports, attributes, helper methods solely used by non‑strict paths)

### Implementation TODOs
- [ ] `agent.py`: Remove `strict_validation` from `BaseAgent.__init__` signature and instance state; stop passing it when creating `TaskValidator` and `PlanExecutionEngine`
- [ ] `execution_engine.py`: Remove `strict_validation` constructor arg/property; make relevance and error gating mandatory in:
  - [ ] Adding observations/evidence only when tool is relevant to current task/subtask
  - [ ] Blocking evidence on error‑like results
  - [ ] Auto‑advance only when relevant tool succeeded and evidence includes the exact tool name
- [ ] `validator.py`: Remove `strict_validation` constructor arg/property; make strict checks unconditional in:
  - [ ] `validate_main_task_completion` (require all subtasks complete when present)
  - [ ] `validate_subtask_completion` (require relevant tool‑named evidence; no error evidence)
  - [ ] `validate_tool_result_for_completion` (require success + relevance; fail fast on errors)
  - [ ] Remove or stop using permissive helpers (e.g., `_basic_main_task_validation`) and any validator registry items used only for non‑strict paths
- [ ] Call sites/tests: Remove any `strict_validation=` arguments (e.g., `backend/testing/calculations_vtwo_smoke_test.py`)
- [ ] Cleanup: Remove dead imports/attributes resulting from the above deletions

### Non‑Goals (for this change)
- No new files or folders
- No changes to tool APIs
- No changes to planning/task creation semantics beyond validation/gating

### Validation Plan (post‑change)
- [ ] Run core agent flows (CIO/CRO) and confirm:
  - Subtasks only complete when their required tools were executed successfully and referenced in evidence
  - Main tasks with subtasks only complete when all subtasks are complete
  - Error tool results never contribute positive evidence or auto‑advancement
- [ ] Ensure tests compile and run after removing constructor args

### Review
- After implementation, summarize removed branches and confirms stricter gating improved correctness without introducing regressions. Add any follow‑ups if additional lenient paths are discovered during testing.
