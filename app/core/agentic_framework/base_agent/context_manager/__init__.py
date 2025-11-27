"""Context Manager - Manages conversation context window.

This module provides utilities for pruning messages to keep the context
window manageable:
- Prune completed task messages while preserving work summaries
- Prune note content while keeping note titles visible
"""

from .message_pruner import prune_completed_task_messages
from .notes_pruner import prune_note_content
from .think_pruner import prune_think_content
from .utils import (
    parse_tool_call_arguments,
    find_tool_response_index,
    count_messages_by_role,
    get_message_token_estimate
)

__all__ = [
    "prune_completed_task_messages",
    "prune_note_content",
    "prune_think_content",
    "parse_tool_call_arguments",
    "find_tool_response_index",
    "count_messages_by_role",
    "get_message_token_estimate"
]