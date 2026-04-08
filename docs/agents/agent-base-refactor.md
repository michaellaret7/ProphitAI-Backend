# AgentBase Refactor: Centralizing Repeated Agent Code

**Status:** Planned  
**Date:** 2026-04-08  
**Scope:** `packages/atlas/src/prophitai_atlas/agents/`  
**Files affected:** `base.py`, `agent.py`, `planner_agent.py`, `worker_agent.py`

---

## 1. Problem Statement

The three concrete agent classes (`Agent`, `PlannerAgent`, `WorkerAgent`) each repeat significant structural boilerplate that is semantically identical across all of them. This violates DRY and makes the execution contract harder to evolve -- any change to the tracing setup, message format, or response construction must be replicated in three places.

The `AgentBase` ABC currently provides:
- `__init__` (LLM client, tool registry, execution components)
- `add_tool`, `remove_tool`, `get_tool_names`, `has_tool`
- Abstract `run()`

It does **not** provide any shared execution helpers, leaving each subclass to independently implement the same patterns for tracing, message building, result construction, and token management.

---

## 2. Overlap Inventory

### 2.1 Langfuse Observation Wrapping

**Where:** Every `run()` method opens a Langfuse observation span with the same structure.

| File | Lines |
|------|-------|
| `agent.py` | 191-196 |
| `planner_agent.py` | 47-52 |
| `worker_agent.py` | 77-82 |

**Repeated code (6 lines per agent, 18 total):**

```python
with self.langfuse.start_as_current_observation(
    as_type="agent",
    name="<agent_name>.run",
    input=<task_or_message>,
    metadata={"provider": self.provider, "model": self.model},
) as run_span:
```

**Variation:** Only `name` and `input` differ. The `as_type` and `metadata` dict are always identical.

**Risk of divergence:** If we add a new metadata field (e.g. `max_iterations`, `session_id`), we must update all three. If one is missed, observability becomes inconsistent.

---

### 2.2 Langfuse Attribute Propagation + Execution

**Where:** All three agents wrap `self.execution_loop.execute()` in `propagate_attributes`.

| File | Lines |
|------|-------|
| `agent.py` | 249-259 |
| `planner_agent.py` | 73-78 |
| `worker_agent.py` | 91-96 |

**Repeated code (8 lines per agent, 24 total):**

```python
with propagate_attributes(
    trace_name=<name>,
    session_id=self.session_id,
    tags=[<AgentType>, self.provider],
    metadata={"model": self.model, ...},
):
    result = self.execution_loop.execute()
```

**Variation:** `trace_name` and `tags` differ. Everything else is identical.

**Risk of divergence:** Same as 2.1. Adding a new tag or metadata key requires three edits. The `Agent` version also passes `max_iterations` in metadata while `PlannerAgent` and `WorkerAgent` do not -- this is already an inconsistency.

---

### 2.3 AgentResponse Construction

**Where:** `Agent` and `WorkerAgent` build `AgentResponse` from the execution result dict.

| File | Lines |
|------|-------|
| `agent.py` | 283-293 |
| `worker_agent.py` | 100-108 |

**Repeated code (8 lines per agent, 16 total):**

```python
AgentResponse(
    answer=result["answer"],
    tool_calls_made=result["tool_calls"],
    tokens_used=result["total_tokens"],
    cache_creation_input_tokens=result["cache_creation_input_tokens"],
    cache_read_input_tokens=result["cache_read_input_tokens"],
    iterations=result["iterations"],
    stop_reason=result["stop_reason"],
)
```

**Variation:** `Agent` adds `plan` and `parsed_output` kwargs. `WorkerAgent` uses the bare form.

**Risk of divergence:** If `AgentResponse` gains a new field or a result dict key is renamed, both locations must be updated in lockstep.

---

### 2.4 Tool List Registration Loop

**Where:** `Agent` and `WorkerAgent` iterate a `tools` list to register callables.

| File | Lines |
|------|-------|
| `agent.py` | 99-101 |
| `worker_agent.py` | 70-72 |

**Repeated code (3 lines per agent, 6 total):**

```python
if tools:
    for func in tools:
        self.add_tool(**func.tool)
```

**Variation:** None. Completely identical.

---

### 2.5 `llm_web_search` Registration

**Where:** Both `Agent` and `WorkerAgent` register the web search tool.

| File | Lines |
|------|-------|
| `agent.py` | 126 |
| `worker_agent.py` | 67 |

