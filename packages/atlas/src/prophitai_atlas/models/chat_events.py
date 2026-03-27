# prophitai_atlas/models/chat_events.py

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel


class ChatEventType(str, Enum):
    """WebSocket event types for chat streaming."""

    # Lifecycle events
    RUN_STARTED = "run_started"
    RUN_FINISHED = "run_finished"
    RUN_ERROR = "run_error"

    # Iteration events
    ITERATION_START = "iteration_start"
    ITERATION_END = "iteration_end"

    # Tool execution events
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_ARGS = "tool_call_args"      # Streaming arguments
    TOOL_CALL_END = "tool_call_end"
    TOOL_CALL_RESULT = "tool_call_result"

    # Text streaming events
    TEXT_DELTA = "text_delta"
    TEXT_COMPLETE = "text_complete"

    # Connection events
    HEARTBEAT = "heartbeat"


class ChatEvent(BaseModel):
    """Base event structure sent over WebSocket."""
    type: ChatEventType
    session_id: str
    timestamp: str
    payload: dict


# Specific payload models
class ToolCallStartPayload(BaseModel):
    tool_call_id: str
    tool_name: str
    iteration: int


class ToolCallArgsPayload(BaseModel):
    tool_call_id: str
    arguments: dict  # Full arguments (or stream incrementally)


class ToolCallResultPayload(BaseModel):
    tool_call_id: str
    tool_name: str
    result: Any
    success: bool
    duration_ms: int


class TextDeltaPayload(BaseModel):
    message_id: str
    delta: str  # Incremental text chunk


class RunFinishedPayload(BaseModel):
    answer: str
    tool_calls_made: list[str]
    iterations: int
    tokens_used: int
    stop_reason: str
