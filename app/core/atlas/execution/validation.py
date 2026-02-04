"""Tool validation utilities."""

from typing import Any
import yaml

from app.core.atlas.models import TaskStatus
from app.core.atlas.tools.responses import dump_yaml


def validate_tool_call(name: str, args: dict, result: Any, agent: Any) -> str:
    """Validate tool execution success and display in-progress tasks."""
    try:
        if isinstance(result, dict):
            tool_payload = result
        else:
            tool_payload = yaml.safe_load(result)

        success = tool_payload.get("success", False)
        data = tool_payload.get("data", {})
        error = tool_payload.get("error") if not success else None

        main_tasks_in_progress = []
        subtasks_in_progress = []

        if hasattr(agent, 'plan') and agent.plan:
            for task in agent.plan.tasks:
                if task.status == TaskStatus.IN_PROGRESS:
                    main_tasks_in_progress.append(f"Task {task.id}: {task.description}")

                for subtask in task.subtasks:
                    if subtask.status == TaskStatus.IN_PROGRESS:
                        subtasks_in_progress.append(f"Subtask {subtask.id}: {subtask.description}")

        return dump_yaml({
            "success": success,
            "tool_name": name,
            "args": args,
            "main_tasks_in_progress": main_tasks_in_progress,
            "subtasks_in_progress": subtasks_in_progress,
            "data": data,
            "error": error,
        })

    except Exception as e:
        print(f"Warning: Error validating tool result: {e}")
        return dump_yaml({
            "success": False,
            "error": f"Tool validation failed: {str(e)}",
            "tool_name": name,
            "args": args,
            "main_tasks_in_progress": [],
            "subtasks_in_progress": []
        })
