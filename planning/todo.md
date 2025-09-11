## Fix Plan: Make task completion depend on correct tool execution (strict, error-aware gating)

### Problem statement
The agent is marking tasks and subtasks as completed even when the required tools were not executed and when tool calls returned errors. Generic “success” evidence is being attached to the active subtask regardless of relevance, so unrelated calls (e.g., `get_ticker_fundamental_data`) are recorded as valid progress for subtasks that require other tools (e.g., `episodic_remember`/`episodic_recall`). Error strings are also treated as “substantial output,” inflating confidence and auto-advancing tasks.

### Impact
- Incorrect task completion, misleading evidence, and false progress
- Potentially harmful outputs and broken trust in the execution trace

### Root cause (current behavior)
- Evidence is added for any tool call as “Successfully executed tool …” plus generic indicators, without verifying success or relevance
- Evidence/observations are attached to the current subtask even if the tool is unrelated
- Subtask completion is driven by counts/length of evidence/observations rather than validation that the required tool(s) ran successfully
- Error strings (e.g., missing args) are classified as “substantial text output,” contributing to completion

### Goals
- Only mark a subtask complete when its required tool(s) ran successfully
- Do not attach success evidence when a call failed or returned an error-like string
- Prevent unrelated tools from satisfying a subtask; unrelated calls should not advance progress
- Keep the fix minimal, modular, and backwards-compatible

### Non-goals
- No new files or folders
- No broad refactor of planning/execution; limit changes to validation and evidence handling

---

### Step-by-step solution (high-level)
1) Evidence hygiene (strict, error-aware)
   - Treat strings containing error keywords as failures
   - Only add “Successfully executed tool …” and “Data retrieval completed” when result shows success and no error indicators
   - Never add “substantial text output” evidence for error-looking strings

2) Relevance gating
   - Only attach evidence/observations to the current subtask when the tool is relevant to that subtask
   - Relevance rule (simple, robust): tool name must either (a) be listed in the main task’s `predicted_tool_use` and (b) be mentioned in the current subtask description (exact tool name substring)
   - Otherwise, attach observations to the main task (optional), but do not count toward subtask completion

3) Completion gating
   - Subtask auto-advance requires: (a) relevant tool match per above AND (b) success (no error) AND (c) at least one evidence item that includes the exact tool name
   - Main task completion requires: all its subtasks completed (prefer this path); fall back only if there are no subtasks

4) Planning nudges (minimal)
   - Nudge the planning tool prompt to include explicit tool names in subtask descriptions when a tool is required (it already often does). This makes relevance gating reliable without changing models

5) Safe rollout
   - Guard with a boolean `STRICT_VALIDATION` flag (default True) so we can quickly toggle behavior if needed

---

### Files to update (minimal surface area)
- `backend/src/agentic_framework/base_agent/tasks/execution_engine.py`
  - Evidence creation: make success evidence conditional on non-error, suppress “substantial text” on errors
  - Only attach evidence/observations to current subtask if tool is relevant (predicted + name present in subtask description)
  - `_should_auto_advance_subtask`: require relevant tool + success + evidence containing the exact tool name

- `backend/src/agentic_framework/base_agent/tasks/validator.py`
  - Subtask validation: require at least one evidence entry that includes the relevant tool name and no error indicators
  - Main task validation: prefer “all subtasks complete”; de-weight generic evidence
  - Treat error strings as strong negatives across validators

- `backend/src/agentic_framework/base_agent/agent.py`
  - Add `STRICT_VALIDATION: bool = True` (init param or attribute) and pass through to execution/validator if needed

- `backend/src/agentic_framework/base_agent/base_tools/planning_tool.py`
  - Add one sentence to the system rules asking for explicit tool names in subtask descriptions when a tool is required

Note: No new files. No API changes to tool functions.

---

### Acceptance criteria
- A subtask that says “Store V1 via `episodic_remember` and validate via `episodic_recall`” only completes if those tools are actually called successfully; calling `get_ticker_fundamental_data` does not count
- Error calls (e.g., missing `portfolio_dict` for `build_portfolio`) no longer add success evidence and cannot complete subtasks
- `task_state.json` evidence lists reflect the correct tool names for each subtask; unrelated tools do not appear as completion evidence for that subtask
- Main tasks only complete when all their subtasks are complete (or when they have no subtasks)

---

### Implementation TODOs (checklist)
- [ ] Add `STRICT_VALIDATION` flag on the agent (default True)
- [ ] Update `execution_engine.collect_evidence_from_tool_result` to be error-aware and suppress generic success on failures
- [ ] Update `execution_engine.update_task_from_tool_result` to gate subtask evidence/observations by relevance (predicted + tool name in subtask description)
- [ ] Update `execution_engine._should_auto_advance_subtask` to require relevant tool + success + tool-named evidence
- [ ] Harden `validator.validate_subtask_completion` to require at least one evidence item containing the relevant tool name and no error indicators
- [ ] Harden `validator.validate_main_task_completion` to require all subtasks completed (when present), reduce weight of generic evidence
- [ ] Tweak `planning_tool` prompt to request explicit tool names in subtask descriptions when a tool is required
- [ ] Manual validation run: CIO flow through V1/V2/V3 – confirm episodic memory steps only complete when memory tools are used
- [ ] Manual validation run: `build_portfolio` – confirm it cannot complete without a valid `portfolio_dict`

---

### Test plan (manual)
1) Re-run a scenario that previously “completed” memory subtasks without calling memory tools; verify those subtasks now remain pending until `episodic_remember` and `episodic_recall` are called successfully
2) Trigger a failing call (e.g., `build_portfolio` without `portfolio_dict`); verify no success evidence is attached and the subtask does not advance
3) Verify `task_state.json` contains accurate, relevant evidence for each subtask (no unrelated tools listed as completion evidence)

### Rollback plan
- Toggle `STRICT_VALIDATION = False` on the agent to restore prior permissive behavior if needed

---

### Review (to be completed after implementation)
- High-level summary of edits and their effect on accuracy and safety
- Any follow-ups or additional hardening identified during validation
