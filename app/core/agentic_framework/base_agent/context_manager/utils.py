"""Utility functions for message inspection and analysis.

This module provides helper functions for working with message lists,
parsing tool calls, and analyzing conversation context.
"""

import json
from typing import List, Dict, Any, Optional


def parse_tool_call_arguments(tool_call) -> Dict[str, Any]:
    """Safely parse tool call arguments from function.arguments JSON string.

    Args:
        tool_call: Tool call object with function.arguments attribute

    Returns:
        Parsed arguments as dictionary, empty dict if parsing fails

    Example:
        >>> args = parse_tool_call_arguments(tool_call)
        >>> print(args.get("main_task"))
        "2"
    """
    try:
        # Handle different tool call formats
        if hasattr(tool_call, 'function') and hasattr(tool_call.function, 'arguments'):
            args_json = tool_call.function.arguments
        elif isinstance(tool_call, dict) and 'function' in tool_call:
            args_json = tool_call['function'].get('arguments', '{}')
        else:
            return {}

        # Parse JSON string
        if isinstance(args_json, str):
            return json.loads(args_json)
        elif isinstance(args_json, dict):
            return args_json
        else:
            return {}

    except (json.JSONDecodeError, AttributeError, KeyError):
        # Return empty dict on parse failure (malformed JSON, missing attributes, or bad structure)
        # This is defensive - callers can check for empty dict and handle gracefully
        return {}


def find_tool_response_index(
    messages: List[Dict[str, Any]],
    tool_call_id: str,
    start_index: int = 0
) -> Optional[int]:
    """Find index of tool response message matching tool_call_id.

    Searches for a message with role='tool' and matching tool_call_id.

    Args:
        messages: Full message list
        tool_call_id: The tool_call_id to search for
        start_index: Index to start searching from (optimization)

    Returns:
        Index of matching tool response, or None if not found

    Example:
        >>> idx = find_tool_response_index(messages, "toolu_123", start_index=10)
        >>> if idx:
        ...     print(messages[idx]["content"])
    """
    for i in range(start_index, len(messages)):
        msg = messages[i]
        if msg.get("role") == "tool" and msg.get("tool_call_id") == tool_call_id:
            return i
    return None


def count_messages_by_role(messages: List[Dict[str, Any]]) -> Dict[str, int]:
    """Return count of messages by role (for debugging/stats).

    Args:
        messages: Full message list

    Returns:
        Dictionary mapping role to count

    Example:
        >>> counts = count_messages_by_role(messages)
        >>> print(f"Assistant: {counts['assistant']}, Tool: {counts['tool']}")
    """
    counts = {}
    for msg in messages:
        role = msg.get("role", "unknown")
        counts[role] = counts.get(role, 0) + 1
    return counts


def get_message_token_estimate(messages: List[Dict[str, Any]]) -> int:
    """Estimate token count for message list (rough heuristic).

    Uses simple heuristic: ~4 characters per token (conservative estimate).
    Does not account for message structure overhead or tool call formatting.

    **WARNING**: This is a rough approximation for monitoring purposes only.
    DO NOT use for strict token limit enforcement. For accurate counts,
    use tiktoken library or the model's actual token counter.

    Args:
        messages: Full message list

    Returns:
        Estimated token count (approximate)

    Example:
        >>> tokens = get_message_token_estimate(messages)
        >>> print(f"Estimated tokens: {tokens}")
    """
    total_chars = 0

    for msg in messages:
        # Count content
        content = msg.get("content", "")
        if isinstance(content, str):
            total_chars += len(content)

        # Count tool calls (if present)
        tool_calls = msg.get("tool_calls", [])
        if tool_calls:
            for tc in tool_calls:
                # Count function name and arguments
                if hasattr(tc, 'function'):
                    total_chars += len(getattr(tc.function, 'name', ''))
                    total_chars += len(getattr(tc.function, 'arguments', ''))
                elif isinstance(tc, dict) and 'function' in tc:
                    total_chars += len(tc['function'].get('name', ''))
                    total_chars += len(tc['function'].get('arguments', ''))

    # Rough conversion: 4 characters per token (conservative)
    estimated_tokens = total_chars // 4

    return estimated_tokens
