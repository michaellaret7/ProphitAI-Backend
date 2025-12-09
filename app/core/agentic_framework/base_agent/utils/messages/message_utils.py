"""Utility functions for managing agent message history."""

from typing import List, Dict, Any

def remove_system_messages(
    messages: List[Dict[str, Any]],
    patterns: List[str]
) -> List[Dict[str, Any]]:
    """Remove system messages that contain any of the given patterns.

    Used to clear out old system messages before injecting fresh versions
    each iteration (e.g., notes reminders, think prompts).

    Args:
        messages: The agent's message history.
        patterns: List of string patterns to match against message content.
                  Messages containing any pattern will be removed.

    Returns:
        Filtered message list with matching system messages removed.
    """
    return [
        msg for msg in messages
        if not (
            msg.get("role") == "system" and
            any(pattern in msg.get("content", "") for pattern in patterns)
        )
    ]