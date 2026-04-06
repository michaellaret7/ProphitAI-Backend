"""Update Plan Tool - Mark orchestrator plan tasks as complete."""

from typing import Any

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import success_response, error_response
from prophitai_atlas.models.new_plan import Plan, TaskStatus


# ================================
# --> Tools
# ================================

@agent_tool(name="update_plan")
def update_plan(_plan: Plan, _chat_callback: Any, task_id: str) -> str:
    """Mark a plan task as complete after you have finished it.
Call this after completing a task — whether you executed it yourself
with direct tool calls or delegated it to a worker agent.

    Args:
        task_id: The task ID to mark as complete (e.g., '1', '2', '3')

    Examples:
        update_plan(task_id='1')  # after completing task 1
    """
    if not _plan or not _plan.tasks:
        return error_response("No plan available to update")

    task = next((t for t in _plan.tasks if t.id == task_id), None)
    if not task:
        available = [t.id for t in _plan.tasks]
        return error_response(f"Task '{task_id}' not found. Available: {available}")

    if task.status == TaskStatus.COMPLETE:
        return error_response(f"Task {task_id} is already complete.")

    task.status = TaskStatus.COMPLETE

    # Notify frontend of the plan state change
    if _chat_callback and hasattr(_chat_callback, "on_plan_updated"):
        _chat_callback.on_plan_updated(_plan)

    completed = sum(1 for t in _plan.tasks if t.status == TaskStatus.COMPLETE)
    total = len(_plan.tasks)
    remaining = [
        f"  {t.id}. {t.description}"
        for t in _plan.tasks if t.status != TaskStatus.COMPLETE
    ]

    summary = f"Task {task_id} marked complete. Progress: {completed}/{total}."
    if remaining:
        summary += f"\n\nRemaining tasks:\n" + "\n".join(remaining)
    else:
        summary += "\n\nAll tasks complete — synthesize your final answer now."

    return success_response({"message": summary})


# Reason: `function` is intentionally omitted — it must be bound via
# functools.partial(update_plan, plan, chat_callback) at registration time.
UPDATE_PLAN_TOOL = {k: v for k, v in update_plan.tool.items() if k != "function"}
