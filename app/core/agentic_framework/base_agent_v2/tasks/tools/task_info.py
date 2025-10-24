"""Task info tool - allows agent to see current task context.

This tool gives the agent awareness of where they are in the plan.
"""

from typing import Dict, Any
import yaml


def get_current_task_info(task_tracker) -> str:
    """
    Tool for agent to see current task/subtask context.

    Agent can call this anytime to understand where they are in the plan.

    Args:
        task_tracker: LightweightTaskTracker instance

    Returns:
        YAML string with current task context
    """
    context = task_tracker.get_current_context()
    return yaml.dump(context, default_flow_style=False, sort_keys=False)


# Tool schema for LLM function calling
GET_CURRENT_TASK_INFO_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_current_task_info",
        "description": (
            "Get information about your current task and subtask in the plan. "
            "Use this to understand where you are, what you're working on, and what's next. "
            "Returns current task, current subtask, progress percentage, and next task/subtask."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}