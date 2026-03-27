"""Request/response schemas for chat endpoints."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    """Request body for creating a chat session."""

    user_id: str = Field(
        ...,
        description="Clerk user ID for broker context injection.",
    )


class CreateSessionResponse(BaseModel):
    """Response from creating a chat session."""

    session_id: str = Field(..., description="Unique identifier for the session")
    created_at: str = Field(..., description="ISO timestamp of session creation")


class SendMessageRequest(BaseModel):
    """Request body for sending a message."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The message to send to the agent",
    )


class SendMessageResponse(BaseModel):
    """Response from sending a message."""

    message_id: str = Field(..., description="Unique identifier for this message")
    status: str = Field(default="processing", description="Current processing status")


class MessageHistoryResponse(BaseModel):
    """Response containing conversation history."""

    session_id: str = Field(..., description="The session ID")
    messages: List[Dict[str, Any]] = Field(
        ..., description="List of messages with role and content"
    )


class ExportPDFRequest(BaseModel):
    """Request body for exporting an agent response to PDF."""

    content: str = Field(
        ...,
        min_length=1,
        description="Markdown content from the agent response to convert to PDF",
    )
    title: Optional[str] = Field(
        default=None,
        description="Optional title displayed at the top of the PDF",
    )
