"""Context Manager - Manages conversation context window.

This module provides utilities for pruning completed task messages
to keep the context window manageable while preserving work summaries
in the plan status block.
"""

from .message_pruner import prune_completed_task_messages
from .utils import (
    parse_tool_call_arguments,
    find_tool_response_index,
    count_messages_by_role,
    get_message_token_estimate
)

__all__ = [
    "prune_completed_task_messages",
    "parse_tool_call_arguments", 
    "find_tool_response_index",
    "count_messages_by_role",
    "get_message_token_estimate"
]