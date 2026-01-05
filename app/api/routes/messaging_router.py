"""
Messaging router for DM functionality.

Provides WebSocket endpoint for real-time messaging and REST endpoints
for fetching conversations and messages.
"""
import asyncio
import json
import logging
from typing import Dict, Optional
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from pydantic import ValidationError

from app.models.messaging_models import (
    MessageCreate,
    MessageResponse,
    ConversationResponse,
    ConversationListResponse,
    MessagesListResponse,
    UserSummary,
    WSSendMessage,
    WSMarkRead,
    WSTyping,
    WSNewMessage,
    WSTypingIndicator,
    WSReadReceipt,
    WSError,
    WSConnected,
)
from app.services.messaging import (
    send_message,
    get_conversations,
    get_messages,
    mark_conversation_read,
    get_unread_count,
    get_or_create_conversation,
)
from app.repositories import messaging_data as messages_repo
from app.utils.time_utils import get_current_utc_time

logger = logging.getLogger(__name__)

# Heartbeat interval in seconds
HEARTBEAT_INTERVAL = 30

router = APIRouter(prefix="/messaging", tags=["💬 Messaging"])


# =============================================================================
# CONNECTION MANAGER
# =============================================================================

class DMConnectionManager:
    """
    Manages WebSocket connections for direct messaging.

    Tracks connected users and provides methods to send messages
    to specific users or check their online status.
    """

    def __init__(self):
        # Map of user_id -> WebSocket connection
        self.connections: Dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        """
        Accept and register a WebSocket connection for a user.

        If user already has a connection, the old one is replaced.

        Args:
            user_id: The user's UUID as string
            websocket: The WebSocket connection
        """
        await websocket.accept()

        # Close existing connection if any
        if user_id in self.connections:
            try:
                await self.connections[user_id].close()
            except Exception:
                pass

        self.connections[user_id] = websocket
        logger.info(f"User {user_id} connected to messaging WebSocket")

    def disconnect(self, user_id: str) -> None:
        """
        Remove a user's WebSocket connection.

        Args:
            user_id: The user's UUID as string
        """
        self.connections.pop(user_id, None)
        logger.info(f"User {user_id} disconnected from messaging WebSocket")

    async def send_to_user(self, user_id: str, message: dict) -> bool:
        """
        Send a message to a specific user.

        Args:
            user_id: The recipient's UUID as string
            message: The message payload as dict

        Returns:
            True if message was sent, False if user not connected
        """
        websocket = self.connections.get(user_id)
        if not websocket:
            return False

        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"Failed to send message to {user_id}: {e}")
            self.disconnect(user_id)
            return False

    def is_online(self, user_id: str) -> bool:
        """
        Check if a user is currently connected.

        Args:
            user_id: The user's UUID as string

        Returns:
            True if user is connected, False otherwise
        """
        return user_id in self.connections

    def get_online_users(self) -> list[str]:
        """Get list of all connected user IDs."""
        return list(self.connections.keys())


# Global connection manager instance
connection_manager = DMConnectionManager()


# =============================================================================
# WEBSOCKET ENDPOINT
# =============================================================================

