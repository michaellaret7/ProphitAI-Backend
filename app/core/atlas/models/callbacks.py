"""Callback protocols for streaming agent events.

Provides protocols for receiving notifications when agent state changes,
enabling real-time streaming to frontends via WebSocket or other mechanisms.
"""

from typing import Any, Dict, List, Protocol


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
        """Called when agent starts processing a message.

        Args:
            session_id: The chat session identifier.
            message_id: Unique identifier for this user message.
        """
        ...

    def on_iteration_start(self, iteration: int) -> None:
        """Called at the start of each ReAct iteration.

        Args:
            iteration: The current iteration number (1-indexed).
        """
        ...

    def on_iteration_end(self, iteration: int, tokens_used: int) -> None:
        """Called at the end of each ReAct iteration.

        Args:
            iteration: The iteration number that just completed.
            tokens_used: Tokens consumed in this iteration.
        """
        ...

    def on_tool_call_start(
        self,
        tool_call_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        iteration: int,
    ) -> None:
        """Called when a tool execution begins.

        Args:
            tool_call_id: Unique identifier for this tool call.
            tool_name: Name of the tool being executed.
            arguments: Arguments passed to the tool.
            iteration: Current iteration number.
        """
        ...

    def on_tool_call_result(
        self,
        tool_call_id: str,
        tool_name: str,
        result: Any,
        success: bool,
        duration_ms: int,
    ) -> None:
        """Called when a tool execution completes.

        Args:
            tool_call_id: Unique identifier matching on_tool_call_start.
            tool_name: Name of the tool that was executed.
            result: The result returned by the tool.
            success: Whether the tool execution succeeded.
            duration_ms: Execution time in milliseconds.
        """
        ...

    def on_run_finished(
        self,
        answer: str,
        tool_calls_made: List[str],
        iterations: int,
        tokens_used: int,
        stop_reason: str,
    ) -> None:
        """Called when agent completes processing.

        Args:
            answer: The final answer text.
            tool_calls_made: List of tool names that were called.
            iterations: Total number of iterations used.
            tokens_used: Total tokens consumed.
            stop_reason: Why execution stopped ("answer_ready", "max_iterations").
        """
        ...

    def on_run_error(self, error: str) -> None:
        """Called when an error occurs during execution.

        Args:
            error: Error message describing what went wrong.
        """
        ...

    def on_plan_created(self, plan: Any) -> None:
        """Called when the orchestrator creates its execution plan.

        Args:
            plan: The Plan object with tasks list.
        """
        ...

    def on_plan_updated(self, plan: Any) -> None:
        """Called when a plan task status changes (e.g., marked complete).

        Args:
            plan: The updated Plan object.
        """
        ...


class NoOpChatCallback:
    """Default no-operation callback for chat agents.

    Used as the default chat_callback when no streaming is needed.
    All methods are no-ops that do nothing.
    """

    def on_run_started(self, session_id: str, message_id: str) -> None:
        """No-op implementation."""
        pass

    def on_iteration_start(self, iteration: int) -> None:
        """No-op implementation."""
        pass

    def on_iteration_end(self, iteration: int, tokens_used: int) -> None:
        """No-op implementation."""
        pass

    def on_tool_call_start(
        self,
        tool_call_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        iteration: int,
    ) -> None:
        """No-op implementation."""
        pass

    def on_tool_call_result(
        self,
        tool_call_id: str,
        tool_name: str,
        result: Any,
        success: bool,
        duration_ms: int,
    ) -> None:
        """No-op implementation."""
        pass

    def on_run_finished(
        self,
        answer: str,
        tool_calls_made: List[str],
        iterations: int,
        tokens_used: int,
        stop_reason: str,
    ) -> None:
        """No-op implementation."""
        pass

    def on_run_error(self, error: str) -> None:
        """No-op implementation."""
        pass

    def on_plan_created(self, plan: Any) -> None:
        """No-op implementation."""
        pass

    def on_plan_updated(self, plan: Any) -> None:
        """No-op implementation."""
        pass
