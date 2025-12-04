"""
Shared services used across multiple domains.

Provides services for:
- Stock price data fetching
- Agent execution management with WebSocket streaming
"""

from app.services.shared.price import PriceService
from app.services.shared.agent_executor import (
    AgentExecutionManager,
    ExecutionState,
    ExecutionStatus,
    WebSocketCallback,
    execution_manager,
    run_agent_background,
)

__all__ = [
    # Price service
    "PriceService",
    # Agent execution
    "AgentExecutionManager",
    "ExecutionState",
    "ExecutionStatus",
    "WebSocketCallback",
    "execution_manager",
    "run_agent_background",
]
