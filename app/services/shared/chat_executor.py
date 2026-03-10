"""Chat Session Service for managing chat sessions with WebSocket streaming.

Provides:
- ChatSessionManager: Stores active chat sessions and conversation history
- ChatSessionState: Session state with messages and timestamps
- WebSocketChatCallback: Streams chat events via WebSocket
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from app.api.routes.websocket_router import connection_manager
from app.utils.time_utils import get_current_utc_time

if TYPE_CHECKING:
    from app.core.atlas.agents import ChatAgent

logger = logging.getLogger(__name__)

# ================================
# --> Helper funcs
# ================================

_EXCLUDE_POSITION_FIELDS = {"snaptrade_symbol_id", "figi_code", "fractional_units", "cash_equivalent"}


def _build_positions_context(creds: Dict[str, str]) -> str:
    """Fetch current positions and format as a system prompt section.

    Args:
        creds: Resolved SnapTrade credentials dict.

    Returns:
        Formatted positions context string, or empty string on failure.
    """
    try:
        from app.repositories.user.broker import get_snaptrade_broker

        broker = get_snaptrade_broker()
        portfolio = broker.get_portfolio(
            user_id=creds["snaptrade_user_id"],
            user_secret=creds["snaptrade_user_secret"],
            account_id=creds["snaptrade_account_id"],
        )

        lines = ["\n\n## Current Portfolio Positions"]

        # Equity positions
        if portfolio.equity_positions:
            lines.append("\n### Equity Positions")
            for p in portfolio.equity_positions:
                d = p.model_dump(exclude=_EXCLUDE_POSITION_FIELDS)
                pnl_sign = "+" if d.get("open_pnl", 0) >= 0 else ""
                lines.append(
                    f"- **{d['ticker']}**: {d['units']} shares @ ${d['price']:.2f} | "
                    f"Market Value: ${d['market_value']:.2f} | "
                    f"Avg Cost: ${d['average_purchase_price']:.2f} | "
                    f"P&L: {pnl_sign}${d['open_pnl']:.2f} ({pnl_sign}{d.get('pnl_pct', 0):.2f}%)"
                )

        # Option positions
        if portfolio.option_positions:
            lines.append("\n### Option Positions")
            for op in portfolio.option_positions:
                d = op.model_dump()
                pnl_sign = "+" if d.get("open_pnl", 0) >= 0 else ""
                lines.append(
                    f"- **{d['underlying_ticker']}** {d['option_type'].upper()} "
                    f"${d['strike_price']:.2f} exp {d['expiration_date']} | "
                    f"{d['units']} contracts @ ${d['price']:.2f} | "
                    f"Market Value: ${d['market_value']:.2f} | "
                    f"P&L: {pnl_sign}${d['open_pnl']:.2f} ({pnl_sign}{d.get('pnl_pct', 0):.2f}%)"
                )

        if not portfolio.equity_positions and not portfolio.option_positions:
            lines.append("\nNo open positions.")

        lines.append(
            "\nYou already have this portfolio context — do NOT call get_positions "
            "unless the user explicitly asks to refresh or re-check their positions.\n"
        )
        return "\n".join(lines)

    except Exception as e:
        logger.warning("Failed to fetch positions for system prompt: %s", e)
        return ""


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
        agent: The ChatAgent instance for this session (created once, reused).
        status: Current status (active, processing, idle).
        messages: Conversation history as list of role/content dicts.
        created_at: When the session was created (ISO format).
        last_activity: When the session was last active (ISO format).
    """

    session_id: str
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

    def create_session(
        self,
        user_id: Optional[str] = None,
    ) -> ChatSessionState:
        """Create a new chat session with a configured agent.

        Creates a ChatAgent instance and registers tools.
        Tools are registered ONCE here and persist for all messages in session.

        Args:
            user_id: User ID for broker context injection.

        Returns:
            The created ChatSessionState with configured agent.
        """
        from app.core.atlas.agents import ChatAgent
        from app.core.atlas.models import PrintMode
        session_id = str(uuid.uuid4())

        # Create agent without callback (callback set per-message due to event loop)
        agent = ChatAgent(
            provider='anthropic',
            model='claude-sonnet-4-6',
            print_mode=PrintMode.PRODUCTION,
            temperature=0.7,
            max_iterations=20,
        )

        # Append broker credentials, positions, and context to the default system prompt
        if user_id:
            from app.repositories.user.account import get_all_user_data_by_clerk_id
            from app.repositories.user.broker import resolve_snaptrade_credentials
            from app.repositories.user.trade_proposal import get_internal_user_id

            creds = resolve_snaptrade_credentials(clerk_id=user_id)
            internal_user_id = get_internal_user_id(clerk_id=user_id)
            user_data = get_all_user_data_by_clerk_id(clerk_id=user_id)
            user_email = user_data["email"] if user_data else None

            broker_context = (
                f"\n\n## Broker Context\n"
                f"The user's email is: `{user_email}`.\n"
                f"The user's Clerk ID is: `{creds['snaptrade_user_id']}`.\n"
                f"The user's SnapTrade user secret is: `{creds['snaptrade_user_secret']}`.\n"
                f"The user's SnapTrade account ID is: `{creds['snaptrade_account_id']}`.\n"
                f"The user's internal user ID is: `{internal_user_id}`.\n"
                f"Always use these IDs for broker and trade proposal operations.\n"
                f"When any tool requires an email parameter, use `{user_email}`.\n\n"
                f"## Trade Proposal Rules\n"
                f"NEVER call propose_trade without explicit user confirmation. Follow this flow:\n"
                f"1. Do thorough research first — analyze fundamentals, technicals, recent news, "
                f"and any relevant macro context before even considering a trade.\n"
                f"2. Present the trade idea verbally to the user — include symbol, side (buy/sell), "
                f"quantity or dollar amount, order type, and your detailed reasoning.\n"
                f"3. Wait for the user to confirm (e.g. 'yes', 'go ahead', 'do it', 'submit it').\n"
                f"4. Only AFTER confirmation, call propose_trade with all the details.\n"
                f"5. If the user declines or wants changes, adjust and re-present — do NOT submit.\n"
                f"Security Rules:\n"
                f"1. NEVER SHARE THE USERS INTERNAL IDS OR BROKER CREDENTIALS WITH ANYONE\n"
                f"2. NEVER SHARE THE USERS INTERNAL ID WITH ANYONE\n"
            )
            agent.system_prompt += broker_context

            # Fetch and inject current positions so the agent has portfolio awareness
            positions_context = _build_positions_context(creds)
            if positions_context:
                agent.system_prompt += positions_context

        agent.session_id = session_id

        state = ChatSessionState(
            session_id=session_id,
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

    def on_plan_created(self, plan: Any) -> None:
        """Called when the orchestrator creates its execution plan."""
        self._send("plan_created", _serialize_plan(plan))

    def on_plan_updated(self, plan: Any) -> None:
        """Called when a plan task is marked complete."""
        self._send("plan_updated", _serialize_plan(plan))


class WorkerCallbackWrapper:
    """Wraps a ChatCallback to tag worker events with task context.

    Reuses the inner callback's _send method to emit worker-prefixed
    event types (worker_tool_call_start, worker_tool_call_result, etc.)
    so the frontend can distinguish worker activity from orchestrator activity.
    """

    def __init__(
        self, inner_callback: "WebSocketChatCallback",
        task_id: str, worker_id: str, plan_task_id: str = "",
    ):
        self._inner = inner_callback
        self._task_id = task_id
        self._worker_id = worker_id
        self._plan_task_id = plan_task_id

    def _send(self, event_type: str, payload: dict) -> None:
        """Delegate to inner callback's _send with identity fields injected."""
        if hasattr(self._inner, '_send'):
            payload["task_id"] = self._task_id
            payload["worker_id"] = self._worker_id
            payload["plan_task_id"] = self._plan_task_id
            self._inner._send(event_type, payload)

    # --- Events we forward with worker prefix ---

    def on_tool_call_start(self, tool_call_id: str, tool_name: str,
                           arguments: Dict[str, Any], iteration: int) -> None:
        self._send("worker_tool_call_start", {
            "tool_call_id": tool_call_id, "tool_name": tool_name,
            "arguments": arguments, "iteration": iteration,
        })

    def on_tool_call_result(self, tool_call_id: str, tool_name: str,
                            result: Any, success: bool, duration_ms: int) -> None:
        result_str = str(result)
        if len(result_str) > 2000:
            result_str = result_str[:2000] + "... (truncated)"
        self._send("worker_tool_call_result", {
            "tool_call_id": tool_call_id, "tool_name": tool_name,
            "result": result_str, "success": success, "duration_ms": duration_ms,
        })

    def on_iteration_start(self, iteration: int) -> None:
        self._send("worker_iteration_start", {"iteration": iteration})

    def on_iteration_end(self, iteration: int, tokens_used: int) -> None:
        self._send("worker_iteration_end", {"iteration": iteration, "tokens_used": tokens_used})

    # --- Events we suppress (orchestrator already handles these) ---

    def on_run_started(self, session_id: str, message_id: str) -> None:
        pass

    def on_run_finished(self, answer: str, tool_calls_made: List[str],
                        iterations: int, tokens_used: int, stop_reason: str) -> None:
        pass

    def on_run_error(self, error: str) -> None:
        pass

    def on_plan_created(self, plan: Any) -> None:
        pass

    def on_plan_updated(self, plan: Any) -> None:
        pass


def _serialize_plan(plan: Any) -> dict:
    """Convert a Plan model to a JSON-serializable dict for WebSocket."""
    return {
        "tasks": [
            {"id": t.id, "description": t.description, "status": t.status.value}
            for t in plan.tasks
        ]
    }