**Repeated code:** `self.add_tool(**llm_web_search.tool)` -- single line, two locations.

**Note:** `PlannerAgent` does **not** register this tool. Moving it into the base class would over-provision the planner. This is intentional -- planners don't need web search. Best left as-is or handled via a flag, but the ROI on centralizing a single line is low.

---

### 2.6 Message List Construction

**Where:** All three agents build `self.messages` as `[system, ...history, user]`.

| File | Lines | Method |
|------|-------|--------|
| `agent.py` | 144-171 | `build_messages()` (public method) |
| `planner_agent.py` | 68-71 | Inline |
| `worker_agent.py` | 86-89 | Inline |

**Pattern:**

```python
messages = [{"role": "system", "content": <system_prompt>}]
# optionally: messages.extend(conversation_history)
messages.append({"role": "user", "content": <user_content>})
```

**Variation:** `Agent` supports `conversation_history` and has prompt-selection logic. `PlannerAgent` and `WorkerAgent` never use history.

**Risk of divergence:** The message format (role names, structure) is an implicit contract with the LLM providers. If the format changes, all three must update.

---

### 2.7 Token Counter Reset

**Where:** Only `Agent` resets counters before execution.

| File | Lines |
|------|-------|
| `agent.py` | 199-201 |

**Code:**

```python
self.total_tokens = 0
self.cache_creation_input_tokens = 0
self.cache_read_input_tokens = 0
```

`PlannerAgent` and `WorkerAgent` skip this. They're typically single-use, so it doesn't cause bugs today. But it's an inconsistency -- if a `WorkerAgent` were ever reused across multiple `run()` calls, token counts would accumulate incorrectly.

---

## 3. Proposed Base Methods

### 3.1 `register_tools(tools: List[Callable]) -> None`

**Replaces:** The `if tools: for func in tools:` loop in Agent and Worker.

```python
def register_tools(self, tools: List[Callable]) -> None:
    """Bulk-register a list of @agent_tool-decorated callables."""

    for func in tools:
        self.add_tool(**func.tool)
```

**Callers:** `Agent.__init__`, `WorkerAgent.__init__`

---

### 3.2 `_observe(span_name: str, input: Any)` context manager

**Replaces:** The `langfuse.start_as_current_observation` block in all three `run()` methods.

```python
@contextmanager
def _observe(self, span_name: str, input: Any):
    """Wrap a run in a Langfuse observation span.

    Yields the span so the caller can call span.update(output=...) before exit.
    """

    with self.langfuse.start_as_current_observation(
        as_type="agent",
        name=span_name,
        input=input,
        metadata={"provider": self.provider, "model": self.model},
    ) as span:

        yield span
```

**Callers:** All three `run()` methods. Each passes its own `span_name` and `input`.

---

### 3.3 `_execute_with_tracing(trace_name: str) -> Dict[str, Any]`

**Replaces:** The `propagate_attributes` + `execution_loop.execute()` block in all three agents.

```python
def _execute_with_tracing(self, trace_name: str) -> Dict[str, Any]:
    """Run the execution loop inside Langfuse attribute propagation."""

    with propagate_attributes(
        trace_name=trace_name,
        session_id=self.session_id,
        tags=[trace_name, self.provider],
        metadata={
            "model": self.model,
            "provider": self.provider,
            "max_iterations": str(self.max_iterations),
        },
    ):
        return self.execution_loop.execute()
```

**Callers:** All three `run()` methods.

**Side benefit:** Fixes the current inconsistency where `Agent` passes `max_iterations` in metadata but `PlannerAgent` and `WorkerAgent` do not. Now all agents get it automatically.

---

### 3.4 `_reset_counters() -> None`

**Replaces:** The 3-line token reset block in `Agent.run()`.

```python
def _reset_counters(self) -> None:
    """Reset token counters before a new run."""

    self.total_tokens = 0
    self.cache_creation_input_tokens = 0
    self.cache_read_input_tokens = 0
```

**Callers:** `Agent.run()` explicitly. `PlannerAgent` and `WorkerAgent` can adopt it for consistency if reuse becomes a concern.

---

### 3.5 `_build_messages(system_prompt, user_content, conversation_history=None) -> List[Dict]`

**Replaces:** Inline message list construction in all three agents. Replaces Agent's public `build_messages()` method.

