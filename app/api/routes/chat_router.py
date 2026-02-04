"""Chat router for interactive agent chat sessions.

Provides REST and WebSocket endpoints for:
- Creating chat sessions
- Sending messages (triggers agent execution)
- Retrieving conversation history
- Real-time streaming via WebSocket
"""

import asyncio
from typing import TYPE_CHECKING, Any, Dict, List

from fastapi import APIRouter, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.api.routes.websocket_router import connection_manager
from app.services.shared.chat_executor import (
    WebSocketChatCallback,
    chat_session_manager,
)
from app.utils.time_utils import get_current_utc_time

if TYPE_CHECKING:
    from app.core.atlas.agents import ChatAgent

router = APIRouter(prefix="/chat", tags=["Chat"])


# ---------------------------------------------------------------------
# Pydantic Request/Response Models
# ---------------------------------------------------------------------


class CreateSessionRequest(BaseModel):
    """Request body for creating a chat session."""

    agent_type: str = Field(
        default="general",
        description="Type of agent for this session: 'macro_research' (macro strategy with research + web search), 'equity_research' (equity analysis with fundamentals, earnings, news), or 'general' (default)",
    )


class CreateSessionResponse(BaseModel):
    """Response from creating a chat session."""

    session_id: str = Field(..., description="Unique identifier for the session")
    agent_type: str = Field(..., description="The agent type for this session")
    created_at: str = Field(..., description="ISO timestamp of session creation")


class SendMessageRequest(BaseModel):
    """Request body for sending a message."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The message to send to the agent",
    )


class SendMessageResponse(BaseModel):
    """Response from sending a message."""

    message_id: str = Field(..., description="Unique identifier for this message")
    status: str = Field(default="processing", description="Current processing status")


class MessageHistoryResponse(BaseModel):
    """Response containing conversation history."""

    session_id: str = Field(..., description="The session ID")
    messages: List[Dict[str, Any]] = Field(
        ..., description="List of messages with role and content"
    )


# ---------------------------------------------------------------------
# REST Endpoints
# ---------------------------------------------------------------------


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_chat_session(
    request: CreateSessionRequest = CreateSessionRequest(),
) -> CreateSessionResponse:
    """Create a new chat session with specified agent type.

    The agent_type determines which tools and prompts are configured:
    - macro_research: Macro strategy agent with research search + web search
    - equity_research: Equity analyst with fundamentals, earnings calls, news, estimates, ratings
    - general: Default general-purpose tools

    Returns a session_id that should be used for all subsequent
    requests and WebSocket connections.
    """
    session = chat_session_manager.create_session(agent_type=request.agent_type)
    return CreateSessionResponse(
        session_id=session.session_id,
        agent_type=session.agent_type,
        created_at=session.created_at,
    )


@router.post("/sessions/{session_id}/messages", response_model=SendMessageResponse)
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    background_tasks: BackgroundTasks,
) -> SendMessageResponse:
    """Send a message and start agent processing.

    Uses the session's pre-configured agent (tools registered at session creation).
    The agent runs in the background. Connect to WebSocket
    /api/chat/ws/{session_id} to receive real-time updates.

    Args:
        session_id: The session to send the message to.
        request: The message content.
        background_tasks: FastAPI background tasks for async execution.

    Returns:
        A message_id and processing status.

    Raises:
        HTTPException: 404 if session not found.
    """
    session = chat_session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.agent is None:
        raise HTTPException(status_code=500, detail="Session agent not initialized")

    # Store user message in session history
    chat_session_manager.add_message(session_id, "user", request.message)

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
        request.message,
        chat_session_manager.get_history(session_id),
        message_id,
    )

    return SendMessageResponse(message_id=message_id, status="processing")


@router.get("/sessions/{session_id}/history", response_model=MessageHistoryResponse)
async def get_chat_history(session_id: str) -> MessageHistoryResponse:
    """Get conversation history for a session.

    Args:
        session_id: The session to get history for.

    Returns:
        The conversation history.

    Raises:
        HTTPException: 404 if session not found.
    """
    session = chat_session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return MessageHistoryResponse(
        session_id=session_id,
        messages=chat_session_manager.get_history(session_id),
    )


# ---------------------------------------------------------------------
# WebSocket Endpoint
# ---------------------------------------------------------------------


@router.websocket("/ws/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str) -> None:
    """WebSocket for real-time chat updates.

    Connect to receive streaming events during agent execution:
    - run_started: Agent begins processing
    - iteration_start/end: ReAct iteration lifecycle
    - tool_call_start: Tool execution begins (name + args)
    - tool_call_result: Tool execution complete (result + timing)
    - run_finished: Final answer ready
    - run_error: Error occurred
    - heartbeat: Keep-alive (every 30s)

    Args:
        websocket: The WebSocket connection.
        session_id: The session to receive updates for.
    """
    await connection_manager.connect(session_id, websocket)

    async def send_heartbeat() -> None:
        """Send periodic heartbeat to keep connection alive."""
        while True:
            await asyncio.sleep(30)
            try:
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": get_current_utc_time().isoformat(),
                })
            except Exception:
                break

    heartbeat_task = asyncio.create_task(send_heartbeat())

    try:
        while True:
            # Keep connection open, receive any client messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        heartbeat_task.cancel()
        connection_manager.disconnect(session_id)


# ---------------------------------------------------------------------
# Background Task
# ---------------------------------------------------------------------


async def run_chat_agent_background(
    agent: "ChatAgent",
    session_id: str,
    user_message: str,
    conversation_history: List[Dict[str, Any]],
    message_id: str,
) -> None:
    """Run chat agent in thread pool with WebSocket streaming.

    Args:
        agent: The ChatAgent instance with callback configured.
        session_id: The session ID for storing the response.
        user_message: The user's message.
        conversation_history: Previous conversation for context.
        message_id: Unique ID for this message exchange.
    """
    loop = asyncio.get_running_loop()

    try:
        # Run synchronous agent in thread pool
        result = await loop.run_in_executor(
            None,
            lambda: agent.run(user_message, conversation_history),
        )

        # Store assistant response in session history
        chat_session_manager.add_message(session_id, "assistant", result.answer)

    except Exception as e:
        # Error already sent via callback's on_run_error
        # Log for debugging but don't re-raise (background task)
        print(f"Chat agent error for session {session_id}: {e}")
