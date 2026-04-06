"""Agent execution controllers — start agents and retrieve results."""

import asyncio
from typing import Any, Dict

from prophitai_api.agents import WatchlistAgent, PortfolioBuilderAgent
from prophitai_api.schemas.agent import AgentType
from prophitai_api.agents.sessions import (
    execution_manager,
    run_agent_background,
    WebSocketChatCallback,
)
from prophitai_api.utils.decorators import handle_controller_errors


# ================================
# --> Helper funcs
# ================================


def _create_agent(
    agent_type: AgentType,
    parameters: Dict[str, Any],
    execution_id: str,
    loop: asyncio.AbstractEventLoop,
):
    """Factory function to create agent instances based on type.

    Args:
        agent_type: The type of agent to create.
        parameters: Agent-specific parameters.
        execution_id: Unique execution ID (used for WebSocket routing).
        loop: The main event loop for thread-safe WebSocket communication.

    Returns:
        An agent instance ready to run.

    Raises:
        ValueError: If agent_type is not supported or required parameters are missing.
    """
    if agent_type == AgentType.WATCHLIST:
        user_preferences = parameters.get("user_preferences")
        if not user_preferences:
            raise ValueError("user_preferences is required for watchlist agent")

        chat_callback = WebSocketChatCallback(execution_id, loop)
        return WatchlistAgent(
            user_preferences=user_preferences,
            chat_callback=chat_callback,
            session_id=execution_id,
        )

    elif agent_type == AgentType.PORTFOLIO_BUILDER:
        user_preferences = parameters.get("user_preferences")
        if not user_preferences:
            raise ValueError("user_preferences is required for portfolio_builder agent")

        chat_callback = WebSocketChatCallback(execution_id, loop)
        return PortfolioBuilderAgent(
            user_preferences=user_preferences,
            chat_callback=chat_callback,
            session_id=execution_id,
        )

    else:
        raise ValueError(f"Unsupported agent type: {agent_type}")


# ================================
# --> Controllers
# ================================


@handle_controller_errors
async def execute_agent_controller(
    agent_type: AgentType,
    parameters: Dict[str, Any],
    background_tasks: Any,
) -> Dict[str, Any]:
    """Start an agent execution.

    Creates a new execution, starts the agent in the background,
    and returns the execution_id for tracking.

    Args:
        agent_type: The type of agent to execute.
        parameters: Agent-specific parameters.
        background_tasks: FastAPI BackgroundTasks for async execution.

    Returns:
        Dict with execution_id and message.
    """
    execution_state = execution_manager.create_execution()
    execution_id = execution_state.execution_id

    # Reason: agent runs in thread pool, but WebSocket is async on the main loop.
    loop = asyncio.get_running_loop()

    try:
        agent = _create_agent(agent_type, parameters, execution_id, loop)
    except (ValueError, Exception) as e:
        execution_manager.remove_execution(execution_id)
        raise

    background_tasks.add_task(run_agent_background, agent, execution_id)

    return {
        "execution_id": execution_id,
        "message": f"Agent execution started for {agent_type.value}",
    }


@handle_controller_errors
async def get_execution_result_controller(execution_id: str) -> Dict[str, Any]:
    """Poll for execution result.

    Args:
        execution_id: The execution ID from the execute endpoint.

    Returns:
        Dict with status, result, error, iterations, and tokens.

    Raises:
        ValueError: If execution_id not found.
    """
    state = execution_manager.get_execution(execution_id)
    if state is None:
        raise ValueError(f"Execution {execution_id} not found")

    return {
        "status": state.status,
        "result": state.result,
        "error": state.error,
        "iterations": state.iterations,
        "tokens": state.tokens,
    }
