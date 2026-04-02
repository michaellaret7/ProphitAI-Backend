# Architectural Spec: Observability Callback Pattern

## Problem

The `ExecutionLoop` and `ToolHandler` are cluttered with Langfuse tracing logic (`start_as_current_observation`, `span.update`, context managers) interleaved with core execution logic. This creates:

1. **Mixed concerns** - execution flow + observability in the same methods
2. **Rigid coupling** - swapping/disabling tracing requires touching core execution code
3. **Duplication** - three parallel notification systems (Langfuse, ChatCallback, AgentPrinter) all triggered at the same lifecycle points

## Current State

```
ExecutionLoop.execute()
├── langfuse.start_as_current_observation("chain")     # Langfuse
├── callback.on_run_started()                          # ChatCallback
├── for each iteration:
│   ├── langfuse.start_as_current_observation("span")  # Langfuse
│   ├── iteration_span.update(input=...)               # Langfuse
│   ├── callback.on_iteration_start()                  # ChatCallback
│   ├── printer.iteration_start()                      # AgentPrinter
│   ├── ... core logic ...
│   ├── iteration_span.update(output=...)              # Langfuse
│   ├── callback.on_iteration_end()                    # ChatCallback
│   └── printer.iteration_complete()                   # AgentPrinter
├── loop_span.update(output=...)                       # Langfuse
└── callback.on_run_finished()                         # ChatCallback

ToolHandler._execute_tool()
├── langfuse.start_as_current_observation("tool")      # Langfuse
├── tool_span.update(input=...)                        # Langfuse
├── ... execute tool ...
├── tool_span.update(output=...)                       # Langfuse
├── callback.on_tool_call_start()                      # ChatCallback (caller)
└── callback.on_tool_call_result()                     # ChatCallback (caller)
```

Three systems, same lifecycle hooks, all inline.

---

## Proposed Architecture

### Core Idea

Unify all observability behind the `ChatCallback` protocol. The `ExecutionLoop` and `ToolHandler` emit lifecycle events through a **single callback interface**. Langfuse tracing becomes just another callback implementation, composed alongside WebSocket streaming.

### New Component: `LangfuseCallback`

A `ChatCallback` implementation that owns all Langfuse span management internally.

```python
class LangfuseCallback:
    """ChatCallback implementation that manages Langfuse tracing.
    
    Translates ChatCallback lifecycle events into Langfuse spans:
        on_run_started   -> opens "execution_loop" chain span
        on_iteration_start -> opens "iteration_{i}" span
        on_tool_call_start -> opens "tool: {name}" span
        on_tool_call_result -> closes tool span with output
        on_iteration_end -> closes iteration span with output
        on_run_finished  -> closes chain span with output
        on_run_error     -> closes all spans with error
    """

    def __init__(self, langfuse_client, agent_metadata: dict):
        self._langfuse = langfuse_client
        self._agent_metadata = agent_metadata
        
        # Span stack - managed internally
        self._loop_span = None
        self._iteration_span = None
        self._tool_spans: dict[str, Any] = {}  # tool_call_id -> span
        
        # Accumulator for iteration output
        self._iteration_tools: list[str] = []

    def on_run_started(self, session_id: str, message_id: str) -> None:
        self._loop_span = self._langfuse.start_as_current_observation(
            as_type="chain",
            name="execution_loop",
            input=self._agent_metadata,
        )
        self._loop_span.__enter__()

    def on_iteration_start(self, iteration: int) -> None:
        self._iteration_tools = []
        self._iteration_span = self._langfuse.start_as_current_observation(
            as_type="span",
            name=f"iteration_{iteration}",
        )
        self._iteration_span.__enter__()
        self._iteration_span.update(
            input={"iteration": iteration},
            metadata={"iteration": str(iteration)},
        )

    def on_tool_call_start(self, tool_call_id: str, tool_name: str,
                           arguments: dict, iteration: int) -> None:
        span = self._langfuse.start_as_current_observation(
            as_type="tool",
            name=f"tool: {tool_name}",
        )
        span.__enter__()
        span.update(input=arguments, metadata={"tool_name": tool_name})
        self._tool_spans[tool_call_id] = span
        self._iteration_tools.append(tool_name)

    def on_tool_call_result(self, tool_call_id: str, tool_name: str,
                            result: Any, success: bool, duration_ms: int) -> None:
        span = self._tool_spans.pop(tool_call_id, None)
        if span:
            if success:
                span.update(output=result)
            else:
                span.update(level="ERROR", output=result)
            span.__exit__(None, None, None)

    def on_iteration_end(self, iteration: int, tokens_used: int) -> None:
        if self._iteration_span:
            self._iteration_span.update(output={
                "tools_called": self._iteration_tools,
                "tokens_used": tokens_used,
            })
            self._iteration_span.__exit__(None, None, None)
            self._iteration_span = None

    def on_run_finished(self, answer: str, tool_calls_made: list[str],
                        iterations: int, tokens_used: int, stop_reason: str) -> None:
        if self._loop_span:
            self._loop_span.update(output={
                "stop_reason": stop_reason,
                "iterations": iterations,
                "total_tokens": tokens_used,
            })
            self._loop_span.__exit__(None, None, None)
            self._loop_span = None

    def on_run_error(self, error: str) -> None:
        # Close any open spans with error state
        for span in self._tool_spans.values():
            span.update(level="ERROR", error=error)
            span.__exit__(None, None, None)
        self._tool_spans.clear()

        if self._iteration_span:
            self._iteration_span.update(level="ERROR", error=error)
            self._iteration_span.__exit__(None, None, None)
            self._iteration_span = None

        if self._loop_span:
            self._loop_span.update(level="ERROR", error=error)
            self._loop_span.__exit__(None, None, None)
            self._loop_span = None

    def on_plan_created(self, plan: Any) -> None:
        pass

    def on_plan_updated(self, plan: Any) -> None:
        pass
```

