"""WebSocket ConnectionManager for streaming agent task state updates to frontend."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for agent execution streaming.

    One client per execution_id (no multi-client support needed).
    Agent continues running even if WebSocket disconnects.
    """

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, execution_id: str, websocket: WebSocket) -> None:
        """Accept and register a WebSocket connection for an execution.

        Args:
            execution_id: The unique identifier for the agent execution.
            websocket: The WebSocket connection to register.
        """
        await websocket.accept()
        # Replace any existing connection for this execution_id
        if execution_id in self.active_connections:
            try:
                await self.active_connections[execution_id].close()
            except Exception:
                pass
        self.active_connections[execution_id] = websocket

    def disconnect(self, execution_id: str) -> None:
        """Remove a WebSocket connection.

        Args:
            execution_id: The execution_id to disconnect.
        """
        self.active_connections.pop(execution_id, None)

    async def send_message(self, execution_id: str, message_type: str, payload: dict) -> bool:
        """Send a JSON message to the connected client.

        Args:
            execution_id: The execution to send the message to.
            message_type: The type of message (plan_created, task_update, complete).
            payload: The message payload.

        Returns:
            True if message was sent, False if no connection or send failed.
        """
        websocket = self.active_connections.get(execution_id)
        if websocket is None:
            return False

        message = {
            "type": message_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        }

        try:
            await websocket.send_json(message)
            return True
        except Exception:
            # Connection likely closed, remove it
            self.disconnect(execution_id)
            return False

    def has_connection(self, execution_id: str) -> bool:
        """Check if there's an active connection for an execution.

        Args:
            execution_id: The execution to check.

        Returns:
            True if connected, False otherwise.
        """
        return execution_id in self.active_connections


async def websocket_heartbeat(websocket: WebSocket, interval: int = 30) -> None:
    """Send periodic heartbeat messages to keep a WebSocket connection alive.

    Runs indefinitely until the connection closes or an error occurs.
    Designed to be used as an asyncio task.

    Args:
        websocket: The WebSocket connection to send heartbeats on.
        interval: Seconds between heartbeats (default 30).
    """
    from prophitai_shared.time_utils import get_current_utc_time

    while True:
        await asyncio.sleep(interval)
        try:
            await websocket.send_json({
                "type": "heartbeat",
                "timestamp": get_current_utc_time().isoformat(),
            })
        except Exception:
            break


# Global connection manager instance
connection_manager = ConnectionManager()
