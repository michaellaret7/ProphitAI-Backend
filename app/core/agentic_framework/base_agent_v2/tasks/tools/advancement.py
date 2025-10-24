"""Task advancement tools - allows agent to control task progression.

These tools give the agent control over when to advance tasks/subtasks.
NO automatic advancement - agent must explicitly call these.
"""

from typing import Dict, Any
import yaml


def advance_to_next_subtask(
    task_tracker,
    completion_reasoning: str,
    key_findings: str
) -> str:
    """
    Tool for agent to advance to next subtask.

    Agent MUST call this explicitly when ready to move forward.
    System will NEVER automatically advance - agent is in control.

    Args:
        task_tracker: LightweightTaskTracker instance
        completion_reasoning: Explain why current subtask is complete
        key_findings: Main insights from this subtask

    Returns:
        YAML string with advancement result
    """
    result = task_tracker.advance_subtask(
        completion_reasoning=completion_reasoning,
        key_findings=key_findings
    )
    return yaml.dump(result, default_flow_style=False, sort_keys=False)


def advance_to_next_main_task(
    task_tracker,
    completion_reasoning: str,
    key_findings: str
) -> str:
    """
    Tool for agent to advance to next main task.

    Agent MUST call this explicitly when ready to move forward.
    System will NEVER automatically advance - agent is in control.

    NOTE: All subtasks must be complete before you can advance a main task.
    If subtasks are incomplete, this will return an error.

    Args:
        task_tracker: LightweightTaskTracker instance
        completion_reasoning: Explain why entire task is complete
        key_findings: Main insights and discoveries from this task

    Returns:
        YAML string with advancement result
    """
    result = task_tracker.advance_main_task(
        completion_reasoning=completion_reasoning,
        key_findings=key_findings
    )
    return yaml.dump(result, default_flow_style=False, sort_keys=False)


# Tool schemas for LLM function calling

ADVANCE_SUBTASK_SCHEMA = {
    "type": "function",
    "function": {
        "name": "advance_to_next_subtask",
        "description": (
            "Advance to the next subtask when current one is complete. "
            "You MUST call this to progress through subtasks - the system will NOT automatically advance. "
            "Provide your reasoning for why the subtask is complete and the key findings you discovered."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "completion_reasoning": {
                    "type": "string",
                    "description": "Explain why you believe the current subtask is complete and you're ready to move to the next one"
                },
                "key_findings": {
                    "type": "string",
                    "description": "Summarize the main insights, findings, or discoveries from this subtask"
                }
            },
            "required": ["completion_reasoning", "key_findings"]
        }
    }
}

ADVANCE_MAIN_TASK_SCHEMA = {
    "type": "function",
    "function": {
        "name": "advance_to_next_main_task",
        "description": (
            "Advance to the next main task when current one is complete. "
            "You MUST call this to progress through main tasks - the system will NOT automatically advance. "
            "NOTE: All subtasks must be completed before you can advance a main task. "
            "Provide your reasoning for completion and summarize the key findings from the entire task."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "completion_reasoning": {
                    "type": "string",
                    "description": "Explain why you believe the current task is complete and you're ready to move to the next one"
                },
                "key_findings": {
                    "type": "string",
                    "description": "Summarize the main insights, findings, or discoveries from this entire task (across all subtasks)"
                }
            },
            "required": ["completion_reasoning", "key_findings"]
        }
    }
}