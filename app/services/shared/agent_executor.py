"""Agent Execution Service for managing agent runs with WebSocket streaming.

Provides:
- AgentExecutionManager: Stores active/completed executions
- WebSocketCallback: Streams task state updates to frontend
- run_agent_background: Runs agent in background asyncio task
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, TYPE_CHECKING, Union

from app.api.routes.websocket_router import connection_manager
from app.core.atlas.models import Plan, TaskStatus
from app.utils.time_utils import get_current_utc_time

if TYPE_CHECKING:
    from app.core.atlas.agents import DeepAgent as BaseAgent
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
        plan: The agent's execution plan (once created).
        result: The final result (once complete).
        error: Error message (if status is error).
        iterations: Number of iterations used.
        tokens: Total tokens consumed.
        created_at: When the execution started.
    """

    execution_id: str
    status: ExecutionStatus = ExecutionStatus.RUNNING
    plan: Optional[Plan] = None
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
        plan: Optional[Plan] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        iterations: Optional[int] = None,
        tokens: Optional[int] = None,
    ) -> Optional[ExecutionState]:
        """Update an execution's state.

        Args:
            execution_id: The execution to update.
            status: New status.
            plan: The execution plan.
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
        if plan is not None:
            state.plan = plan
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


class WebSocketCallback:
    """StateCallback implementation that streams updates via WebSocket.

    Sends task state changes to the frontend through the connection manager.
    """

    def __init__(self, execution_id: str, loop: asyncio.AbstractEventLoop):
        """Initialize with the execution ID and event loop to stream to.

        Args:
            execution_id: The execution ID for WebSocket routing.
            loop: The main event loop (FastAPI's loop) where WebSocket connections exist.
        """
        self.execution_id = execution_id
        self._loop = loop

    def _send_async(self, message_type: str, payload: dict) -> None:
        """Send a message via the connection manager.

        Uses run_coroutine_threadsafe to schedule on the main event loop,
        since this may be called from a thread pool executor.
        """
        async def _send():
            await connection_manager.send_message(self.execution_id, message_type, payload)

        try:
            # Schedule the coroutine on the main event loop (thread-safe)
            future = asyncio.run_coroutine_threadsafe(_send(), self._loop)
            # Wait for it to complete with a timeout
            future.result(timeout=5.0)
        except Exception:
            # Silently ignore send failures (connection may be closed)
            pass

    def _close_connection(self) -> None:
        """Gracefully close the WebSocket connection after completion."""
        async def _close():
            websocket = connection_manager.active_connections.get(self.execution_id)
            if websocket:
                try:
                    await websocket.close(code=1000, reason="Agent completed")
                except Exception:
                    pass
                connection_manager.disconnect(self.execution_id)

        try:
            future = asyncio.run_coroutine_threadsafe(_close(), self._loop)
            future.result(timeout=5.0)
        except Exception:
            pass

    def on_plan_created(self, plan: Plan) -> None:
        """Called when the agent creates its execution plan.

        Args:
            plan: The structured plan with tasks and subtasks.
        """
        # Update execution manager with plan
        execution_manager.update_execution(self.execution_id, plan=plan)

        # Serialize plan for WebSocket
        payload = {
            "tasks": [
                {
                    "id": task.id,
                    "description": task.description,
                    "status": task.status.value,
                    "subtasks": [
                        {
                            "id": st.id,
                            "description": st.description,
                            "status": st.status.value,
                        }
                        for st in task.subtasks
                    ],
                }
                for task in plan.tasks
            ]
        }
        self._send_async("plan_created", payload)

    def on_task_update(
        self,
        task_id: str,
        subtask_id: Optional[str],
        status: TaskStatus,
    ) -> None:
        """Called when a task or subtask status changes.

        Args:
            task_id: The main task identifier.
            subtask_id: The subtask identifier if applicable, or None.
            status: The new status.
        """
        payload = {
            "task_id": task_id,
            "subtask_id": subtask_id,
            "status": status.value,
        }
        self._send_async("task_update", payload)

    def on_agent_finished(
        self,
        execution_id: str,
        result: Optional[Dict[str, Any]] = None,
        iterations: int = 0,
        tokens: int = 0,
    ) -> None:
        """Called when the agent completes execution.

        Sends the final result to the frontend via WebSocket so
        it can be displayed immediately without polling.

        Args:
            execution_id: The unique identifier for this execution.
            result: The final portfolio result data.
            iterations: Number of iterations used.
            tokens: Total tokens consumed.
        """
        payload = {
            "execution_id": execution_id,
            "result": result,
            "iterations": iterations,
            "tokens": tokens,
        }
        self._send_async("complete", payload)

        # Gracefully close the WebSocket after sending complete
        self._close_connection()


async def run_agent_background(
    agent: "Union[BaseAgent, AgentBase]",
    execution_id: str,
) -> None:
    """Run an agent in the background with WebSocket streaming.

    Executes the agent in a thread pool to avoid blocking.
    Handles both old-style agents (DeepAgent, returns dict) and
    new-style agents (AgentBase/OrchestratorAgent, returns AgentResponse).

    Args:
        agent: The agent instance to run.
        execution_id: The execution ID for state management.
    """
    from app.core.atlas.models import AgentResponse

    try:
        loop = asyncio.get_running_loop()

        # Detect agent architecture by base class
        from app.core.atlas.agents.base import AgentBase
        is_new_architecture = isinstance(agent, AgentBase)

        if is_new_architecture:
            raw_result = await loop.run_in_executor(None, agent.run)
        else:
            response_format = getattr(agent, 'response_model', None)
            raw_result = await loop.run_in_executor(
                None,
                lambda: agent.run(response_format=response_format)
            )

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
            # Old-style dict result
            result = raw_result
            iterations = result.get("iterations", 0) if isinstance(result, dict) else 0
            tokens = result.get("total_tokens", 0) if isinstance(result, dict) else 0

            if "parsed_output" in result and result["parsed_output"] is not None:
                parsed = result["parsed_output"]
                if hasattr(parsed, "model_dump"):
                    result["final_answer"] = parsed.model_dump()
                else:
                    result["final_answer"] = parsed
                del result["parsed_output"]

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
