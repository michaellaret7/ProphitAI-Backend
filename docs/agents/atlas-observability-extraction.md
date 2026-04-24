# Atlas Observability Extraction

**Status:** Draft Proposal  
**Date:** 2026-04-24  
**Scope:** `packages/atlas/src/prophitai_atlas/`  

---

## 1. Problem Statement

Atlas agent, execution, and tool code currently contains direct Langfuse and OpenTelemetry plumbing. The observability is important and must remain intact, but the implementation detail is mixed into files that should primarily express agent behavior.

The goal is to move vendor-specific observability code into a dedicated Atlas observability layer, while preserving the current Langfuse span names, metadata, trace/session behavior, and tool tracing semantics.

This is a pure refactor. It should not change agent behavior, trace shape, tool behavior, model calls, or harness-review visibility.

---

## 2. Current Coupling

Direct Langfuse/OpenTelemetry usage currently appears in:

| File | Current Concern |
|------|-----------------|
| `agents/base.py` | Creates `self.langfuse = get_client()` |
| `agents/agent.py` | Agent run span and `propagate_attributes(...)` |
| `agents/planner_agent.py` | Planner run span and `propagate_attributes(...)` |
| `agents/worker_agent.py` | Worker run span and `propagate_attributes(...)` |
| `execution/loop.py` | Execution-loop span and per-iteration spans |
| `execution/tool_handler.py` | Tool spans and OpenTelemetry thread context propagation |

This makes unrelated logic harder to edit:

- Agent classes mix prompt/planning/response logic with trace setup.
- `ExecutionLoop` mixes ReAct control flow with span lifecycle.
- `ToolHandler` mixes tool execution with Langfuse and OpenTelemetry mechanics.

---

## 3. Design Decision

Create a dedicated observability package:

```text
packages/atlas/src/prophitai_atlas/observability/
    __init__.py
    langfuse_observer.py
    noop_observer.py
```

Production Atlas agents should always use the real Langfuse-backed observer. A no-op/fake observer may exist for tests, but it is not a normal runtime option.

`AgentBase` owns construction of the production observer and passes it directly to execution components:

```python
self.observer = LangfuseObserver()
self.tool_handler = ToolHandler(self, self.printer, observer=self.observer)
self.execution_loop = ExecutionLoop(self, observer=self.observer)
```

Reason: observability remains always-on in production, while `ExecutionLoop` and `ToolHandler` receive their dependency explicitly instead of reaching back through `agent.langfuse`.

---

## 4. Observer API

The observer should expose Atlas-domain methods, not Langfuse-shaped generic span calls.

Recommended public surface:

```python
class LangfuseObserver:
    def agent_run(self, *, name, input, provider, model): ...
    def trace_context(self, *, session_id, tags, metadata, trace_name=None): ...
    def execution_loop(self, *, input): ...
    def iteration(self, *, number, input): ...
    def tool(self, *, name, args): ...
    def current_context(self): ...
    def attach_context(self, context): ...
```

The intent is that Atlas code reads like Atlas code:

```python
with observer.tool(name=name, args=args) as tool_span:
    result = func(**execution_args)
```

instead of:

```python
with langfuse.start_as_current_observation(as_type="tool", name=f"tool: {name}") as span:
    ...
```

---

## 5. Trace Context Boundary

Keep trace/session propagation visible at the agent boundary, but hide Langfuse's `propagate_attributes(...)` implementation.

Agent code should use:

```python
with self.observer.trace_context(
    trace_name=trace_name,
    session_id=self.session_id,
    tags=[trace_name, self.provider],
    metadata={
        "model": self.model,
        "provider": self.provider,
        "max_iterations": str(self.max_iterations),
    },
):
    result = self.execution_loop.execute()
```

Reason: the concrete agent knows the session, tags, provider/model metadata, and optional trace name. The execution loop should not infer whether it is running as `Agent`, an `Agent` subclass, `PlannerAgent`, or `WorkerAgent`.

---

## 6. Behavior Preservation Rules

This refactor must preserve current observability behavior exactly.

### 6.1 Agent Run Spans

Keep existing span names:

| Agent | Span Name |
|-------|-----------|
| `Agent.run(plan_first=False)` | `agent.run` |
| `Agent.run(plan_first=True)` | `agent.run_planned` |
| `PlannerAgent.run()` | `planner_agent.run` |
| `WorkerAgent.run()` | `worker_agent.run` |

Keep existing run-span metadata shape:

```python
{"provider": self.provider, "model": self.model}
```

Keep existing output shapes:

| Agent | Output |
|-------|--------|
| `Agent` | dict containing answer, tool calls, tokens, cache tokens, iterations, stop reason |
| `PlannerAgent` | `plan.model_dump()` |
| `WorkerAgent` | answer string |

