from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.websocket_manager import ws_manager

router = APIRouter()

@router.websocket("/ws/agents/{run_id}")
async def stream_agent_evidence(ws: WebSocket, run_id: str):
    # Add auth before accept if needed
    await ws_manager.connect(run_id, ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(run_id, ws)