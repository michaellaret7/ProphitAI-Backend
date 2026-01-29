"""Agent execution router for starting agents and retrieving results.

Provides REST endpoints for:
- Starting agent execution (returns execution_id)
- Polling for execution results
"""

import asyncio
from enum import Enum
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app.services.shared.agent_executor import (
    ExecutionStatus,
    WebSocketCallback,
    execution_manager,
    run_agent_background,
)

from app.core.atlas.models import PrintMode

router = APIRouter(prefix="/agents", tags=["Agent Execution"])

class AgentType(str, Enum):
    """Available agent types for execution.

    Only main agents (inheriting from BaseAgent) that support
    state_callback streaming are available here.
    """

    OPTIMIZER = "optimizer"
    WATCHLIST = "watchlist"
    # Add more BaseAgent-based agents as needed


class ExecuteAgentRequest(BaseModel):
    """Request body for starting agent execution."""

    agent_type: AgentType = Field(..., description="The type of agent to execute")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Agent-specific parameters (varies by agent type)",
    )


class ExecuteAgentResponse(BaseModel):
    """Response from starting agent execution."""

    execution_id: str = Field(..., description="Unique identifier for this execution")
    message: str = Field(default="Agent execution started")


class ExecutionResultResponse(BaseModel):
    """Response from polling execution result."""

    status: ExecutionStatus = Field(..., description="Current execution status")
    plan: Optional[Dict[str, Any]] = Field(None, description="The agent's execution plan")
    result: Optional[Dict[str, Any]] = Field(None, description="Final result (when complete)")
    error: Optional[str] = Field(None, description="Error message (when status is error)")
    iterations: int = Field(0, description="Number of iterations used")
    tokens: int = Field(0, description="Total tokens consumed")


def _create_agent(agent_type: AgentType, parameters: Dict[str, Any], state_callback: WebSocketCallback):
    """Factory function to create agent instances based on type.

    Args:
        agent_type: The type of agent to create.
        parameters: Agent-specific parameters.
        state_callback: The callback for streaming state updates.

    Returns:
        An agent instance ready to run.

    Raises:
        ValueError: If agent_type is not supported or required parameters are missing.
    """
    if agent_type == AgentType.OPTIMIZER:
        from app.domain.portfolio_operations.optimizer.agent import OptimizerAgent

        portfolio_id = parameters.get("portfolio_id")
        if not portfolio_id:
            raise ValueError("portfolio_id is required for optimizer agent")

        return OptimizerAgent(
            portfolio_id=portfolio_id,
            risk_tolerance=parameters.get("risk_tolerance"),
            time_horizon=parameters.get("time_horizon"),
            investment_goals=parameters.get("investment_goals"),
            sectors_to_exclude=parameters.get("sectors_to_exclude"),
            sectors_to_include=parameters.get("sectors_to_include"),
            tickers_to_keep=parameters.get("tickers_to_keep"),
            tickers_to_exclude=parameters.get("tickers_to_exclude"),
            state_callback=state_callback,
            print_mode=PrintMode.PRODUCTION,
        )

    elif agent_type == AgentType.WATCHLIST:
        from app.domain.ai_watchlist.agent import AiWatchlistAgent

        user_preferences = parameters.get("user_preferences")
        if not user_preferences:
            raise ValueError("user_preferences is required for watchlist agent")

        return AiWatchlistAgent(
            user_preferences=user_preferences,
            state_callback=state_callback,
            print_mode=PrintMode.PRODUCTION,
        )

    else:
        raise ValueError(f"Unsupported agent type: {agent_type}")


@router.post("/execute", response_model=ExecuteAgentResponse)
async def execute_agent(
    request: ExecuteAgentRequest,
    background_tasks: BackgroundTasks,
) -> ExecuteAgentResponse:
    """Start an agent execution.

    Creates a new execution, starts the agent in the background,
    and returns the execution_id for tracking.

    Connect to WebSocket /ws/agent/{execution_id} for real-time task updates.
    Poll GET /api/agents/{execution_id}/result for the final result.

    Args:
        request: The agent type and parameters.
        background_tasks: FastAPI background tasks for async execution.

    Returns:
        The execution_id for tracking this agent run.
    """
    # Create execution entry
    execution_state = execution_manager.create_execution()
    execution_id = execution_state.execution_id

    # Create WebSocket callback with the current event loop
    # This loop is needed for thread-safe WebSocket communication
    loop = asyncio.get_running_loop()
    callback = WebSocketCallback(execution_id, loop)

    try:
        # Create the agent with the callback
        agent = _create_agent(request.agent_type, request.parameters, callback)
    except ValueError as e:
        execution_manager.remove_execution(execution_id)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        execution_manager.remove_execution(execution_id)
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {str(e)}")

    # Start agent execution in background
    background_tasks.add_task(run_agent_background, agent, execution_id)

    return ExecuteAgentResponse(
        execution_id=execution_id,
        message=f"Agent execution started for {request.agent_type.value}",
    )


@router.get("/{execution_id}/result", response_model=ExecutionResultResponse)
async def get_execution_result(execution_id: str) -> ExecutionResultResponse:
    """Poll for execution result.

    Returns the current state of an agent execution.
    Poll this endpoint to check if the agent has completed.

    Args:
        execution_id: The execution ID from the execute endpoint.

    Returns:
        The current execution state including status, plan, and result.

    Raises:
        HTTPException: 404 if execution_id not found.
    """
    state = execution_manager.get_execution(execution_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")

    # Serialize plan if present
    plan_dict = None
    if state.plan is not None:
        plan_dict = {
            "tasks": [
                {
                    "id": task.id,
                    "description": task.description,
                    "status": task.status.value,
                    "work_summary": task.work_summary,
                    "subtasks": [
                        {
                            "id": st.id,
                            "description": st.description,
                            "status": st.status.value,
                            "work_summary": st.work_summary,
                        }
                        for st in task.subtasks
                    ],
                }
                for task in state.plan.tasks
            ]
        }

    return ExecutionResultResponse(
        status=state.status,
        plan=plan_dict,
        result=state.result,
        error=state.error,
        iterations=state.iterations,
        tokens=state.tokens,
    )
