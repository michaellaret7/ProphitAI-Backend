"""Chat session controllers — create, send messages, retrieve history."""

import asyncio
from typing import Any, Dict

from prophitai_api.agents.sessions import (
    WebSocketChatCallback,
    chat_session_manager,
    run_chat_agent_background,
)
from prophitai_api.utils.decorators import handle_controller_errors
from prophitai_shared.time_utils import get_current_utc_time


@handle_controller_errors
async def create_session_controller(user_id: str) -> Dict[str, Any]:
    """Create a new chat session with a configured agent.

    Args:
        user_id: Clerk user ID for broker context injection.

    Returns:
        Dict with session_id and created_at.
    """
    session = chat_session_manager.create_session(user_id=user_id)
    return {
        "session_id": session.session_id,
        "created_at": session.created_at,
    }


@handle_controller_errors
async def send_message_controller(
    session_id: str,
    message: str,
    background_tasks: Any,
) -> Dict[str, Any]:
    """Send a message and start agent processing in the background.

    Args:
        session_id: The session to send the message to.
        message: The message content.
        background_tasks: FastAPI BackgroundTasks for async execution.

    Returns:
        Dict with message_id and status.

    Raises:
        ValueError: If session not found or agent not initialized.
    """
    session = chat_session_manager.get_session(session_id)
    if session is None:
        raise ValueError(f"Session {session_id} not found")

    if session.agent is None:
        raise ValueError(f"Session {session_id} agent not initialized")

    # Store user message in session history
    chat_session_manager.add_message(session_id, "user", message)

    # Set callback on the session's agent (needs current event loop)
    loop = asyncio.get_running_loop()
    session.agent.chat_callback = WebSocketChatCallback(session_id, loop)

    # Generate message ID
    message_id = f"msg_{int(get_current_utc_time().timestamp() * 1000)}"

    # Run agent in background (reusing session's agent with pre-registered tools)
    background_tasks.add_task(
        run_chat_agent_background,
        session.agent,
        session_id,
        message,
        chat_session_manager.get_history(session_id),
        message_id,
    )

    return {"message_id": message_id, "status": "processing"}


@handle_controller_errors
async def get_history_controller(session_id: str) -> Dict[str, Any]:
    """Get conversation history for a session.

    Args:
        session_id: The session to get history for.

    Returns:
        Dict with session_id and messages list.

    Raises:
        ValueError: If session not found.
    """
    session = chat_session_manager.get_session(session_id)
    if session is None:
        raise ValueError(f"Session {session_id} not found")

    return {
        "session_id": session_id,
        "messages": chat_session_manager.get_history(session_id),
    }
