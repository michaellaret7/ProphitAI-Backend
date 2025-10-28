"""Tool validation utilities."""

from typing import TYPE_CHECKING
import yaml
from app.core.agentic_framework.base_agent_v2.utils.models import TaskStatus

if TYPE_CHECKING:
    from ..agent import SimpleAgent

str = """
success: true
message: "Task completed successfully"
data:
    portfolio_value: 1000000
    positions: 5
"""

def check_tool_success(result: str, agent: 'SimpleAgent') -> None:
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

        print("+" * 150)
        print(success)

        in_progress_items = []

        if hasattr(agent, 'plan') and agent.plan:
            for task in agent.plan.tasks:
                # Check main task
                if task.status == TaskStatus.IN_PROGRESS:
                    in_progress_items.append(f"Task {task.id}: {task.description}")

                # Check subtasks
                for subtask in task.subtasks:
                    if subtask.status == TaskStatus.IN_PROGRESS:
                        in_progress_items.append(f"Subtask {subtask.id}: {subtask.description}")

        print(in_progress_items)
        print("-" * 150)

    except Exception as e:
        print(f"⚠️ Error validating tool result: {e}")

if __name__ == "__main__":
    check_tool_success(str, None)