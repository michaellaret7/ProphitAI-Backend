"""Think Pruner - Manages context window by pruning thought content from think tool calls."""

from typing import List, Dict, Any
import json


def prune_think_content(
    messages: List[Dict[str, Any]],
    exclude_index: int = None,
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """Remove thought field from think tool call arguments to save context window.

    Args:
        messages: Full message history
        exclude_index: Optional index of assistant message to exclude from pruning
        verbose: Print pruning statistics

    Returns:
        Pruned message list with thought arguments removed but responses preserved
    """
    pruned_messages = []
    pruned_count = 0

    for i, msg in enumerate(messages):
        if exclude_index is not None and i == exclude_index:
            pruned_messages.append(msg)
            continue

        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            tool_calls = msg.get("tool_calls", [])

            has_think = False
            modified_tool_calls = []

            for tc in tool_calls:
                tool_name = None
                if hasattr(tc, 'function') and hasattr(tc.function, 'name'):
                    tool_name = tc.function.name
                elif isinstance(tc, dict) and 'function' in tc:
                    tool_name = tc['function'].get('name')

                if tool_name == "think":
                    has_think = True
                    modified_tc = _prune_think_content_from_tool_call(tc)
                    modified_tool_calls.append(modified_tc)
                    pruned_count += 1
                else:
                    modified_tool_calls.append(tc)

            if has_think:
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
        print(f"[context] Pruned {pruned_count} think argument(s) (responses preserved)")

    return pruned_messages


def _prune_think_content_from_tool_call(tool_call: Any) -> Any:
    """Remove thought field from a think tool call's arguments."""
    if hasattr(tool_call, 'function'):
        args_json = tool_call.function.arguments

        try:
            if isinstance(args_json, str):
                args = json.loads(args_json)
            else:
                args = args_json

            if "thought" in args:
                args["thought"] = "I recorded my thought it will appear in the tool content below"
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

            if "thought" in args:
                args["thought"] = "I recorded my thought it will appear in the tool content below"
                tool_call['function']['arguments'] = json.dumps(args)

        except (json.JSONDecodeError, KeyError):
            pass

        return tool_call

    else:
        return tool_call
