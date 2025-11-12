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

    Prunes tool calls at state transitions to save tokens while preserving thinking:
    - When task completes: prune old in_progress calls for that task
    - When new task starts: prune ALL old completed calls

    This prevents infinite loops - the model needs to see state transitions before pruning.

    **Important**: The assistant message is PRESERVED with its thinking/reasoning content.
    Only the tool_calls are removed from the message. This avoids redundancy since work
    summaries are stored in the plan status block, while keeping valuable context.

    Args:
        messages: Full message history
        main_task: Main task ID (e.g., "2") - optional if prune_all_completed=True
        subtasks: Optional list of subtask IDs (e.g., ["2c", "2d"])
        exclude_index: Optional index of assistant message to exclude from pruning
                      (used to avoid pruning the current message being processed)
        verbose: Print pruning statistics
        prune_all_completed: If True, prunes ALL completed status update_tasks regardless of task ID
        prune_status: If provided, only prunes update_tasks with this status (e.g., "in_progress")

    Returns:
        Pruned message list with tool calls removed but thinking preserved

    Examples:
        # When Task 1 completes, prune its in_progress calls:
        pruned = prune_completed_task_messages(messages, main_task="1", prune_status="in_progress", exclude_index=15)

        # When Task 2 starts, prune ALL completed calls:
        pruned = prune_completed_task_messages(messages, prune_all_completed=True, exclude_index=15)
    """
    # Find all update_tasks calls for this task/subtasks (excluding the current one)
    matching_indices = _find_update_tasks_calls(
        messages, main_task, subtasks, exclude_index, prune_all_completed, prune_status
    )

    if not matching_indices:
        # No matching update_tasks calls found
        return messages

    # Extract all tool_call_ids to remove
    tool_call_ids_to_remove: Set[str] = set()
    for idx in matching_indices:
        assistant_msg = messages[idx]
        ids = _get_tool_call_ids_for_task(assistant_msg, main_task, subtasks, prune_all_completed, prune_status)
        tool_call_ids_to_remove.update(ids)

    if not tool_call_ids_to_remove:
        # No tool_call_ids found
        return messages

    # Remove tool calls and responses
    pruned_messages = _remove_message_pairs(messages, list(tool_call_ids_to_remove))

    # Print stats if verbose
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

        print(f"🗑️  Pruned {len(tool_call_ids_to_remove)} tool calls + {removed_count} tool responses for {task_label}")
        print(f"   Message count: {len(messages)} → {len(pruned_messages)} (thinking preserved)")

    return pruned_messages


def _find_update_tasks_calls(
    messages: List[Dict[str, Any]],
    main_task: Optional[str],
    subtasks: Optional[List[str]] = None,
    exclude_index: Optional[int] = None,
    prune_all_completed: bool = False,
    prune_status: Optional[str] = None
) -> List[int]:
    """Find indices of update_tasks calls matching task/subtasks/status.

    Returns list of assistant message indices that contain matching update_tasks calls.

    Args:
        messages: Full message history
        main_task: Main task ID to match (optional if prune_all_completed=True)
        subtasks: Optional list of subtask IDs to match
        exclude_index: Optional index to exclude (current message being processed)
        prune_all_completed: If True, finds ALL completed status update_tasks regardless of task ID
        prune_status: If provided, only finds update_tasks with this status

    Returns:
        List of message indices containing matching update_tasks calls
    """
    matching_indices = []

    for i, msg in enumerate(messages):
        # Skip the excluded index (current message being processed)
        if exclude_index is not None and i == exclude_index:
            continue

        # Only check assistant messages with tool_calls
        if msg.get("role") != "assistant":
            continue

        tool_calls = msg.get("tool_calls", [])
        if not tool_calls:
            continue

        # Check each tool call
        for tc in tool_calls:
            # Get tool name
            tool_name = None
            if hasattr(tc, 'function') and hasattr(tc.function, 'name'):
                tool_name = tc.function.name
            elif isinstance(tc, dict) and 'function' in tc:
                tool_name = tc['function'].get('name')

            # Only interested in update_tasks
            if tool_name != "update_tasks":
                continue

            # Parse arguments
            args = parse_tool_call_arguments(tc)
            status = args.get("status", "")

            # If prune_all_completed mode, only check status
            if prune_all_completed:
                if status in ("complete", "completed"):
                    matching_indices.append(i)
                    break  # Found a completed task, move to next message
                continue

            # If prune_status specified, filter by status
            if prune_status and status != prune_status:
                continue

            # Otherwise, filter by main_task and subtasks
            args_main_task = args.get("main_task")
            args_subtasks = args.get("subtasks", [])

            # Check if main_task matches
            if main_task and args_main_task != main_task:
                continue

            # If we're looking for specific subtasks, check if any match
            if subtasks:
                # Match if any subtask overlaps with the subtasks being completed now
                # Example: Completing ["2c", "2d"] will match messages containing "2c" or "2d"
                # This allows incremental pruning as different subtasks complete
                if any(st in args_subtasks for st in subtasks):
                    matching_indices.append(i)
                    break  # Found a match in this message, move to next message
            else:
                # No specific subtasks - match on main_task only
                matching_indices.append(i)
                break  # Found a match in this message, move to next message

    return matching_indices


def _get_tool_call_ids_for_task(
    assistant_message: Dict[str, Any],
    main_task: Optional[str],
    subtasks: Optional[List[str]] = None,
    prune_all_completed: bool = False,
    prune_status: Optional[str] = None
) -> List[str]:
    """Extract tool_call_ids from assistant message that match task criteria.

    Parses tool call arguments to match main_task, subtasks, and/or status.

    Args:
        assistant_message: Assistant message dict with tool_calls
        main_task: Main task ID to match (optional if prune_all_completed=True)
        subtasks: Optional list of subtask IDs to match
        prune_all_completed: If True, extracts ALL completed status update_tasks
        prune_status: If provided, only extracts update_tasks with this status

    Returns:
        List of tool_call_ids that match the criteria
    """
    matching_ids = []

    tool_calls = assistant_message.get("tool_calls", [])
    for tc in tool_calls:
        # Get tool name
        tool_name = None
        if hasattr(tc, 'function') and hasattr(tc.function, 'name'):
            tool_name = tc.function.name
        elif isinstance(tc, dict) and 'function' in tc:
            tool_name = tc['function'].get('name')

        # Only interested in update_tasks
        if tool_name != "update_tasks":
            continue

        # Parse arguments
        args = parse_tool_call_arguments(tc)
        status = args.get("status", "")

        # If prune_all_completed mode, only check status
        if prune_all_completed:
            if status not in ("complete", "completed"):
                continue
        else:
            # If prune_status specified, filter by status
            if prune_status and status != prune_status:
                continue

            # Otherwise, filter by main_task and subtasks
            args_main_task = args.get("main_task")
            args_subtasks = args.get("subtasks", [])

            # Check if it matches
            if main_task and args_main_task != main_task:
                continue

            if subtasks:
                # Match if any subtask overlaps
                if not any(st in args_subtasks for st in subtasks):
                    continue

        # Extract tool_call_id
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
    """Remove tool calls and their responses while preserving assistant message thinking.

    For each tool_call_id:
    - Remove the matching tool_call from the assistant message's tool_calls array
    - If all tool_calls are removed, remove the tool_calls field but KEEP the message content
    - Remove the corresponding tool response messages

    **Key Behavior**: This preserves the assistant's thinking/reasoning in the content field
    while removing redundant tool calls (since work summaries are stored in plan status).

    Args:
        messages: Full message history
        tool_call_ids: List of tool_call_ids to remove

    Returns:
        Pruned message list with tool calls removed but thinking preserved
    """
    if not tool_call_ids:
        return messages

    # Build set for O(1) lookup
    tool_call_ids_set = set(tool_call_ids)

    # Track tool response indices to skip
    tool_response_indices_to_skip: Set[int] = set()

    # First pass: identify all tool responses to remove
    for i, msg in enumerate(messages):
        if msg.get("role") == "tool":
            tool_call_id = msg.get("tool_call_id")
            if tool_call_id and tool_call_id in tool_call_ids_set:
                tool_response_indices_to_skip.add(i)

    # Second pass: modify assistant messages and build pruned list
    pruned_messages = []

    for i, msg in enumerate(messages):
        # Skip tool responses we've marked for removal
        if i in tool_response_indices_to_skip:
            continue

        # Check if this is an assistant message with tool_calls
        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            tool_calls = msg.get("tool_calls", [])

            # Separate tool calls to keep vs remove
            tool_calls_to_keep = []
            for tc in tool_calls:
                tc_id = None
                if hasattr(tc, 'id'):
                    tc_id = tc.id
                elif isinstance(tc, dict) and 'id' in tc:
                    tc_id = tc['id']

                # Keep tool call if it's not in our removal set
                if not (tc_id and tc_id in tool_call_ids_set):
                    tool_calls_to_keep.append(tc)

            # If we removed some tool calls, create modified message
            if len(tool_calls_to_keep) < len(tool_calls):
                # Create a shallow copy to avoid mutating original
                modified_msg = {
                    "role": msg["role"],
                    "content": msg.get("content", "")
                }

                # Only include tool_calls if there are remaining ones
                if tool_calls_to_keep:
                    modified_msg["tool_calls"] = tool_calls_to_keep

                # Always keep the message (even if tool_calls is now empty)
                # The content field contains valuable thinking/reasoning
                pruned_messages.append(modified_msg)
            else:
                # No tool calls were removed, keep message as-is
                pruned_messages.append(msg)
        else:
            # Keep all other messages as-is
            pruned_messages.append(msg)

    return pruned_messages