```python
def _build_messages(
    self,
    system_prompt: Any,
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

**Callers:** All three agents. Agent's `build_messages()` becomes a thin wrapper that resolves the system prompt (Anthropic blocks vs string) and then delegates to `_build_messages`.

**Note:** The prompt-selection logic (Anthropic blocks, plan injection) stays in `Agent` -- only the mechanical list construction moves to base.

---

### 3.6 `_build_response(result, **extras) -> AgentResponse` static method

**Replaces:** The `AgentResponse(...)` construction in Agent and Worker.

```python
@staticmethod
def _build_response(result: Dict[str, Any], **extras) -> AgentResponse:
    """Build an AgentResponse from an execution loop result dict.

    Args:
        result: The dict returned by ExecutionLoop.execute().
        **extras: Additional kwargs forwarded to AgentResponse (e.g. plan, parsed_output).
    """

    return AgentResponse(
        answer=result["answer"],
        tool_calls_made=result["tool_calls"],
        tokens_used=result["total_tokens"],
        cache_creation_input_tokens=result["cache_creation_input_tokens"],
        cache_read_input_tokens=result["cache_read_input_tokens"],
        iterations=result["iterations"],
        stop_reason=result["stop_reason"],
        **extras,
    )
```

**Callers:**
- `Agent.run()`: `self._build_response(result, plan=self.plan, parsed_output=parsed_output)`
- `WorkerAgent.run()`: `self._build_response(result)`

**Note:** `PlannerAgent` does not return `AgentResponse` -- it returns `Plan`. This method is not used by PlannerAgent, which is correct.

---

## 4. Subclass Impact: Before vs After

### 4.1 WorkerAgent.run()

**Before (32 lines):**

```python
def run(self) -> AgentResponse:

    with self.langfuse.start_as_current_observation(
        as_type="agent",
        name="worker_agent.run",
        input=self.task,
        metadata={"provider": self.provider, "model": self.model},
    ) as run_span:

        worker_prompt = self._build_system_prompt()

        self.messages = [
            {"role": "system", "content": worker_prompt},
            {"role": "user", "content": self.task},
        ]

        with propagate_attributes(
            session_id=self.session_id,
            tags=["WorkerAgent", self.provider],
            metadata={"model": self.model}
        ):
            result = self.execution_loop.execute()

        run_span.update(output=result["answer"])

        return AgentResponse(
            answer=result["answer"],
            tool_calls_made=result["tool_calls"],
            tokens_used=result["total_tokens"],
            cache_creation_input_tokens=result["cache_creation_input_tokens"],
            cache_read_input_tokens=result["cache_read_input_tokens"],
            iterations=result["iterations"],
            stop_reason=result["stop_reason"]
        )
```

**After (10 lines):**

```python
def run(self) -> AgentResponse:

    with self._observe("worker_agent.run", self.task) as run_span:

        self.messages = self._build_messages(self._build_system_prompt(), self.task)

        result = self._execute_with_tracing("WorkerAgent")

        run_span.update(output=result["answer"])

        return self._build_response(result)
