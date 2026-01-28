"""Core pruning logic for completed task messages.

This module provides functions to remove completed task update_tasks messages
from the conversation history to manage context window size while preserving
work summaries in the plan status block.
"""

from typing import List, Dict, Any, Optional, Set
from .utils import parse_tool_call_arguments, find_tool_response_index


def prune_completed_task_messages(
    messages: List[Dict[str, Any]],
    main_task: Optional[str] = None,
    subtasks: Optional[List[str]] = None,
    exclude_index: Optional[int] = None,
    verbose: bool = True,
    prune_all_completed: bool = False,
    prune_status: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Remove update_tasks tool calls to manage context window.

    Args:
        messages: Full message history
        main_task: Main task ID (e.g., "2")
        subtasks: Optional list of subtask IDs (e.g., ["2c", "2d"])
        exclude_index: Optional index of assistant message to exclude from pruning
        verbose: Print pruning statistics
        prune_all_completed: If True, prunes ALL completed status update_tasks
        prune_status: If provided, only prunes update_tasks with this status

    Returns:
        Pruned message list with tool calls removed but thinking preserved
    """
    matching_indices = _find_update_tasks_calls(
        messages, main_task, subtasks, exclude_index, prune_all_completed, prune_status
    )

    if not matching_indices:
        return messages

    tool_call_ids_to_remove: Set[str] = set()
    for idx in matching_indices:
        assistant_msg = messages[idx]
        ids = _get_tool_call_ids_for_task(assistant_msg, main_task, subtasks, prune_all_completed, prune_status)
        tool_call_ids_to_remove.update(ids)

    if not tool_call_ids_to_remove:
        return messages

    pruned_messages = _remove_message_pairs(messages, list(tool_call_ids_to_remove))

    if verbose:
        removed_count = len(messages) - len(pruned_messages)

        if prune_all_completed:
            task_label = "all completed tasks"
        elif prune_status:
            task_label = f"Task {main_task}"
            if subtasks:
                task_label += f" (subtasks: {', '.join(subtasks)})"
            task_label += f" [{prune_status} calls]"
        else:
            task_label = f"Task {main_task}"
            if subtasks:
                task_label += f" (subtasks: {', '.join(subtasks)})"

        print(f"Pruned {len(tool_call_ids_to_remove)} tool calls + {removed_count} tool responses for {task_label}")

    return pruned_messages


def _find_update_tasks_calls(
    messages: List[Dict[str, Any]],
    main_task: Optional[str],
    subtasks: Optional[List[str]] = None,
    exclude_index: Optional[int] = None,
    prune_all_completed: bool = False,
    prune_status: Optional[str] = None
) -> List[int]:
    """Find indices of update_tasks calls matching task/subtasks/status."""
    matching_indices = []

    for i, msg in enumerate(messages):
        if exclude_index is not None and i == exclude_index:
            continue

        if msg.get("role") != "assistant":
            continue

        tool_calls = msg.get("tool_calls", [])
        if not tool_calls:
            continue

        for tc in tool_calls:
            tool_name = None
            if hasattr(tc, 'function') and hasattr(tc.function, 'name'):
                tool_name = tc.function.name
            elif isinstance(tc, dict) and 'function' in tc:
                tool_name = tc['function'].get('name')

            if tool_name != "update_tasks":
                continue

            args = parse_tool_call_arguments(tc)
            status = args.get("status", "")

            if prune_all_completed:
                if status in ("complete", "completed"):
                    matching_indices.append(i)
                    break
                continue

            if prune_status and status != prune_status:
                continue

            args_main_task = args.get("main_task")
            args_subtasks = args.get("subtasks", [])

            if main_task and args_main_task != main_task:
                continue

            if subtasks:
                if any(st in args_subtasks for st in subtasks):
                    matching_indices.append(i)
                    break
            else:
                matching_indices.append(i)
                break

    return matching_indices


def _get_tool_call_ids_for_task(
    assistant_message: Dict[str, Any],
    main_task: Optional[str],
    subtasks: Optional[List[str]] = None,
    prune_all_completed: bool = False,
    prune_status: Optional[str] = None
) -> List[str]:
    """Extract tool_call_ids from assistant message that match task criteria."""
    matching_ids = []

    tool_calls = assistant_message.get("tool_calls", [])
    for tc in tool_calls:
        tool_name = None
        if hasattr(tc, 'function') and hasattr(tc.function, 'name'):
            tool_name = tc.function.name
        elif isinstance(tc, dict) and 'function' in tc:
            tool_name = tc['function'].get('name')

        if tool_name != "update_tasks":
            continue

        args = parse_tool_call_arguments(tc)
        status = args.get("status", "")

        if prune_all_completed:
            if status not in ("complete", "completed"):
                continue
        else:
            if prune_status and status != prune_status:
                continue

            args_main_task = args.get("main_task")
            args_subtasks = args.get("subtasks", [])

            if main_task and args_main_task != main_task:
                continue

            if subtasks:
                if not any(st in args_subtasks for st in subtasks):
                    continue

        tool_call_id = None
        if hasattr(tc, 'id'):
            tool_call_id = tc.id
        elif isinstance(tc, dict) and 'id' in tc:
            tool_call_id = tc['id']

        if tool_call_id:
            matching_ids.append(tool_call_id)

    return matching_ids


def _remove_message_pairs(
    messages: List[Dict[str, Any]],
    tool_call_ids: List[str]
) -> List[Dict[str, Any]]:
    """Remove tool calls and their responses while preserving assistant message thinking."""
    if not tool_call_ids:
        return messages

    tool_call_ids_set = set(tool_call_ids)
    tool_response_indices_to_skip: Set[int] = set()

    for i, msg in enumerate(messages):
        if msg.get("role") == "tool":
            tool_call_id = msg.get("tool_call_id")
            if tool_call_id and tool_call_id in tool_call_ids_set:
                tool_response_indices_to_skip.add(i)

    pruned_messages = []

    for i, msg in enumerate(messages):
        if i in tool_response_indices_to_skip:
            continue

        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            tool_calls = msg.get("tool_calls", [])

            tool_calls_to_keep = []
            for tc in tool_calls:
                tc_id = None
                if hasattr(tc, 'id'):
                    tc_id = tc.id
                elif isinstance(tc, dict) and 'id' in tc:
                    tc_id = tc['id']

                if not (tc_id and tc_id in tool_call_ids_set):
                    tool_calls_to_keep.append(tc)

            if len(tool_calls_to_keep) < len(tool_calls):
                modified_msg = {
                    "role": msg["role"],
                    "content": msg.get("content", "")
                }

                if tool_calls_to_keep:
                    modified_msg["tool_calls"] = tool_calls_to_keep

                pruned_messages.append(modified_msg)
            else:
                pruned_messages.append(msg)
        else:
            pruned_messages.append(msg)

    return pruned_messages
