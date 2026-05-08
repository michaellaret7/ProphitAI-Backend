"""Callback protocols for streaming agent events.

Provides protocols for receiving notifications when agent state changes,
enabling real-time streaming to frontends via WebSocket or other mechanisms.
"""

from typing import Any, Dict, List, Protocol

from prophitai_atlas.utils.truncation import truncate_for_display


class ChatCallback(Protocol):
    """Protocol for streaming chat execution events to frontend.

    Implementations can stream these events to frontends via WebSocket,
    log them, or perform other actions during chat agent execution.

    Event flow:
        on_run_started -> (on_iteration_start -> [on_tool_call_start ->
        on_tool_call_result]* -> on_iteration_end)* -> on_run_finished
        OR on_run_error at any point
    """

    def on_run_started(self, session_id: str, message_id: str) -> None:
        ...

    def on_iteration_start(self, iteration: int) -> None:
        ...

    def on_iteration_end(self, iteration: int, tokens_used: int) -> None:
        ...

    def on_tool_call_start(
        self,
        tool_call_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        iteration: int,
    ) -> None:
        ...

    def on_tool_call_result(
        self,
        tool_call_id: str,
        tool_name: str,
        result: Any,
        success: bool,
        duration_ms: int,
    ) -> None:
        ...

    def on_run_finished(
        self,
        answer: str,
        tool_calls_made: List[str],
        iterations: int,
        tokens_used: int,
        stop_reason: str,
    ) -> None:
        ...

    def on_run_error(self, error: str) -> None:
        ...

    def on_plan_created(self, plan: Any) -> None:
        ...

    def on_plan_updated(self, plan: Any) -> None:
        ...


class NoOpChatCallback:
    """Default no-operation callback for chat agents.

    Used as the default chat_callback when no streaming is needed.
    All methods are no-ops that do nothing.
    """

    def on_run_started(self, session_id: str, message_id: str) -> None:
        pass

    def on_iteration_start(self, iteration: int) -> None:
        pass

    def on_iteration_end(self, iteration: int, tokens_used: int) -> None:
        pass

    def on_tool_call_start(
        self,
        tool_call_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        iteration: int,
    ) -> None:
        pass

    def on_tool_call_result(
        self,
        tool_call_id: str,
        tool_name: str,
        result: Any,
        success: bool,
        duration_ms: int,
    ) -> None:
        pass

    def on_run_finished(
        self,
        answer: str,
        tool_calls_made: List[str],
        iterations: int,
        tokens_used: int,
        stop_reason: str,
    ) -> None:
        pass

    def on_run_error(self, error: str) -> None:
        pass

    def on_plan_created(self, plan: Any) -> None:
        pass

    def on_plan_updated(self, plan: Any) -> None:
        pass


class WorkerCallbackWrapper:
    """Wraps a ChatCallback to tag worker events with task context.

    Reuses the inner callback's _send method to emit worker-prefixed
    event types (worker_tool_call_start, worker_tool_call_result, etc.)
    so the frontend can distinguish worker activity from orchestrator activity.
    """

    def __init__(
        self, inner_callback: Any,
        task_id: str, worker_id: str, plan_task_id: str = "",
    ):
        self._inner = inner_callback
        self._task_id = task_id
        self._worker_id = worker_id
        self._plan_task_id = plan_task_id

    def _send(self, event_type: str, payload: dict) -> None:
        """Delegate to inner callback's _send with identity fields injected."""
        if hasattr(self._inner, '_send'):
            payload["task_id"] = self._task_id
            payload["worker_id"] = self._worker_id
            payload["plan_task_id"] = self._plan_task_id
            self._inner._send(event_type, payload)

    # --- Events we forward with worker prefix ---

    def on_tool_call_start(self, tool_call_id: str, tool_name: str,
                           arguments: Dict[str, Any], iteration: int) -> None:
        self._send("worker_tool_call_start", {
            "tool_call_id": tool_call_id, "tool_name": tool_name,
            "arguments": arguments, "iteration": iteration,
        })

    def on_tool_call_result(self, tool_call_id: str, tool_name: str,
                            result: Any, success: bool, duration_ms: int) -> None:
        self._send("worker_tool_call_result", {
            "tool_call_id": tool_call_id, "tool_name": tool_name,
            "result": truncate_for_display(result), "success": success, "duration_ms": duration_ms,
        })

    def on_iteration_start(self, iteration: int) -> None:
        self._send("worker_iteration_start", {"iteration": iteration})

    def on_iteration_end(self, iteration: int, tokens_used: int) -> None:
        self._send("worker_iteration_end", {"iteration": iteration, "tokens_used": tokens_used})

    # --- Events we suppress (orchestrator already handles these) ---

    def on_run_started(self, session_id: str, message_id: str) -> None:
        pass

    def on_run_finished(self, answer: str, tool_calls_made: List[str],
                        iterations: int, tokens_used: int, stop_reason: str) -> None:
        pass

    def on_run_error(self, error: str) -> None:
        pass

    def on_plan_created(self, plan: Any) -> None:
        pass

    def on_plan_updated(self, plan: Any) -> None:
        pass