```

**Reduction:** 32 -> 10 lines (**69% reduction**)

---

### 4.2 PlannerAgent.run()

**Before (41 lines):**

```python
def run(self) -> Plan:

    with self.langfuse.start_as_current_observation(
        as_type="agent",
        name="planner_agent.run",
        input=self.task,
        metadata={"provider": self.provider, "model": self.model},
    ) as run_span:

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

        self.messages = [
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        with propagate_attributes(
            session_id=self.session_id,
            tags=["PlannerAgent", self.provider],
            metadata={"model": self.model},
        ):
            response = self.execution_loop.execute()

        plan = parse_with_gpt(
            response["answer"],
            target_model=Plan,
        )

        run_span.update(output=plan.model_dump())

        return plan
```

**After (20 lines):**

```python
def run(self) -> Plan:

    with self._observe("planner_agent.run", self.task) as run_span:

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

        result = self._execute_with_tracing("PlannerAgent")

        plan = parse_with_gpt(result["answer"], target_model=Plan)

        run_span.update(output=plan.model_dump())

        return plan
```

**Reduction:** 41 -> 20 lines (**51% reduction**)

---

### 4.3 Agent.run()

**Before (100 lines):**

The full `run()` method in `agent.py` spans lines 173-301.

**After (~65 lines):**

The planning phase, prompt selection, and structured output parsing stay in Agent since they are Agent-specific logic. The savings come from:

- `self._observe(...)` replaces 6-line observation block
- `self._reset_counters()` replaces 3-line inline reset
- `self._build_messages(...)` replaces public `build_messages()` call
- `self._execute_with_tracing(...)` replaces 10-line propagation block
- `self._build_response(result, ...)` replaces 11-line AgentResponse construction

Additionally, `Agent.build_messages()` (the public method at lines 144-171) can be simplified since the mechanical construction delegates to `_build_messages`. The prompt-selection logic (Anthropic blocks check) stays but becomes a thin resolver.

**Reduction:** ~100 -> ~65 lines (**35% reduction**)

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

Minor but consistent.

---

## 5. What NOT to Centralize

### 5.1 `llm_web_search` registration

Both `Agent` and `WorkerAgent` register it, but `PlannerAgent` does not. Moving it to base would give the planner a tool it doesn't need. Since it's a single line, the duplication cost is negligible.

### 5.2 Anthropic prompt-block handling

The logic for choosing between `system_prompt_blocks` (Anthropic) vs `system_prompt` (OpenAI/others) is Agent-specific behavior tied to its multi-turn, deferred-tools architecture. `WorkerAgent` handles this in `_build_system_prompt()` which has different logic (date injection). These should stay in their respective classes.

### 5.3 Planning phase logic

Plan creation, plan injection, update_plan tool registration/teardown -- all Agent-specific. No other agent type plans.

### 5.4 Deferred tools / register_tools tool

Only Agent supports deferred tool loading via the `register_tools` built-in tool. This is a feature of the Agent class, not a base concern.

---

## 6. Implementation Checklist

- [ ] **`base.py`**: Add `register_tools()`, `_observe()`, `_execute_with_tracing()`, `_reset_counters()`, `_build_messages()`, `_build_response()`
- [ ] **`base.py`**: Add `from contextlib import contextmanager` and `from langfuse import propagate_attributes` imports
- [ ] **`base.py`**: Add `AgentResponse` to imports from `prophitai_atlas.models`
- [ ] **`worker_agent.py`**: Refactor `__init__` to use `self.register_tools(tools)`
- [ ] **`worker_agent.py`**: Refactor `run()` to use `_observe`, `_build_messages`, `_execute_with_tracing`, `_build_response`
- [ ] **`planner_agent.py`**: Refactor `run()` to use `_observe`, `_build_messages`, `_execute_with_tracing`
- [ ] **`agent.py`**: Refactor `__init__` to use `self.register_tools(tools)`
- [ ] **`agent.py`**: Refactor `run()` to use `_observe`, `_reset_counters`, `_build_messages`, `_execute_with_tracing`, `_build_response`
- [ ] **`agent.py`**: Collapse or remove public `build_messages()` if no external callers depend on it
- [ ] **Verify**: Check if `build_messages()` is called externally (outside of `agent.py`) before removing
- [ ] **Test**: Run existing agent tests to confirm no behavioral changes
- [ ] **Test**: Run a real Agent chat turn, a plan-first run, and a standalone WorkerAgent run

---

## 7. Metrics

| Metric | Before | After |
|--------|--------|-------|
| Total duplicated lines across subclasses | ~72 | 0 |
| WorkerAgent.run() line count | 32 | 10 |
| PlannerAgent.run() line count | 41 | 20 |
| Agent.run() line count | ~100 | ~65 |
| New base methods | 0 | 6 |
| New base method total lines | 0 | ~55 |
| Net line reduction | -- | ~17 lines fewer overall |

The net line count reduction is modest because the boilerplate moves into base methods rather than disappearing. The real win is **single-source-of-truth**: tracing setup, message format, and response construction are each defined once and evolved in one place.

---

## 8. Risk Assessment

**Risk: Breaking the execution contract**  
The `ExecutionLoop` and `ToolHandler` read from `self.messages`, `self.tools`, `self.tool_functions`, etc. None of the proposed changes alter these attributes or their structure. The base methods are pure wrappers around existing calls.  
**Mitigation:** Run a real end-to-end agent turn after refactoring, not just unit tests.

**Risk: Anthropic provider-specific behavior**  
The `_build_messages` method treats `system_prompt` as opaque `Any`. Anthropic's block format (list of dicts with `cacheable` flags) is passed through unchanged. This matches current behavior.  
**Mitigation:** Verify Anthropic cache hits are preserved after refactoring.

**Risk: `build_messages()` external callers**  
If any code outside `agent.py` calls `agent.build_messages()`, removing it would break. Must grep before removing.  
**Mitigation:** `grep -r "build_messages" --include="*.py"` across the repo.