@router.websocket("/ws/{user_id}")
async def messaging_websocket(
    websocket: WebSocket,
    user_id: str,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time messaging.

    Connect: ws://host/messaging/ws/{user_id}?token=<jwt>

    Incoming messages (client -> server):
    - send_message: Send a message to another user
    - mark_read: Mark a conversation as read
    - typing: Send typing indicator

    Outgoing messages (server -> client):
    - connected: Connection confirmed with unread count
    - new_message: New message received
    - typing: Someone is typing
    - read_receipt: Message was read
    - error: Error occurred
    - heartbeat: Keepalive ping
    """
    # TODO: Validate JWT token
    # For now, we accept all connections
    # user = await validate_ws_token(token)
    # if not user or str(user.id) != user_id:
    #     await websocket.close(code=4001)
    #     return

    await connection_manager.connect(user_id, websocket)

    # Send connection confirmation with unread count
    try:
        unread = get_unread_count(UUID(user_id))
        await websocket.send_json(
            WSConnected(user_id=UUID(user_id), unread_count=unread).model_dump(mode='json')
        )
    except Exception as e:
        logger.error(f"Error sending connection confirmation: {e}")

    # Heartbeat task
    async def send_heartbeat():
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
            raw_data = await websocket.receive_text()

            try:
                data = json.loads(raw_data)
                msg_type = data.get("type")

                if msg_type == "send_message":
                    await _handle_send_message(user_id, data)

                elif msg_type == "mark_read":
                    await _handle_mark_read(user_id, data)

                elif msg_type == "typing":
                    await _handle_typing(user_id, data)

                else:
                    await websocket.send_json(
                        WSError(message=f"Unknown message type: {msg_type}").model_dump(mode='json')
                    )

            except json.JSONDecodeError:
                await websocket.send_json(
                    WSError(message="Invalid JSON", code="INVALID_JSON").model_dump(mode='json')
                )
            except ValidationError as e:
                await websocket.send_json(
                    WSError(message=str(e), code="VALIDATION_ERROR").model_dump(mode='json')
                )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        heartbeat_task.cancel()
        connection_manager.disconnect(user_id)


async def _handle_send_message(sender_id: str, data: dict) -> None:
    """Handle incoming send_message WebSocket message."""
    try:
        msg = WSSendMessage(**data)

        # Send message via service
        message_response = send_message(
            sender_id=UUID(sender_id),
            recipient_id=msg.recipient_id,
            content=msg.content,
            message_type=msg.message_type.value
        )

        if not message_response:
            sender_ws = connection_manager.connections.get(sender_id)
            if sender_ws:
                await sender_ws.send_json(
                    WSError(message="Failed to send message", code="SEND_FAILED").model_dump(mode='json')
                )
            return

        # Notify recipient if online
        recipient_id = str(msg.recipient_id)
        if connection_manager.is_online(recipient_id):
            await connection_manager.send_to_user(
                recipient_id,
                WSNewMessage(message=message_response).model_dump(mode='json')
            )

    except Exception as e:
        logger.error(f"Error handling send_message: {e}")


async def _handle_mark_read(user_id: str, data: dict) -> None:
    """Handle incoming mark_read WebSocket message."""
    try:
        msg = WSMarkRead(**data)

        success = mark_conversation_read(UUID(user_id), msg.conversation_id)

        if success:
            # Notify the other user about read receipt
            # First get the conversation to find the other user
            conversation = messages_repo.get_conversation(msg.conversation_id)

            if conversation:
                other_user_id = str(conversation.user_2_id) if str(conversation.user_1_id) == user_id else str(conversation.user_1_id)

                if connection_manager.is_online(other_user_id):
                    await connection_manager.send_to_user(
                        other_user_id,
                        WSReadReceipt(
                            conversation_id=msg.conversation_id,
                            user_id=UUID(user_id),
                            read_at=get_current_utc_time()
                        ).model_dump(mode='json')
                    )

    except Exception as e:
        logger.error(f"Error handling mark_read: {e}")


async def _handle_typing(user_id: str, data: dict) -> None:
    """Handle incoming typing WebSocket message."""
    try:
        msg = WSTyping(**data)

        # Get conversation to find the other user
        conversation = messages_repo.get_conversation(msg.conversation_id)

        if conversation:
            other_user_id = str(conversation.user_2_id) if str(conversation.user_1_id) == user_id else str(conversation.user_1_id)

            if connection_manager.is_online(other_user_id):
                await connection_manager.send_to_user(
                    other_user_id,
                    WSTypingIndicator(
                        conversation_id=msg.conversation_id,
                        user_id=UUID(user_id),
                        is_typing=msg.is_typing
                    ).model_dump(mode='json')
                )

    except Exception as e:
        logger.error(f"Error handling typing: {e}")


# =============================================================================
# REST ENDPOINTS
# =============================================================================

@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(user_id: str = Query(..., description="User's UUID")):
    """
    Get all conversations for a user.

    Returns conversations sorted by most recent activity,
    with last message preview and unread count.
    """
    # TODO: Get user_id from JWT token instead of query param
    try:
        return get_conversations(UUID(user_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")


@router.get("/conversations/{conversation_id}/messages", response_model=MessagesListResponse)
async def list_messages(
    conversation_id: str,
    user_id: str = Query(..., description="User's UUID"),
    limit: int = Query(50, ge=1, le=100),
    before: Optional[str] = Query(None, description="ISO timestamp for pagination")
):
    """
    Get messages in a conversation with pagination.

    Use the 'before' parameter with the oldest message's timestamp
    to fetch earlier messages.
    """
    # TODO: Get user_id from JWT token instead of query param
    try:
        from datetime import datetime
        before_dt = datetime.fromisoformat(before) if before else None

        result = get_messages(
            user_id=UUID(user_id),
            conversation_id=UUID(conversation_id),
            limit=limit,
            before=before_dt
        )

        if result is None:
            raise HTTPException(status_code=404, detail="Conversation not found or access denied")

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter format: {e}")


@router.post("/messages", response_model=MessageResponse)
async def create_message(
    message: MessageCreate,
    user_id: str = Query(..., description="Sender's UUID")
):
    """
    Send a message to another user.

    Creates or retrieves the conversation automatically.
    """
    # TODO: Get user_id from JWT token instead of query param
    try:
        result = send_message(
            sender_id=UUID(user_id),
            recipient_id=message.recipient_id,
            content=message.content,
            message_type=message.message_type.value
        )

        if result is None:
            raise HTTPException(status_code=500, detail="Failed to send message")

        # Notify recipient via WebSocket if online
        recipient_id = str(message.recipient_id)
        if connection_manager.is_online(recipient_id):
            await connection_manager.send_to_user(
                recipient_id,
                WSNewMessage(message=result).model_dump(mode='json')
            )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter format: {e}")


@router.post("/conversations/{conversation_id}/read")
async def mark_read(
    conversation_id: str,
    user_id: str = Query(..., description="User's UUID")
):
    """
    Mark all messages in a conversation as read.
    """
    # TODO: Get user_id from JWT token instead of query param
    try:
        success = mark_conversation_read(UUID(user_id), UUID(conversation_id))

        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found or access denied")

        return {"status": "ok"}

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")


@router.get("/unread-count")
async def get_unread(
    user_id: str = Query(..., description="User's UUID"),
    conversation_id: Optional[str] = Query(None, description="Optional conversation UUID")
):
    """
    Get unread message count.

    If conversation_id is provided, returns count for that conversation.
    Otherwise, returns total unread count across all conversations.
    """
    # TODO: Get user_id from JWT token instead of query param
    try:
        conv_uuid = UUID(conversation_id) if conversation_id else None
        count = get_unread_count(UUID(user_id), conv_uuid)
        return {"unread_count": count}

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    user_id: str = Query(..., description="User's UUID"),
    other_user_id: str = Query(..., description="Other user's UUID")
):
    """
    Get or create a conversation with another user.
    """
    # TODO: Get user_id from JWT token instead of query param
    try:
        result = get_or_create_conversation(UUID(user_id), UUID(other_user_id))

        if result is None:
            raise HTTPException(status_code=500, detail="Failed to create conversation")

        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")


@router.get("/users/search", response_model=list[UserSummary])
async def search_users(
    q: str = Query(..., min_length=1, description="Search term for name or email")
):
    """
    Search for users by name or email.

    Returns users whose first name, last name, or email matches the search term.
    """
    users = messages_repo.search_users(q)
    return [
        UserSummary(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email
        )
        for user in users
    ]
