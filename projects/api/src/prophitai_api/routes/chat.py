"""Chat router for interactive agent chat sessions.

Provides REST and WebSocket endpoints for:
- Creating chat sessions
- Sending messages (triggers agent execution)
- Retrieving conversation history
- Real-time streaming via WebSocket
- PDF export of agent responses
"""

import asyncio
import io

from fastapi import APIRouter, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from prophitai_api.controllers.chat import (
    create_session_controller,
    send_message_controller,
    get_history_controller,
    export_pdf_controller,
)
from prophitai_api.schemas.chat import (
    CreateSessionRequest,
    CreateSessionResponse,
    SendMessageRequest,
    SendMessageResponse,
    MessageHistoryResponse,
    ExportPDFRequest,
)
from prophitai_api.services.sessions.connection_manager import connection_manager, websocket_heartbeat

router = APIRouter(prefix="/chat", tags=["Chat"])


# ================================
# --> REST Endpoints
# ================================


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_chat_session(request: CreateSessionRequest) -> CreateSessionResponse:
    """Create a new chat session."""
    result = await create_session_controller(user_id=request.user_id)
    return CreateSessionResponse(**result)


@router.post("/sessions/{session_id}/messages", response_model=SendMessageResponse)
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    background_tasks: BackgroundTasks,
) -> SendMessageResponse:
    """Send a message and start agent processing."""
    result = await send_message_controller(
        session_id=session_id,
        message=request.message,
        background_tasks=background_tasks,
    )
    return SendMessageResponse(**result)


@router.get("/sessions/{session_id}/history", response_model=MessageHistoryResponse)
async def get_chat_history(session_id: str) -> MessageHistoryResponse:
    """Get conversation history for a session."""
    result = await get_history_controller(session_id=session_id)
    return MessageHistoryResponse(**result)


@router.post("/export-pdf")
async def export_pdf(request: ExportPDFRequest) -> StreamingResponse:
    """Convert an agent response (markdown) to a branded PDF."""
    pdf_bytes = await export_pdf_controller(content=request.content, title=request.title)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="prophitai_export.pdf"'},
    )


# ================================
# --> WebSocket Endpoint
# ================================


@router.websocket("/ws/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str) -> None:
    """WebSocket for real-time chat updates.

    Streams events during agent execution: run_started, iteration_start/end,
    tool_call_start, tool_call_result, run_finished, run_error, heartbeat.
    """
    await connection_manager.connect(session_id, websocket)
    heartbeat_task = asyncio.create_task(websocket_heartbeat(websocket))

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        heartbeat_task.cancel()
        connection_manager.disconnect(session_id)
