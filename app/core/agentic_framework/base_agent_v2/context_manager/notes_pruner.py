"""
Notes Pruner - Manages context window by pruning note content from write_note tool calls.

The notes system provides an out-of-context scratchpad for agents. However, the note content
becomes part of the message history when the tool is called. This pruner removes the content
argument while keeping the title, so the agent knows what notes exist without bloating context.
"""
from typing import List, Dict, Any
import json


def prune_note_content(
    messages: List[Dict[str, Any]],
    exclude_index: int = None,
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """Remove content field from write_note tool calls to save context window.

    After write_note executes, the note content is saved to disk. Keeping the full content
    in the message history is redundant and defeats the purpose of having an out-of-context
    notepad. This function removes the content field while preserving the title.

    **Important**: The assistant message and title are PRESERVED. Only the content field
    is removed from the arguments.

    Args:
        messages: Full message history
        exclude_index: Optional index of assistant message to exclude from pruning
                      (used to avoid pruning the current message being processed)
        verbose: Print pruning statistics

    Returns:
        Pruned message list with note content removed but titles preserved

    Example:
        # After write_note executes successfully:
        pruned = prune_note_content(messages, exclude_index=15)
        # Result: Arguments changed from {"title": "...", "content": "..."}
        #         to {"title": "...", "content": "[pruned]"}
    """
    pruned_messages = []
    pruned_count = 0

    for i, msg in enumerate(messages):
        # Skip excluded index
        if exclude_index is not None and i == exclude_index:
            pruned_messages.append(msg)
            continue

        # Check if this is an assistant message with tool_calls
        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            tool_calls = msg.get("tool_calls", [])

            # Check if any tool calls are write_note and modify them
            has_write_note = False
            modified_tool_calls = []

            for tc in tool_calls:
                # Get tool name
                tool_name = None
                if hasattr(tc, 'function') and hasattr(tc.function, 'name'):
                    tool_name = tc.function.name
                elif isinstance(tc, dict) and 'function' in tc:
                    tool_name = tc['function'].get('name')

                # If it's write_note, prune the content
                if tool_name == "write_note":
                    has_write_note = True
                    modified_tc = _prune_note_content_from_tool_call(tc)
                    modified_tool_calls.append(modified_tc)
                    pruned_count += 1
                else:
                    # Keep other tool calls unchanged
                    modified_tool_calls.append(tc)

            # If we found write_note calls, create modified message with pruned content
            if has_write_note:
                # Create new message with pruned tool_calls
                modified_msg = {
                    "role": msg["role"],
                    "content": msg.get("content", ""),
                    "tool_calls": modified_tool_calls
                }
                pruned_messages.append(modified_msg)
            else:
                # No write_note calls, keep message exactly as-is
                pruned_messages.append(msg)
        else:
            # Keep all other messages as-is
            pruned_messages.append(msg)

    # Print stats if verbose
    if verbose and pruned_count > 0:
        print(f"🗑️  Pruned {pruned_count} note content fields (titles preserved)")
        print(f"   Message count: {len(messages)} (no change, only content removed)")

    return pruned_messages


def _prune_note_content_from_tool_call(tool_call: Any) -> Any:
    """Remove content field from a write_note tool call's arguments.

    IMPORTANT: This function modifies the tool_call IN PLACE to preserve object references
    and prevent 'dict' object has no attribute 'id' errors downstream.

    Args:
        tool_call: Tool call object (OpenAI format)

    Returns:
        The same tool call object with content replaced by "[pruned]"
    """
    # Handle both object and dict formats
    if hasattr(tool_call, 'function'):
        # Object format - modify in place
        args_json = tool_call.function.arguments

        try:
            if isinstance(args_json, str):
                args = json.loads(args_json)
            else:
                args = args_json

            # Replace content with placeholder
            if "content" in args:
                args["content"] = "[pruned]"
                # Update the arguments string in place
                tool_call.function.arguments = json.dumps(args)

        except (json.JSONDecodeError, AttributeError):
            # If parsing fails, leave unchanged
            pass

        # Return the modified object (not a new dict)
        return tool_call

    elif isinstance(tool_call, dict):
        # Dict format - modify in place
        try:
            args_json = tool_call.get('function', {}).get('arguments', '{}')

            if isinstance(args_json, str):
                args = json.loads(args_json)
            else:
                args = args_json

            # Replace content with placeholder
            if "content" in args:
                args["content"] = "[pruned]"
                # Update in place
                tool_call['function']['arguments'] = json.dumps(args)

        except (json.JSONDecodeError, KeyError):
            # If parsing fails, leave unchanged
            pass

        # Return the modified dict
        return tool_call

    else:
        # Unknown format, return as-is
        return tool_call
