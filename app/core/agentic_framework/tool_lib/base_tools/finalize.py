from typing import Optional
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response


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

            return error_response(error_msg)

    return success_response({
        "answer": (answer or "").strip(),
        "meta": meta or {},
    })


FINALIZE_DESCRIPTION = (
    "CRITICAL: This is the ONLY tool to use when you are DONE and ready to deliver the final answer. "
    "Calling this tool TERMINATES the run. Do not summarize or continue planning afterwards.\n\n"
    "⚠️  BEFORE CALLING THIS TOOL - VALIDATION REQUIRED:\n"
    "1. If you created a plan, verify EVERY task has status='complete'\n"
    "2. Verify EVERY subtask has status='complete' - do not skip this check\n"
    "3. If any task/subtask is still 'in progress', call update_tasks() to complete it first\n"
    "4. Do NOT call this tool if you have incomplete work - it will reject your attempt\n\n"
    "This tool validates your plan state. If any tasks are incomplete, you will receive an error "
    "message and must complete them before trying again.\n\n"
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


