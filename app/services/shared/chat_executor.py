"""Chat Session Service for managing chat sessions with WebSocket streaming.

Provides:
- ChatSessionManager: Stores active chat sessions and conversation history
- ChatSessionState: Session state with messages and timestamps
- WebSocketChatCallback: Streams chat events via WebSocket
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from app.api.routes.websocket_router import connection_manager
from app.utils.time_utils import get_current_utc_time

if TYPE_CHECKING:
    from app.core.atlas.agents import ChatAgent


class ChatSessionStatus(str, Enum):
    """Status of a chat session."""

    ACTIVE = "active"
    PROCESSING = "processing"
    IDLE = "idle"


@dataclass
class ChatSessionState:
    """State of a single chat session.

    Attributes:
        session_id: Unique identifier for this session.
        agent_type: Type of agent determining which tools are registered.
        agent: The ChatAgent instance for this session (created once, reused).
        status: Current status (active, processing, idle).
        messages: Conversation history as list of role/content dicts.
        created_at: When the session was created (ISO format).
        last_activity: When the session was last active (ISO format).
    """

    session_id: str
    agent_type: str = "general"
    agent: Optional["ChatAgent"] = None
    status: ChatSessionStatus = ChatSessionStatus.IDLE
    messages: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: get_current_utc_time().isoformat())
    last_activity: str = field(default_factory=lambda: get_current_utc_time().isoformat())


class ChatSessionManager:
    """Manages chat session states.

    Stores active sessions in memory with their conversation history.
    Each session has a dedicated ChatAgent instance with tools registered
    once at session creation.
    """

    def __init__(self):
        self._sessions: Dict[str, ChatSessionState] = {}

    def create_session(self, agent_type: str = "general") -> ChatSessionState:
        """Create a new chat session with a configured agent.

        Creates a ChatAgent instance and registers tools based on agent_type.
        Tools are registered ONCE here and persist for all messages in session.

        Args:
            agent_type: Type of agent (e.g., "macro_research", "earnings_call").

        Returns:
            The created ChatSessionState with configured agent.
        """
        from app.core.atlas.agents import ChatAgent
        from app.core.atlas.models import PrintMode
        from app.core.atlas.tools.chat_registry import register_tools_for_agent_type

        session_id = str(uuid.uuid4())

        # Create agent without callback (callback set per-message due to event loop)
        agent = ChatAgent(
            provider='anthropic',
            model='claude-opus-4-5-20251101',
            # model='claude-haiku-4-5-20251001',
            print_mode=PrintMode.PRODUCTION,
            temperature=0.7,
            max_iterations=20,
        )

        agent.session_id = session_id

        # Register tools ONCE based on agent_type
        register_tools_for_agent_type(agent, agent_type)

        state = ChatSessionState(
            session_id=session_id,
            agent_type=agent_type,
            agent=agent,
        )
        self._sessions[session_id] = state
        return state

    def get_session(self, session_id: str) -> Optional[ChatSessionState]:
        """Get a session by ID.

        Args:
            session_id: The session to retrieve.

        Returns:
            The ChatSessionState or None if not found.
        """
        return self._sessions.get(session_id)

    def add_message(self, session_id: str, role: str, content: str) -> bool:
        """Add a message to a session's history.

        Args:
            session_id: The session to add the message to.
            role: The message role (user, assistant).
            content: The message content.

        Returns:
            True if added, False if session not found.
        """
        session = self._sessions.get(session_id)
        if session is None:
            return False

        session.messages.append({"role": role, "content": content})
        session.last_activity = get_current_utc_time().isoformat()
        return True

    def get_history(
        self, session_id: str, max_messages: int = 20
    ) -> List[Dict[str, Any]]:
        """Get conversation history for a session.

        Filters to only user/assistant messages for LLM context.

        Args:
            session_id: The session to get history for.
            max_messages: Maximum number of messages to return.

        Returns:
            List of message dicts, or empty list if session not found.
        """
        session = self._sessions.get(session_id)
        if session is None:
            return []

        # Filter to user/assistant messages only
        filtered = [
            msg for msg in session.messages if msg.get("role") in ("user", "assistant")
        ]
        return filtered[-max_messages:]

    def update_status(
        self, session_id: str, status: ChatSessionStatus
    ) -> Optional[ChatSessionState]:
        """Update a session's status.

        Args:
            session_id: The session to update.
            status: The new status.

        Returns:
            The updated ChatSessionState or None if not found.
        """
        session = self._sessions.get(session_id)
        if session is None:
            return None

        session.status = status
        session.last_activity = get_current_utc_time().isoformat()
        return session

    def remove_session(self, session_id: str) -> bool:
        """Remove a session from the manager.

        Args:
            session_id: The session to remove.

        Returns:
            True if removed, False if not found.
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False


# Global chat session manager instance
chat_session_manager = ChatSessionManager()


class WebSocketChatCallback:
    """ChatCallback implementation that streams events via WebSocket.

    Bridges synchronous agent execution with async WebSocket connections
    using asyncio.run_coroutine_threadsafe for thread-safe communication.
    """

    def __init__(self, session_id: str, loop: asyncio.AbstractEventLoop):
        """Initialize with session ID and event loop.

        Args:
            session_id: The session ID for WebSocket routing.
            loop: The main event loop where WebSocket connections exist.
        """
        self.session_id = session_id
        self._loop = loop

    def _send(self, event_type: str, payload: dict) -> None:
        """Send a message via the connection manager (thread-safe).

        Args:
            event_type: The type of event to send.
            payload: The event payload.
        """
        async def _send_async():
            await connection_manager.send_message(self.session_id, event_type, payload)

        try:
            future = asyncio.run_coroutine_threadsafe(_send_async(), self._loop)
            future.result(timeout=5.0)
        except Exception:
            pass  # Connection may be closed, fail silently

    def on_run_started(self, session_id: str, message_id: str) -> None:
        """Called when agent starts processing a message."""
        self._send("run_started", {
            "session_id": session_id,
            "message_id": message_id,
        })

    def on_iteration_start(self, iteration: int) -> None:
        """Called at the start of each ReAct iteration."""
        self._send("iteration_start", {"iteration": iteration})

    def on_iteration_end(self, iteration: int, tokens_used: int) -> None:
        """Called at the end of each ReAct iteration."""
        self._send("iteration_end", {
            "iteration": iteration,
            "tokens_used": tokens_used,
        })

    def on_tool_call_start(
        self,
        tool_call_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        iteration: int,
    ) -> None:
        """Called when a tool execution begins."""
        self._send("tool_call_start", {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "arguments": arguments,
            "iteration": iteration,
        })

    def on_tool_call_result(
        self,
        tool_call_id: str,
        tool_name: str,
        result: Any,
        success: bool,
        duration_ms: int,
    ) -> None:
        """Called when a tool execution completes."""
        # Truncate large results to prevent massive WebSocket payloads
        result_str = str(result)
        if len(result_str) > 2000:
            result_str = result_str[:2000] + "... (truncated)"

        self._send("tool_call_result", {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "result": result_str,
            "success": success,
            "duration_ms": duration_ms,
        })

    def on_run_finished(
        self,
        answer: str,
        tool_calls_made: List[str],
        iterations: int,
        tokens_used: int,
        stop_reason: str,
    ) -> None:
        """Called when agent completes processing."""
        self._send("run_finished", {
            "answer": answer,
            "tool_calls_made": tool_calls_made,
            "iterations": iterations,
            "tokens_used": tokens_used,
            "stop_reason": stop_reason,
        })

    def on_run_error(self, error: str) -> None:
        """Called when an error occurs."""
        self._send("run_error", {"error": error})
