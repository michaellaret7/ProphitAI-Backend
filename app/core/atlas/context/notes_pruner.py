"""Notes Pruner - Manages context window by pruning note content from write_note tool calls."""

from typing import List, Dict, Any
import json


def prune_note_content(
    messages: List[Dict[str, Any]],
    exclude_index: int = None,
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """Remove content field from write_note tool calls to save context window.

    Args:
        messages: Full message history
        exclude_index: Optional index of assistant message to exclude from pruning
        verbose: Print pruning statistics

    Returns:
        Pruned message list with note content removed but titles preserved
    """
    pruned_messages = []
    pruned_count = 0

    for i, msg in enumerate(messages):
        if exclude_index is not None and i == exclude_index:
            pruned_messages.append(msg)
            continue

        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            tool_calls = msg.get("tool_calls", [])

            has_write_note = False
            modified_tool_calls = []

            for tc in tool_calls:
                tool_name = None
                if hasattr(tc, 'function') and hasattr(tc.function, 'name'):
                    tool_name = tc.function.name
                elif isinstance(tc, dict) and 'function' in tc:
                    tool_name = tc['function'].get('name')

                if tool_name == "write_note":
                    has_write_note = True
                    modified_tc = _prune_note_content_from_tool_call(tc)
                    modified_tool_calls.append(modified_tc)
                    pruned_count += 1
                else:
                    modified_tool_calls.append(tc)

            if has_write_note:
                modified_msg = {
                    "role": msg["role"],
                    "content": msg.get("content", ""),
                    "tool_calls": modified_tool_calls
                }
                pruned_messages.append(modified_msg)
            else:
                pruned_messages.append(msg)
        else:
            pruned_messages.append(msg)

    if verbose and pruned_count > 0:
        print(f"Pruned {pruned_count} note content fields (titles preserved)")

    return pruned_messages


def _prune_note_content_from_tool_call(tool_call: Any) -> Any:
    """Remove content field from a write_note tool call's arguments."""
    if hasattr(tool_call, 'function'):
        args_json = tool_call.function.arguments

        try:
            if isinstance(args_json, str):
                args = json.loads(args_json)
            else:
                args = args_json

            if "content" in args:
                args["content"] = "[pruned]"
                tool_call.function.arguments = json.dumps(args)

        except (json.JSONDecodeError, AttributeError):
            pass

        return tool_call

    elif isinstance(tool_call, dict):
        try:
            args_json = tool_call.get('function', {}).get('arguments', '{}')

            if isinstance(args_json, str):
                args = json.loads(args_json)
            else:
                args = args_json

            if "content" in args:
                args["content"] = "[pruned]"
                tool_call['function']['arguments'] = json.dumps(args)

        except (json.JSONDecodeError, KeyError):
            pass

        return tool_call

    else:
        return tool_call
