"""WebSocket router for streaming agent task state updates to frontend."""

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from prophitai_api.services.sessions.connection_manager import connection_manager, websocket_heartbeat

router = APIRouter(tags=["Agent WebSocket"])


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
    heartbeat_task = asyncio.create_task(websocket_heartbeat(websocket))

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
