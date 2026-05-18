# AgentBase Refactor: Centralizing Repeated Agent Scaffolding

**Status:** Revised Proposal  
**Date:** 2026-04-09  
**Scope:** `packages/atlas/src/prophitai_atlas/agents/`  
**Files affected:** `base.py`, `agent.py`, `planner_agent.py`, `worker_agent.py`

---

## 1. Problem Statement

The three concrete agent classes (`Agent`, `PlannerAgent`, `WorkerAgent`) repeat the same execution scaffolding:

- Langfuse run observation setup
- Langfuse attribute propagation around `ExecutionLoop.execute()`
- Mechanical message-list assembly
- Bulk upfront tool registration
- Token counter reset logic

This duplication is small per class but high-friction over time. Any change to run wrapping, trace plumbing, or message assembly must be repeated across multiple files.

The goal of this refactor is to centralize the shared execution plumbing while preserving current runtime behavior.

### 1.1 Explicit Non-Goals

This proposal does **not** try to:

- Change current Langfuse trace attribution semantics for `PlannerAgent` or `WorkerAgent`
- Standardize per-agent telemetry metadata in the same change
- Move provider-specific prompt-selection logic into `AgentBase`
- Make `AgentBase` aware of the concrete `AgentResponse` model

Those are separate concerns and should not be bundled into a DRY cleanup.

---

## 2. Overlap Inventory

### 2.1 Langfuse Observation Wrapping

**Where:** Every `run()` method opens a Langfuse observation span with the same outer structure.

| File | Lines |
|------|-------|
| `agent.py` | 191-196 |
| `planner_agent.py` | 47-52 |
| `worker_agent.py` | 77-82 |

**Repeated shape:**

```python
with self.langfuse.start_as_current_observation(
    as_type="agent",
    name="<agent_name>.run",
    input=<task_or_message>,
    metadata={"provider": self.provider, "model": self.model},
) as run_span:
```

**Variation:** `name` and `input`.

**Refactor suitability:** High. This is truly mechanical duplication.

---

### 2.2 Langfuse Attribute Propagation + Execution

> **⚠ Note:** `run_span.update(output=...)` output shapes differ across all three agents — `Agent` passes a full dict, `PlannerAgent` passes `plan.model_dump()`, `WorkerAgent` passes just the answer string. The `_observe` helper can only encapsulate span setup, not teardown — callers must handle `run_span.update()` themselves after yield.

**Where:** All three agents wrap `self.execution_loop.execute()` in `propagate_attributes`.

| File | Lines |
|------|-------|
| `agent.py` | 249-259 |
| `planner_agent.py` | 73-78 |
| `worker_agent.py` | 91-96 |

**Important nuance:** These blocks are similar, but they are **not identical today**.

- `Agent` passes `trace_name`, tags, and metadata including `provider` and `max_iterations`
- `PlannerAgent` passes `session_id`, tags, and `model` only
- `WorkerAgent` passes `session_id`, tags, and `model` only

**Implication:** A shared helper is still worthwhile, but it must preserve the current per-agent telemetry contract instead of forcing one new schema onto all agents.

**Refactor suitability:** High, with care. The helper should centralize the wrapper mechanics, not silently standardize observability behavior.

---

### 2.3 Tool List Registration Loop

**Where:** `Agent` and `WorkerAgent` iterate a `tools` list to register callables.

| File | Lines |
|------|-------|
| `agent.py` | 99-101 |
| `worker_agent.py` | 70-72 |

**Repeated code:**

```python
if tools:
    for func in tools:
        self.add_tool(**func.tool)
```

**Variation:** None.

**Refactor suitability:** Very high.

---

### 2.4 Message List Construction

**Where:** All three agents build `self.messages` as `[system, ...history, user]`.

| File | Lines | Method |
|------|-------|--------|
| `agent.py` | 144-171 | `build_messages()` |
| `planner_agent.py` | 68-71 | Inline |
| `worker_agent.py` | 86-89 | Inline |

**Pattern:**

