"""Agent portfolio controllers — clarification and portfolio building."""

import asyncio
from typing import Any, Dict, List

from prophitai_api.agents import (
    PortfolioBuilderAgent,
    generate_clarifying_questions,
    compose_enriched_brief,
    ClarifyAnswer,
)
from prophitai_api.services.sessions.agent_session import (
    execution_manager,
    run_agent_background,
)
from prophitai_api.services.sessions.chat_session import WebSocketChatCallback
from prophitai_api.utils.decorators import handle_controller_errors


@handle_controller_errors
async def clarify_preferences_controller(user_preferences: str) -> Dict[str, Any]:
    """Generate clarifying questions for a portfolio request.

    Analyzes the user's query and returns context-aware questions
    about missing investment dimensions (risk, horizon, capital, etc.).

    Args:
        user_preferences: The raw user query.

    Returns:
        Dict with questions, detected_preferences, and original_query.
    """
    result = await asyncio.to_thread(
        generate_clarifying_questions, user_preferences
    )
    return {
        "questions": result.questions,
        "detected_preferences": result.detected_preferences,
        "original_query": user_preferences,
    }


@handle_controller_errors
async def build_portfolio_controller(
    user_preferences: str,
    answers: List[ClarifyAnswer],
    background_tasks: Any,
) -> Dict[str, Any]:
    """Build a portfolio from the original query and clarification answers.

    Composes an enriched investment brief from the user's answers,
    then starts the PortfolioBuilder agent in the background.

    Args:
        user_preferences: Original user query.
        answers: Answered clarifying questions.
        background_tasks: FastAPI BackgroundTasks for async execution.

    Returns:
        Dict with execution_id and message.
    """
    enriched_brief = compose_enriched_brief(user_preferences, answers)

    execution_state = execution_manager.create_execution()
    execution_id = execution_state.execution_id
    loop = asyncio.get_running_loop()

    chat_callback = WebSocketChatCallback(execution_id, loop)
    agent = PortfolioBuilderAgent(
        user_preferences=enriched_brief,
        chat_callback=chat_callback,
        session_id=execution_id,
    )

    background_tasks.add_task(run_agent_background, agent, execution_id)

    return {
        "execution_id": execution_id,
        "message": "Portfolio build started",
    }