### New Component: `CompositeCallback`

Fans out events to multiple callbacks (WebSocket + Langfuse + any future ones).

```python
class CompositeCallback:
    """Dispatches lifecycle events to multiple ChatCallback implementations."""

    def __init__(self, *callbacks):
        self._callbacks = [cb for cb in callbacks if cb is not None]

    def on_run_started(self, session_id: str, message_id: str) -> None:
        for cb in self._callbacks:
            cb.on_run_started(session_id=session_id, message_id=message_id)

    def on_iteration_start(self, iteration: int) -> None:
        for cb in self._callbacks:
            cb.on_iteration_start(iteration=iteration)

    def on_tool_call_start(self, tool_call_id: str, tool_name: str,
                           arguments: dict, iteration: int) -> None:
        for cb in self._callbacks:
            cb.on_tool_call_start(
                tool_call_id=tool_call_id, tool_name=tool_name,
                arguments=arguments, iteration=iteration,
            )

    def on_tool_call_result(self, tool_call_id: str, tool_name: str,
                            result: Any, success: bool, duration_ms: int) -> None:
        for cb in self._callbacks:
            cb.on_tool_call_result(
                tool_call_id=tool_call_id, tool_name=tool_name,
                result=result, success=success, duration_ms=duration_ms,
            )

    def on_iteration_end(self, iteration: int, tokens_used: int) -> None:
        for cb in self._callbacks:
            cb.on_iteration_end(iteration=iteration, tokens_used=tokens_used)

    def on_run_finished(self, answer: str, tool_calls_made: list[str],
                        iterations: int, tokens_used: int, stop_reason: str) -> None:
        for cb in self._callbacks:
            cb.on_run_finished(
                answer=answer, tool_calls_made=tool_calls_made,
                iterations=iterations, tokens_used=tokens_used,
                stop_reason=stop_reason,
            )

    def on_run_error(self, error: str) -> None:
        for cb in self._callbacks:
            cb.on_run_error(error=error)

    def on_plan_created(self, plan: Any) -> None:
        for cb in self._callbacks:
            cb.on_plan_created(plan=plan)

    def on_plan_updated(self, plan: Any) -> None:
        for cb in self._callbacks:
            cb.on_plan_updated(plan=plan)
```

---

## Wiring: AgentBase

```python
class AgentBase:
    def __init__(self, ..., chat_callback=None):
        self.langfuse = get_client()

        # Build composite callback
        langfuse_cb = LangfuseCallback(
            langfuse_client=self.langfuse,
            agent_metadata={
                "agent": self.__class__.__name__,
                "model": self.model,
                "max_iterations": self.max_iterations,
                "tools": self.get_tool_names(),
            },
        )

        user_cb = chat_callback or NoOpChatCallback()

        self.chat_callback = CompositeCallback(user_cb, langfuse_cb)
```

No other code changes needed in AgentBase. The composite callback replaces the single callback, and the rest of the system works through the same `ChatCallback` protocol.

---

## Cleaned Execution Loop (After)