```python
messages = [{"role": "system", "content": <system_prompt>}]

if conversation_history:
    messages.extend(conversation_history)

messages.append({"role": "user", "content": <user_content>})
```

**Variation:** `Agent` performs prompt resolution before assembling the list. `PlannerAgent` and `WorkerAgent` do not.

> **⚠ Clarification:** `PlannerAgent` and `WorkerAgent` never use `conversation_history` — they always build a strict `[system, user]` list. The `[system, ...history, user]` pattern is `Agent`-only. The proposed `_build_messages` helper generalizes this with an optional `conversation_history` parameter, which is correct but the shared surface for planner/worker is smaller than implied.

> **⚠ Implementation detail:** `Agent.build_messages()` (lines 155-163) currently contains Anthropic prompt-selection logic *inside itself*:
> ```python
> if system_prompt is not None:
>     prompt = system_prompt
> elif self.provider == "anthropic" and self.system_prompt_blocks is not None:
>     prompt = self.system_prompt_blocks
> else:
>     prompt = self.system_prompt
> ```
> This must be extracted into `Agent.run()` before calling `self._build_messages(resolved_prompt, ...)`. This is the trickiest part of the `Agent` refactor.

**Refactor suitability:** High, as long as prompt selection stays in the subclasses and only the list assembly moves to base.

---

### 2.5 Token Counter Reset

**Where:** Only `Agent` resets token counters before execution.

| File | Lines |
|------|-------|
| `agent.py` | 199-201 |

**Current inconsistency:**

```python
self.total_tokens = 0
self.cache_creation_input_tokens = 0
self.cache_read_input_tokens = 0
```

`PlannerAgent` and `WorkerAgent` currently rely on being short-lived and single-use. That works today but leaves run-level accounting semantics implicit.

**Refactor suitability:** High. This proposal should make token accounting explicit: every `run()` starts from zero for every agent type.

---

### 2.6 `AgentResponse` Construction

**Where:** `Agent` and `WorkerAgent` both map the `ExecutionLoop.execute()` result dict into `AgentResponse`.

| File | Lines |
|------|-------|
| `agent.py` | 283-293 |
| `worker_agent.py` | 100-108 |

**Observation:** This is duplicated.

**Decision:** Do **not** move this into `AgentBase`. `PlannerAgent` returns `Plan`, not `AgentResponse`, and the base class should remain execution-oriented rather than response-model-aware.

**Refactor suitability:** Low for this proposal. Leave it local, or extract later into a non-base helper if it becomes worth it.

---

## 3. Proposed Base Methods

### 3.1 `register_tools(tools: List[Callable]) -> None`

**Replaces:** The `if tools: for func in tools:` loop in `Agent` and `WorkerAgent`.

```python
def register_tools(self, tools: List[Callable]) -> None:
    """Bulk-register a list of @agent_tool-decorated callables."""

    for func in tools:
        self.add_tool(**func.tool)
```

**Callers:** `Agent.__init__`, `WorkerAgent.__init__`

---

### 3.2 `_observe(span_name: str, input: Any)` context manager

**Replaces:** The `start_as_current_observation(...)` block in all three `run()` methods.

```python
@contextmanager
def _observe(self, span_name: str, input: Any):
    """Wrap a run in a Langfuse observation span."""

    with self.langfuse.start_as_current_observation(
        as_type="agent",
        name=span_name,
        input=input,
        metadata={"provider": self.provider, "model": self.model},
    ) as span:
        yield span
```

**Callers:** All three `run()` methods

---

### 3.3 `_execute_with_tracing(...) -> Dict[str, Any]`

**Replaces:** The `propagate_attributes(...)` + `execution_loop.execute()` block in all three agents.

**Key design constraint:** This helper must preserve each agent's existing telemetry shape by default.

```python
def _execute_with_tracing(
    self,
    *,
    tags: List[str],
    trace_name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run the execution loop inside Langfuse attribute propagation."""

    propagate_kwargs = {
        "session_id": self.session_id,
        "tags": tags,
        "metadata": {"model": self.model, **(metadata or {})},
    }

    if trace_name is not None:
        propagate_kwargs["trace_name"] = trace_name

    with propagate_attributes(**propagate_kwargs):
        return self.execution_loop.execute()
```

