"""WebSocket router for streaming agent task state updates to frontend."""

import asyncio
import json
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.utils.time_utils import get_current_utc_time

# Heartbeat interval in seconds (keeps connection alive on hosted platforms)
HEARTBEAT_INTERVAL = 30

router = APIRouter(tags=["Agent WebSocket"])


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
            "timestamp": get_current_utc_time().isoformat(),
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


# Global connection manager instance
connection_manager = ConnectionManager()


@router.websocket("/ws/agent/{execution_id}")
async def agent_websocket(websocket: WebSocket, execution_id: str):
    """WebSocket endpoint for streaming agent task state updates.

    Connect to receive real-time updates for an agent execution:
    - plan_created: When the agent creates its execution plan
    - task_update: When a task/subtask status changes
    - complete: When the agent finishes execution
    - heartbeat: Periodic keepalive signal

    The agent continues running even if this connection closes.
    Poll GET /api/agents/{execution_id}/result for final results.
    """
    await connection_manager.connect(execution_id, websocket)

    async def send_heartbeat():
        """Send periodic heartbeat to keep connection alive."""
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            try:
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": get_current_utc_time().isoformat()
                })
            except Exception:
                break

    heartbeat_task = asyncio.create_task(send_heartbeat())

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        heartbeat_task.cancel()
        connection_manager.disconnect(execution_id)