```python
class ExecutionLoop:
    def execute(self, message_id: Optional[str] = None) -> Dict[str, Any]:
        message_id = message_id or str(uuid.uuid4())
        callback = self.agent.chat_callback

        tool_calls_made: List[str] = []
        assistant_text = ""
        iteration_tokens = 0

        callback.on_run_started(
            session_id=self.agent.session_id,
            message_id=message_id,
        )

        try:
            for i in range(1, self.agent.max_iterations + 1):
                self.agent.tool_handler.current_iteration = i

                callback.on_iteration_start(iteration=i)
                self.printer.iteration_start(i, self.agent.max_iterations)

                response = self.call_llm()
                iteration_tokens = self._track_token_usage(response)
                assistant_text = response.assistant_text

                if response.tool_calls:
                    called_tools = self._handle_tool_calls(
                        response.tool_calls, assistant_text
                    )
                    tool_calls_made.extend(called_tools)
                    callback.on_iteration_end(iteration=i, tokens_used=iteration_tokens)
                else:
                    self.agent.messages.append({
                        "role": "assistant",
                        "content": assistant_text,
                    })
                    callback.on_iteration_end(iteration=i, tokens_used=iteration_tokens)
                    self.printer.iteration_complete(i, "answer_ready")

                    result = {
                        "answer": assistant_text,
                        "tool_calls": tool_calls_made,
                        "total_tokens": self.agent.total_tokens,
                        "iterations": i,
                        "stop_reason": "answer_ready",
                    }
                    callback.on_run_finished(
                        answer=assistant_text,
                        tool_calls_made=tool_calls_made,
                        iterations=i,
                        tokens_used=self.agent.total_tokens,
                        stop_reason="answer_ready",
                    )
                    return result

            # Max iterations
            callback.on_iteration_end(
                iteration=self.agent.max_iterations,
                tokens_used=iteration_tokens,
            )
            self.printer.iteration_complete(self.agent.max_iterations, "max_iterations")

            final_answer = (
                assistant_text if assistant_text
                else "Unable to complete request within iteration limit."
            )

            result = {
                "answer": final_answer,
                "tool_calls": tool_calls_made,
                "total_tokens": self.agent.total_tokens,
                "iterations": self.agent.max_iterations,
                "stop_reason": "max_iterations",
            }
            callback.on_run_finished(
                answer=final_answer,
                tool_calls_made=tool_calls_made,
                iterations=self.agent.max_iterations,
                tokens_used=self.agent.total_tokens,
                stop_reason="max_iterations",
            )
            return result

        except Exception as e:
            callback.on_run_error(error=str(e))
            raise
```

**What changed**: Zero Langfuse imports, zero `with` blocks, zero `span.update()` calls. Pure execution logic.

---

## Cleaned ToolHandler._execute_tool (After)

```python
def _execute_tool(self, name: str, args: Dict[str, Any]) -> Any:
    func = self.agent.tool_functions.get(name)
    if not func:
        error_msg = f"Tool '{name}' not found. Available: {list(self.agent.tool_functions.keys())}"
        self.printer.tool_error(error_msg)
        return error_response(error_msg)

    try:
        execution_args = args.copy()
        if (
            "_clerk_id" not in execution_args
            and hasattr(self.agent, "user_id")
            and self.agent.user_id
        ):
            if self._accepts_hidden_clerk_id(func):
                execution_args["_clerk_id"] = self.agent.user_id

        return func(**execution_args)

    except Exception as e:
        error_msg = f"Error executing {name}: {str(e)}"
        self.printer.tool_error(error_msg)
        return error_response(error_msg)
```

Langfuse tool spans are now managed by `LangfuseCallback.on_tool_call_start/result` — the ToolHandler just executes tools.

---

## File Changes Summary

| File | Change |
|------|--------|
| `models/callbacks.py` | Add `LangfuseCallback`, `CompositeCallback` |
| `agents/base.py` | Wire `CompositeCallback(user_cb, langfuse_cb)` in `__init__` |
| `execution/loop.py` | Remove all `langfuse` imports and `with` blocks |
| `execution/tool_handler.py` | Remove `langfuse` span from `_execute_tool` |

---

## Key Design Decisions

### Why extend ChatCallback instead of a separate ObservabilityCallback?

The lifecycle hooks are identical. Creating a second protocol with the same methods violates DRY. The `ChatCallback` protocol is already the right abstraction — "something that wants to know about agent lifecycle events." Langfuse is just another consumer.

### Why CompositeCallback instead of a list?

A composite gives you a single object that satisfies the `ChatCallback` protocol. No need to loop through callbacks at every call site. The loop and tool handler just call `self.callback.on_*()` — they don't know or care how many listeners exist.

### Why not just subclass WebSocketChatCallback?

WebSocket streaming and Langfuse tracing are independent concerns. Composing them keeps each focused on one job. You can run Langfuse without WebSocket (tests, CLI), WebSocket without Langfuse (if tracing is off), or both.

### What about the AgentPrinter?

The printer stays separate for now. It's console-only debug output with different verbosity modes (`PRODUCTION`, `VERBOSE`, `DEBUG`). It could become a third callback in the composite, but that's a separate refactor — and the printer's conditional verbosity logic makes it a less clean fit for the protocol.

### What about tool error detection in LangfuseCallback?

Currently `_execute_tool` inspects the result dict for `success: False` to set `level="ERROR"` on the span. After the refactor, `on_tool_call_result` receives `success: bool` directly — cleaner than parsing YAML in the span logic.

### What about the outer agent-level span?

`Agent.run()`, `PlannerAgent.run()`, and `WorkerAgent.run()` each have their own Langfuse `start_as_current_observation(as_type="agent")` wrapping. This spec doesn't touch those — they're one-liners at the agent entry point and don't clutter execution logic. If you want to unify those too, the same pattern applies: add `on_agent_started` / `on_agent_finished` hooks to the protocol.
