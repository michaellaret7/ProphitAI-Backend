from typing import Optional
import yaml


def finalize(answer: str, *, plan=None, meta: Optional[dict] = None) -> str:
    """Return a structured payload containing the final answer.

    The execution loop will treat a call to this tool as a termination signal.

    Args:
        answer: The final answer to return
        plan: The agent's plan object (for validation)
        meta: Optional metadata
    """
    # WORKFLOW ENFORCEMENT: Validate all tasks are complete before finalizing
    if plan and plan.tasks:
        from app.core.agentic_framework.base_agent.utils.models import TaskStatus

        incomplete_main_tasks = [t for t in plan.tasks if t.status != TaskStatus.COMPLETE]

        if incomplete_main_tasks:
            incomplete_summary = []
            for task in incomplete_main_tasks:
                # Check for incomplete subtasks
                if task.subtasks:
                    incomplete_subtasks = [st.id for st in task.subtasks
                                          if st.status != TaskStatus.COMPLETE]
                    in_progress_subtasks = [st.id for st in task.subtasks
                                           if st.status == TaskStatus.IN_PROGRESS]

                    if incomplete_subtasks:
                        status_detail = f"status: {task.status.value}"
                        if in_progress_subtasks:
                            status_detail += f" (subtasks in progress: {in_progress_subtasks})"

                        incomplete_summary.append(
                            f"  • Task {task.id}: {task.description}\n"
                            f"    {status_detail}\n"
                            f"    Incomplete subtasks: {incomplete_subtasks}"
                        )
                else:
                    # Main task without subtasks
                    incomplete_summary.append(
                        f"  • Task {task.id}: {task.description}\n"
                        f"    Status: {task.status.value}"
                    )

            error_msg = (
                "🚫 CANNOT FINALIZE: Your plan has incomplete tasks.\n\n"
                "Incomplete tasks:\n" + "\n".join(incomplete_summary) + "\n\n"
                "⚠️  You must complete ALL tasks before finalizing.\n\n"
                "If you already did the work but didn't mark tasks complete:\n"
                "  → Call update_tasks() with status='complete' and work_summary for each task\n\n"
                "If you haven't finished the work:\n"
                "  → Complete the remaining tasks, then mark them complete\n\n"
                "Remember: The plan is your contract. You cannot finalize until all tasks "
                "are properly tracked and marked complete."
            )

            return yaml.dump({
                "success": False,
                "error": error_msg
            }, default_flow_style=False)

    payload = {
        "success": True,
        "data": {
            "answer": (answer or "").strip(),
            "meta": meta or {},
        },
    }
    return yaml.dump(payload, default_flow_style=False, sort_keys=False)


FINALIZE_DESCRIPTION = (
    "CRITICAL: This is the ONLY tool to use when you are DONE and ready to deliver the final answer. "
    "Calling this tool TERMINATES the run. Do not summarize or continue planning afterwards. "
    "Provide the COMPLETE final answer as a single string in the 'answer' field."
)

FINALIZE_PARAMETERS = {
    "type": "object",
    "properties": {
        "answer": {
            "type": "string",
            "description": "The complete final answer to return to the user.",
        },
        "meta": {
            "type": "object",
            "description": "Optional metadata to include with the final answer (e.g., scores).",
            "additionalProperties": True,
        },
    },
    "required": ["answer"],
}


