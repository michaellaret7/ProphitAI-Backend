"""
Shared services used across multiple domains.

Provides services for:
- Agent execution orchestration
- Stock price data fetching
- WebSocket connection management
"""

from app.services.shared.agent_runs import start_agent_run, RESULT_CACHE_KEY_TEMPLATE, RESULT_CACHE_TTL
from app.services.shared.price import PriceService
from app.services.shared.websocket_manager import (
    WebSocketConnectionManager,
    ws_manager,
    attach_agent_stream,
)

__all__ = [
    'start_agent_run',
    'RESULT_CACHE_KEY_TEMPLATE',
    'RESULT_CACHE_TTL',
    'PriceService',
    'WebSocketConnectionManager',
    'ws_manager',
    'attach_agent_stream',
]