**Callers:**

- `Agent.run()`:

```python
result = self._execute_with_tracing(
    trace_name=trace_name,
    tags=[trace_name, self.provider],
    metadata={
        "provider": self.provider,
        "max_iterations": str(self.max_iterations),
    },
)
```

- `PlannerAgent.run()`:

```python
result = self._execute_with_tracing(
    tags=["PlannerAgent", self.provider],
)
```

- `WorkerAgent.run()`:

```python
result = self._execute_with_tracing(
    tags=["WorkerAgent", self.provider],
)
```

**Important:** This proposal deliberately avoids standardizing planner/worker metadata in the same refactor. If telemetry should be normalized later, that should be a separate change with dashboard review.

---

### 3.4 `_reset_counters() -> None`

**Replaces:** The inline token reset block in `Agent.run()`.

```python
def _reset_counters(self) -> None:
    """Reset token counters before a new run."""

    self.total_tokens = 0
    self.cache_creation_input_tokens = 0
    self.cache_read_input_tokens = 0
```

**Callers:** All three `run()` methods

**Behavioral decision:** After this refactor, token accounting is explicitly run-scoped for every agent type.

---

### 3.5 `_build_messages(system_prompt, user_content, conversation_history=None) -> List[Dict]`

**Replaces:** Inline message-list assembly in all three agents.

```python
def _build_messages(
    self,
    system_prompt: Union[str, List[Dict[str, Any]]],
    user_content: str,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Build the standard [system, ...history, user] message list."""

    messages = [{"role": "system", "content": system_prompt}]

    if conversation_history:
        messages.extend(conversation_history)

    messages.append({"role": "user", "content": user_content})

    return messages
```

**Callers:** All three agents

**Note:** Prompt selection stays in the subclasses. This helper only builds the list after the caller has already resolved the system prompt value.

**Repo check:** As of 2026-04-09, `Agent.build_messages()` has no external callers outside `agent.py`, so it can be removed or turned into a thin private wrapper without breaking known call sites.

---

## 4. Subclass Impact: Before vs After

### 4.1 WorkerAgent.run()

`WorkerAgent.run()` becomes materially shorter, but not as short as the original draft suggested because `AgentResponse(...)` stays local:

```python
def run(self) -> AgentResponse:
    with self._observe("worker_agent.run", self.task) as run_span:
        self._reset_counters()
        self.messages = self._build_messages(self._build_system_prompt(), self.task)

        result = self._execute_with_tracing(
            tags=["WorkerAgent", self.provider],
        )

        run_span.update(output=result["answer"])

        return AgentResponse(
            answer=result["answer"],
            tool_calls_made=result["tool_calls"],
            tokens_used=result["total_tokens"],
            cache_creation_input_tokens=result["cache_creation_input_tokens"],
            cache_read_input_tokens=result["cache_read_input_tokens"],
            iterations=result["iterations"],
            stop_reason=result["stop_reason"],
        )
```

**Effect:** Shared execution plumbing moves to base; worker-specific prompt building and response type stay local.

---

### 4.2 PlannerAgent.run()

`PlannerAgent.run()` keeps its planner-specific prompt injection and `Plan` parsing, but loses repeated wrapper code:

```python
def run(self) -> Plan:
    with self._observe("planner_agent.run", self.task) as run_span:
        self._reset_counters()

        if self.system_context:
            user_content = (
                f"<agent_system_prompt>\n{self.system_context}\n</agent_system_prompt>\n\n"
                f"The above is the system prompt for the agent that will execute your plan. "
                f"Your plan MUST respect the constraints, available data, and methodology "
                f"defined in that prompt.\n\n"
                f"Task: {self.task}"
            )
        else:
            user_content = self.task

        self.messages = self._build_messages(PLANNER_SYSTEM_PROMPT, user_content)

        result = self._execute_with_tracing(
            tags=["PlannerAgent", self.provider],
        )

        plan = parse_with_gpt(result["answer"], target_model=Plan)
        run_span.update(output=plan.model_dump())
        return plan
```

