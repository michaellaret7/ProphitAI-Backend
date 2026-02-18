"""
Shared services used across multiple domains.

Provides services for:
- Stock price data fetching
- Agent execution management with WebSocket streaming
- Chat session management with WebSocket streaming
"""

from app.services.shared.price import PriceService
from app.services.shared.agent_executor import (
    AgentExecutionManager,
    ExecutionState,
    ExecutionStatus,
    execution_manager,
    run_agent_background,
)
from app.services.shared.chat_executor import (
    ChatSessionManager,
    ChatSessionState,
    ChatSessionStatus,
    WebSocketChatCallback,
    chat_session_manager,
)

__all__ = [
    # Price service
    "PriceService",
    # Agent execution
    "AgentExecutionManager",
    "ExecutionState",
    "ExecutionStatus",
    "execution_manager",
    "run_agent_background",
    # Chat session
    "ChatSessionManager",
    "ChatSessionState",
    "ChatSessionStatus",
    "WebSocketChatCallback",
    "chat_session_manager",
]
