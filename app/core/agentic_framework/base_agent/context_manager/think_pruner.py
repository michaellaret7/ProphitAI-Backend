"""
Think Pruner - Manages context window by pruning thought content from think tool calls.

The think tool records reasoning into the context window. However, both the argument and
the tool response contain the same thought text, causing duplication. This pruner removes
the thought from the argument while keeping it in the tool response, halving context cost.
"""
from typing import List, Dict, Any
import json


def prune_think_content(
    messages: List[Dict[str, Any]],
    exclude_index: int = None,
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """Remove thought field from think tool call arguments to save context window.

    After think executes, the thought content appears in both the tool call arguments
    AND the tool response. This is redundant - the model only needs to see it once.
    This function removes the thought from arguments while preserving it in the response.

    Args:
        messages: Full message history
        exclude_index: Optional index of assistant message to exclude from pruning
                      (used to avoid pruning the current message being processed)
        verbose: Print pruning statistics

    Returns:
        Pruned message list with thought arguments removed but responses preserved

    Example:
        # After think executes successfully:
        pruned = prune_think_content(messages, exclude_index=15)
        # Result: Arguments changed from {"thought": "...reasoning..."}
        #         to {"thought": "I recorded my thought it will appear in the tool content below"}
        # Tool response still contains full thought
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

            # Check if any tool calls are think and modify them
            has_think = False
            modified_tool_calls = []

            for tc in tool_calls:
                # Get tool name
                tool_name = None
                if hasattr(tc, 'function') and hasattr(tc.function, 'name'):
                    tool_name = tc.function.name
                elif isinstance(tc, dict) and 'function' in tc:
                    tool_name = tc['function'].get('name')

                # If it's think, prune the thought content
                if tool_name == "think":
                    has_think = True
                    modified_tc = _prune_think_content_from_tool_call(tc)
                    modified_tool_calls.append(modified_tc)
                    pruned_count += 1
                else:
                    # Keep other tool calls unchanged
                    modified_tool_calls.append(tc)

            # If we found think calls, create modified message with pruned content
            if has_think:
                # Create new message with pruned tool_calls
                modified_msg = {
                    "role": msg["role"],
                    "content": msg.get("content", ""),
                    "tool_calls": modified_tool_calls
                }
                pruned_messages.append(modified_msg)
            else:
                # No think calls, keep message exactly as-is
                pruned_messages.append(msg)
        else:
            # Keep all other messages as-is
            pruned_messages.append(msg)

    # Print stats if verbose
    if verbose and pruned_count > 0:
        print(f"[context] Pruned {pruned_count} think argument(s) (responses preserved)")

    return pruned_messages


def _prune_think_content_from_tool_call(tool_call: Any) -> Any:
    """Remove thought field from a think tool call's arguments.

    IMPORTANT: This function modifies the tool_call IN PLACE to preserve object references
    and prevent 'dict' object has no attribute 'id' errors downstream.

    We replace with a directive message rather than "[pruned]" because LLMs tend to
    copy placeholder patterns. The directive points to the tool response where the
    full thought is preserved.

    Args:
        tool_call: Tool call object (OpenAI format)

    Returns:
        The same tool call object with thought replaced by directive message
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

            # Replace thought with a directive to check tool response
            # Using "[pruned]" causes LLM to copy the pattern, so we use a helpful message
            if "thought" in args:
                args["thought"] = "I recorded my thought it will appear in the tool content below"
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

            # Replace thought with a directive to check tool response
            # Using "[pruned]" causes LLM to copy the pattern, so we use a helpful message
            if "thought" in args:
                args["thought"] = "I recorded my thought it will appear in the tool content below"
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