**Effect:** The planner stays a child agent with the same current trace metadata shape.

---

### 4.3 Agent.run()

`Agent.run()` still owns the complex parts:

- optional planning phase
- plan injection into the system prompt
- provider-specific prompt selection
- structured output parsing
- per-turn cleanup of `update_plan`

The savings come from replacing the repeated scaffolding:

- `self._observe(...)` replaces the outer Langfuse observation block
- `self._reset_counters()` makes run-level token semantics explicit
- `self._build_messages(...)` handles list assembly after prompt resolution
- `self._execute_with_tracing(...)` wraps execution while preserving current `Agent` telemetry fields

This keeps `Agent.run()` meaningfully shorter without forcing planning logic into the base class.

---

### 4.4 WorkerAgent.__init__ and Agent.__init__

Both `__init__` methods replace:

```python
if tools:
    for func in tools:
        self.add_tool(**func.tool)
```

With:

```python
if tools:
    self.register_tools(tools)
```

Minor change, but consistent and low-risk.

---

## 5. What NOT to Centralize

### 5.1 `web_search` registration

`Agent` and `WorkerAgent` both register it, but `PlannerAgent` intentionally does not. This should remain local or be controlled by an explicit opt-in flag later.

### 5.2 Anthropic prompt-block handling

The logic for selecting `system_prompt_blocks` vs `system_prompt` is provider-specific and currently belongs in the concrete agent classes.

### 5.3 Planning phase logic

Plan creation, plan injection, and `update_plan` tool registration/cleanup are `Agent`-specific concerns.

### 5.4 Deferred tools / `register_tools` built-in tool

Only `Agent` supports deferred tool loading via the LLM-facing `register_tools` tool. That feature should remain `Agent`-specific.

### 5.5 `AgentResponse` construction in `AgentBase`

`AgentBase` should not import or construct `AgentResponse`. `PlannerAgent` returns `Plan`, and the base class is cleaner if it stays focused on execution scaffolding rather than concrete response types.

### 5.6 Observability schema standardization

This refactor should not silently add `trace_name`, `provider`, or `max_iterations` metadata to planner/worker runs. If telemetry should be standardized, do it in a separate change after reviewing how current Langfuse dashboards and filters depend on the existing shape.

---

## 6. Implementation Checklist

- [ ] **`base.py`**: Add `register_tools()`, `_observe()`, `_execute_with_tracing()`, `_reset_counters()`, `_build_messages()`
- [ ] **`base.py`**: Add `from contextlib import contextmanager` and `from langfuse import propagate_attributes` imports
- [ ] **`base.py`**: Do **not** add `AgentResponse` imports or response-construction helpers
- [ ] **`worker_agent.py`**: Refactor `__init__` to use `self.register_tools(tools)`
- [ ] **`worker_agent.py`**: Refactor `run()` to use `_observe`, `_reset_counters`, `_build_messages`, `_execute_with_tracing`
- [ ] **`planner_agent.py`**: Refactor `run()` to use `_observe`, `_reset_counters`, `_build_messages`, `_execute_with_tracing`
- [ ] **`agent.py`**: Refactor `__init__` to use `self.register_tools(tools)`
- [ ] **`agent.py`**: Extract Anthropic prompt-selection logic (lines 155-163) from `build_messages()` into `Agent.run()` so the resolved prompt can be passed to `self._build_messages()`
- [ ] **`agent.py`**: Refactor `run()` to use `_observe`, `_reset_counters`, `_build_messages`, `_execute_with_tracing`
- [ ] **`agent.py`**: Ensure the existing `try/finally` block for `update_plan` tool cleanup (lines 198/295-298) coexists correctly with the `_observe` context manager
- [ ] **`agent.py`**: Preserve current `Agent`-only `trace_name` / metadata behavior when calling `_execute_with_tracing(...)`
- [ ] **`agent.py`**: Collapse or remove public `build_messages()` if desired
- [ ] **Verify**: Confirm `build_messages()` has no external callers before removing it
- [ ] **Test**: Add targeted tests that assert the `propagate_attributes(...)` kwargs used by `Agent`, `PlannerAgent`, and `WorkerAgent`
- [ ] **Test**: Add repeated-run tests proving token counters reset on every `run()` for all agent types
- [ ] **Test**: Verify Anthropic prompt blocks still pass through unchanged after refactor
- [ ] **Test**: Run existing smoke tests plus a real standalone `WorkerAgent` run and `PlannerAgent` run

