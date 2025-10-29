"""Tool validation utilities."""

from typing import TYPE_CHECKING
import yaml
from app.core.agentic_framework.base_agent_v2.utils.models import TaskStatus

if TYPE_CHECKING:
    from ..agent import BaseAgent

str = """
success: true
data:
    portfolio_value: 1000000
    positions: 5
"""

def validate_tool_call(name: str, args: dict, result: str, agent: 'BaseAgent') -> None:
    """Validate tool execution success and display in-progress tasks.

    Args:
        result: YAML-formatted tool result string
        agent: Agent instance containing plan and tasks

    Example tool result from LLM:
        ```yaml
        success: true
        message: "Task completed successfully"
        data:
          portfolio_value: 1000000
          positions: 5
        ```
    """
    try:
        tool_payload = yaml.safe_load(result)
        success = tool_payload.get("success", False)
        data = tool_payload.get("data", {})
        error = tool_payload.get("error") if not success else None

        main_tasks_in_progress = []
        subtasks_in_progress = []

        if hasattr(agent, 'plan') and agent.plan:
            for task in agent.plan.tasks:
                # Check main task
                if task.status == TaskStatus.IN_PROGRESS:
                    main_tasks_in_progress.append(f"Task {task.id}: {task.description}")

                # Check subtasks
                for subtask in task.subtasks:
                    if subtask.status == TaskStatus.IN_PROGRESS:
                        subtasks_in_progress.append(f"Subtask {subtask.id}: {subtask.description}")

        return yaml.dump({
            "success": success,
            "tool_name": name,
            "args": args,
            "main_tasks_in_progress": main_tasks_in_progress,
            "subtasks_in_progress": subtasks_in_progress,
            "data": data,
            "error": error,
        }, default_flow_style=False, sort_keys=False)

    except Exception as e:
        print(f"⚠️ Error validating tool result: {e}")
        return yaml.dump({
            "success": False,
            "error": f"Tool validation failed: {str(e)}",
            "tool_name": name,
            "args": args,
            "main_tasks_in_progress": [],
            "subtasks_in_progress": []
        }, default_flow_style=False, sort_keys=False)

