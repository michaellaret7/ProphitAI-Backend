"""
Pydantic schemas for messaging API.

Contains request/response models for REST endpoints and WebSocket messages.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Literal, Union
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# ENUMS
# =============================================================================

class MessageType(str, Enum):
    """Supported message content types."""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"


# =============================================================================
# REST API - REQUEST SCHEMAS
# =============================================================================

class MessageCreate(BaseModel):
    """Request schema for sending a new message."""
    recipient_id: UUID = Field(..., description="UUID of the message recipient")
    content: str = Field(..., min_length=1, max_length=10000, description="Message content")
    message_type: MessageType = Field(default=MessageType.TEXT, description="Type of message")


class MarkReadRequest(BaseModel):
    """Request schema for marking a conversation as read."""
    conversation_id: UUID = Field(..., description="UUID of the conversation to mark as read")


# =============================================================================
# REST API - RESPONSE SCHEMAS
# =============================================================================

class MessageResponse(BaseModel):
    """Response schema for a single message."""
    id: UUID
    conversation_id: UUID
    sender_id: UUID
    content: str
    message_type: str
    created_at: datetime

    class Config:
        from_attributes = True


class UserSummary(BaseModel):
    """Minimal user info for conversation display."""
    id: UUID
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: str

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    """Response schema for a conversation with metadata."""
    id: UUID
    other_user: UserSummary
    last_message: Optional[MessageResponse] = None
    unread_count: int = 0
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    """Response schema for list of conversations."""
    conversations: list[ConversationResponse]
    total_unread: int = 0


class MessagesListResponse(BaseModel):
    """Response schema for paginated messages."""
    messages: list[MessageResponse]
    has_more: bool = False


# =============================================================================
# WEBSOCKET - INCOMING MESSAGES (Client -> Server)
# =============================================================================

class WSSendMessage(BaseModel):
    """WebSocket: Client sends a message."""
    type: Literal["send_message"] = "send_message"
    recipient_id: UUID
    content: str = Field(..., min_length=1, max_length=10000)
    message_type: MessageType = MessageType.TEXT


class WSMarkRead(BaseModel):
    """WebSocket: Client marks conversation as read."""
    type: Literal["mark_read"] = "mark_read"
    conversation_id: UUID


class WSTyping(BaseModel):
    """WebSocket: Client typing indicator."""
    type: Literal["typing"] = "typing"
    conversation_id: UUID
    is_typing: bool = True


# Union type for all incoming WebSocket messages
WSIncomingMessage = Union[WSSendMessage, WSMarkRead, WSTyping]


# =============================================================================
# WEBSOCKET - OUTGOING MESSAGES (Server -> Client)
# =============================================================================

class WSNewMessage(BaseModel):
    """WebSocket: Server notifies of new message."""
    type: Literal["new_message"] = "new_message"
    message: MessageResponse


class WSTypingIndicator(BaseModel):
    """WebSocket: Server broadcasts typing indicator."""
    type: Literal["typing"] = "typing"
    conversation_id: UUID
    user_id: UUID
    is_typing: bool


class WSReadReceipt(BaseModel):
    """WebSocket: Server notifies message was read."""
    type: Literal["read_receipt"] = "read_receipt"
    conversation_id: UUID
    user_id: UUID
    read_at: datetime


class WSError(BaseModel):
    """WebSocket: Server sends error."""
    type: Literal["error"] = "error"
    message: str
    code: Optional[str] = None


class WSConnected(BaseModel):
    """WebSocket: Server confirms connection."""
    type: Literal["connected"] = "connected"
    user_id: UUID
    unread_count: int = 0


# Union type for all outgoing WebSocket messages
WSOutgoingMessage = Union[WSNewMessage, WSTypingIndicator, WSReadReceipt, WSError, WSConnected]