---

## 7. Success Criteria

| Criterion | Target |
|-----------|--------|
| Shared execution helpers added to `AgentBase` | 5 |
| `AgentBase` depends on `AgentResponse` | No |
| `PlannerAgent` / `WorkerAgent` Langfuse metadata shape changes in this refactor | No |
| Token accounting semantics | Reset at the start of every `run()` |
| Anthropic prompt-block behavior | Unchanged |
| Remaining intentional duplication | Local `AgentResponse(...)` construction in `Agent` and `WorkerAgent` |

Line-count reduction is a secondary benefit. The primary goal is single-source-of-truth for execution scaffolding without introducing behavior drift.

---

## 8. Risk Assessment

**Risk: Observability drift**  
If the shared tracing helper forces a new metadata schema, planner and worker traces will change shape even though the stated goal is refactoring.  
**Mitigation:** `_execute_with_tracing(...)` must accept optional `trace_name`, `tags`, and `metadata`, and each caller must pass the same values it uses today. Add tests around exact `propagate_attributes(...)` kwargs.

**Risk: Counter lifecycle ambiguity**  
If only `Agent` resets counters, repeated runs on worker/planner instances will accumulate token counts.  
**Mitigation:** Make `_reset_counters()` mandatory at the start of every `run()` implementation. Add repeated-run tests.

**Risk: Anthropic provider-specific behavior**  
The `_build_messages(...)` helper treats `system_prompt` as opaque. Anthropic block prompts must still pass through untouched.  
**Mitigation:** Keep prompt selection in subclasses and add an Anthropic regression test.

**Risk: `build_messages()` external callers**  
Removing or privatizing `Agent.build_messages()` would break any external code that still calls it.  
**Mitigation:** Repo search before removal. As of 2026-04-09, only internal uses were found.

**Risk: Existing tests are too shallow**  
Current repo tests are smoke-style and do not assert tracing kwargs or repeated-run counter behavior.  
**Mitigation:** Add targeted unit tests for the helper contract before relying on smoke tests alone.

**Risk: `Agent.build_messages()` prompt-selection extraction**  
`Agent.build_messages()` is not a pure list assembler — it contains Anthropic-specific provider branching (lines 155-163) that selects between `system_prompt`, `system_prompt_blocks`, and `self.system_prompt`. After refactoring, this logic must move into `Agent.run()` before calling `self._build_messages(resolved_prompt, ...)`. Missing this would break Anthropic prompt-block behavior.  
**Mitigation:** Explicitly extract prompt resolution as a separate step in `Agent.run()` before calling the base helper. Add a regression test with `provider="anthropic"` and `system_prompt_blocks` set.

**Risk: `Agent.run()` try/finally cleanup pattern**  
`Agent.run()` wraps its body in a `try/finally` (lines 198/295-298) that removes the `update_plan` tool. This must coexist with the `_observe` context manager — the `try/finally` should remain inside the `with self._observe(...)` block, not be replaced by it.  
**Mitigation:** Preserve the `try/finally` inside the observation context manager during refactoring.

**Risk: `system_prompt` type contract is implicit**  
`WorkerAgent._build_system_prompt()` returns either `str` or `List[Dict]` depending on provider. Using `Any` as the type hint on `_build_messages` hides this contract.  
**Mitigation:** Use `Union[str, List[Dict[str, Any]]]` to document the actual type contract.
