"""Agent Execution Service for managing agent runs with WebSocket streaming.

Provides:
- AgentExecutionManager: Stores active/completed executions
- run_agent_background: Runs agent in background asyncio task
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, TYPE_CHECKING

from app.api.routes.websocket_router import connection_manager
from app.utils.time_utils import get_current_utc_time

if TYPE_CHECKING:
    from app.core.atlas.agents.base import AgentBase


class ExecutionStatus(str, Enum):
    """Status of an agent execution."""

    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class ExecutionState:
    """State of a single agent execution.

    Attributes:
        execution_id: Unique identifier for this execution.
        status: Current status (running, complete, error).
        result: The final result (once complete).
        error: Error message (if status is error).
        iterations: Number of iterations used.
        tokens: Total tokens consumed.
        created_at: When the execution started.
    """

    execution_id: str
    status: ExecutionStatus = ExecutionStatus.RUNNING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    iterations: int = 0
    tokens: int = 0
    created_at: str = field(default_factory=lambda: get_current_utc_time().isoformat())


class AgentExecutionManager:
    """Manages agent execution states.

    Stores active and recently completed executions in memory.
    """

    def __init__(self):
        self._executions: Dict[str, ExecutionState] = {}

    def create_execution(self) -> ExecutionState:
        """Create a new execution entry.

        Returns:
            The created ExecutionState with a new execution_id.
        """
        execution_id = str(uuid.uuid4())
        state = ExecutionState(execution_id=execution_id)
        self._executions[execution_id] = state
        return state

    def get_execution(self, execution_id: str) -> Optional[ExecutionState]:
        """Get an execution by ID.

        Args:
            execution_id: The execution to retrieve.

        Returns:
            The ExecutionState or None if not found.
        """
        return self._executions.get(execution_id)

    def update_execution(
        self,
        execution_id: str,
        *,
        status: Optional[ExecutionStatus] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        iterations: Optional[int] = None,
        tokens: Optional[int] = None,
    ) -> Optional[ExecutionState]:
        """Update an execution's state.

        Args:
            execution_id: The execution to update.
            status: New status.
            result: Final result.
            error: Error message.
            iterations: Iterations used.
            tokens: Tokens consumed.

        Returns:
            The updated ExecutionState or None if not found.
        """
        state = self._executions.get(execution_id)
        if state is None:
            return None

        if status is not None:
            state.status = status
        if result is not None:
            state.result = result
        if error is not None:
            state.error = error
        if iterations is not None:
            state.iterations = iterations
        if tokens is not None:
            state.tokens = tokens

        return state

    def remove_execution(self, execution_id: str) -> bool:
        """Remove an execution from the manager.

        Args:
            execution_id: The execution to remove.

        Returns:
            True if removed, False if not found.
        """
        if execution_id in self._executions:
            del self._executions[execution_id]
            return True
        return False


# Global execution manager instance
execution_manager = AgentExecutionManager()


async def run_agent_background(
    agent: "AgentBase",
    execution_id: str,
) -> None:
    """Run an agent in the background with WebSocket streaming.

    Executes the agent in a thread pool to avoid blocking.

    Args:
        agent: The agent instance to run (must be AgentBase subclass).
        execution_id: The execution ID for state management.
    """
    from app.core.atlas.models import AgentResponse

    try:
        loop = asyncio.get_running_loop()
        raw_result = await loop.run_in_executor(None, agent.run)

        # Normalize to a JSON-serializable dict
        if isinstance(raw_result, AgentResponse):
            final_answer = None
            if raw_result.parsed_output is not None:
                po = raw_result.parsed_output
                final_answer = po.model_dump() if hasattr(po, "model_dump") else po

            result = {
                "answer": raw_result.answer,
                "final_answer": final_answer,
                "tool_calls": raw_result.tool_calls_made,
                "total_tokens": raw_result.tokens_used,
                "iterations": raw_result.iterations,
                "stop_reason": raw_result.stop_reason,
            }
            iterations = raw_result.iterations
            tokens = raw_result.tokens_used
        else:
            result = raw_result
            iterations = result.get("iterations", 0) if isinstance(result, dict) else 0
            tokens = result.get("total_tokens", 0) if isinstance(result, dict) else 0

        # Update execution state with result
        execution_manager.update_execution(
            execution_id,
            status=ExecutionStatus.COMPLETE,
            result=result,
            iterations=iterations,
            tokens=tokens,
        )

        # Notify via WebSocket that execution is complete (includes final result)
        websocket_payload = {
            "execution_id": execution_id,
            "answer": result.get("answer"),
            "final_answer": result.get("final_answer"),
            "iterations": iterations,
            "tokens": tokens,
            "stop_reason": result.get("stop_reason"),
        }
        await connection_manager.send_message(execution_id, "complete", websocket_payload)

        # Gracefully close WebSocket
        websocket = connection_manager.active_connections.get(execution_id)
        if websocket:
            try:
                await websocket.close(code=1000, reason="Agent completed")
            except Exception:
                pass
            connection_manager.disconnect(execution_id)

    except Exception as e:
        # Update execution state with error
        execution_manager.update_execution(
            execution_id,
            status=ExecutionStatus.ERROR,
            error=str(e),
        )

        # Still notify completion (with error status)
        await connection_manager.send_message(
            execution_id,
            "complete",
            {"execution_id": execution_id, "error": str(e)},
        )