### 6.2 Trace Context Metadata

Preserve current per-agent `propagate_attributes(...)` values.

`Agent`:

```python
trace_name = self.get_trace_name(planned=plan_first)
session_id = self.session_id
tags = [trace_name, self.provider]
metadata = {
    "model": self.model,
    "provider": self.provider,
    "max_iterations": str(self.max_iterations),
}
```

`PlannerAgent`:

```python
trace_name = self.get_trace_name()
session_id = self.session_id
tags = [trace_name, self.provider]
metadata = {"model": self.model}
```

`WorkerAgent`:

```python
trace_name = self.get_trace_name()
session_id = self.session_id
tags = [trace_name, self.provider]
metadata = {"model": self.model}
```

Do not standardize planner/worker metadata beyond deriving trace names and matching tags from the concrete class.

### 6.3 Execution Loop Spans

Keep the execution-loop observation:

```python
as_type = "chain"
name = "execution_loop"
input = {
    "agent": self.agent.__class__.__name__,
    "model": self.agent.model,
    "max_iterations": self.agent.max_iterations,
    "message_count": len(self.agent.messages),
    "tools": self.agent.get_tool_names(),
}
```

Keep the current loop output fields for `answer_ready` and `max_iterations`.

### 6.4 Iteration Spans

Keep current span names:

```python
name = f"iteration_{i}"
as_type = "span"
metadata = {"iteration": str(i)}
```

Keep current input/output payloads.

### 6.5 Tool Spans

Preserve current behavior: the tool span wraps raw function execution only.

The span should include:

```python
as_type = "tool"
name = f"tool: {name}"
input = args
metadata = {"tool_name": name}
```

The span should record:

- raw tool result on success
- `level="ERROR"` when the tool returns a `{"success": false}`-style result
- `level="ERROR"`, `error=str(e)`, and error output when function execution raises

Do not include validation results in the tool span in this pass. Validation currently happens after raw execution and should remain outside the span.

### 6.6 Parallel Tool Context

Move OpenTelemetry context propagation behind the observer:

```python
parent_context = self.observer.current_context()

with self.observer.attach_context(parent_context):
    return self._execute_tool(name, args)
```

`ToolHandler` should not import `opentelemetry`.

---

## 7. Non-Goals

This refactor should not:

- Change Langfuse span names.
- Change Langfuse metadata shape.
- Standardize planner/worker trace metadata.
- Add validation spans.
- Change callback behavior.
- Change token accounting.
- Change model provider instrumentation in `prophitai_shared`.
- Move the observer into `prophitai_shared`.
- Make observability optional in production.

---

## 8. Implementation Plan

1. Add `prophitai_atlas/observability/`.
2. Implement `LangfuseObserver` with all direct `langfuse` and `opentelemetry` imports.
3. Implement `NoOpObserver` or a minimal fake for tests.
4. Update `AgentBase` to construct `LangfuseObserver`.
5. Pass `observer` directly into `ToolHandler` and `ExecutionLoop`.
6. Replace direct `self.langfuse` usage in agent classes with `self.observer.agent_run(...)`.
7. Replace direct `propagate_attributes(...)` usage with `self.observer.trace_context(...)`.
8. Replace direct Langfuse span usage in `ExecutionLoop`.
9. Replace direct Langfuse/OpenTelemetry usage in `ToolHandler`.
10. Remove Langfuse imports from `agents/` and `execution/`.

---

## 9. Suggested Tests

Add focused unit tests with a fake observer that records calls.

Recommended assertions:

- `Agent.run(plan_first=False)` opens `agent.run` and trace context named after the concrete agent class.
- `Agent.run(plan_first=True)` opens `agent.run_planned` and trace context named `{ConcreteAgentClass} (planned)`.
- `PlannerAgent.run()` uses `PlannerAgent` as its trace context name and first tag.
- `WorkerAgent.run()` uses `WorkerAgent` as its trace context name and first tag.
- `ExecutionLoop.execute()` opens `execution_loop` and `iteration_{i}` observations.
- `ToolHandler._execute_tool()` opens `tool: {name}` with `args` input.
- Parallel tools call `current_context()` and `attach_context(...)`.

Also run existing Atlas smoke tests after the refactor.

---

## 10. Success Criteria

The refactor is successful when:

- No `langfuse` imports remain under `prophitai_atlas/agents/`.
- No `langfuse` or `opentelemetry` imports remain under `prophitai_atlas/execution/`.
- Production agents still always create a Langfuse-backed observer.
- Existing Langfuse dashboards and harness review receive the same trace names and metadata.
- Agent, execution, and tool code read primarily as agent, execution, and tool logic.

