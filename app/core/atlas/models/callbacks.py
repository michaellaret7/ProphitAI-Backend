"""State callback protocol for streaming agent task state updates.

Provides a protocol for receiving notifications when agent task state changes,
enabling real-time streaming to frontends via WebSocket or other mechanisms.
"""

from typing import Any, Dict, Optional, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.atlas.models.plan import Plan, TaskStatus


class StateCallback(Protocol):
    """Protocol for receiving agent state change notifications.

    Implementations can stream these events to frontends via WebSocket,
    log them, or perform other actions on state changes.
    """

    def on_plan_created(self, plan: "Plan") -> None:
        """Called when the agent creates its execution plan (after iteration 1).

        Args:
            plan: The structured plan with tasks and subtasks.
        """
        ...

    def on_task_update(
        self,
        task_id: str,
        subtask_id: Optional[str],
        status: "TaskStatus",
    ) -> None:
        """Called when a task or subtask status changes.

        Args:
            task_id: The main task identifier (e.g., "1").
            subtask_id: The subtask identifier if applicable (e.g., "1a"), or None for main task.
            status: The new status (not_started, in_progress, complete).
        """
        ...

    def on_agent_finished(
        self,
        execution_id: str,
        result: Optional[Dict[str, Any]] = None,
        iterations: int = 0,
        tokens: int = 0,
    ) -> None:
        """Called when the agent completes execution.

        Args:
            execution_id: The unique identifier for this execution.
            result: The final result data (e.g., optimized portfolio).
            iterations: Number of iterations used.
            tokens: Total tokens consumed.
        """
        ...


class NoOpCallback:
    """Default no-operation callback that does nothing.

    Used as the default state_callback when no streaming is needed.
    """

    def on_plan_created(self, plan: "Plan") -> None:
        """No-op implementation."""
        pass

    def on_task_update(
        self,
        task_id: str,
        subtask_id: Optional[str],
        status: "TaskStatus",
    ) -> None:
        """No-op implementation."""
        pass

    def on_agent_finished(
        self,
        execution_id: str,
        result: Optional[Dict[str, Any]] = None,
        iterations: int = 0,
        tokens: int = 0,
    ) -> None:
        """No-op implementation."""
        pass
