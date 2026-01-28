"""Execution loop reminder messages."""


THINK_DEEPLY_MESSAGE = (
    "## THINK DEEPLY AND REFLECT THIS ITERATION\n\n"
    "Before acting, engage in RIGOROUS thinking. Follow your PER-TURN OUTPUT SCHEMA.\n\n"
    "**If tool results exist above, analyze them deeply:**\n"
    "- What are the specific numbers/metrics? What do they MEAN in context?\n"
    "- What patterns, anomalies, or insights emerge from this data?\n"
    "- How does this integrate with previous findings? Does it confirm or contradict earlier hypotheses?\n"
    "- What are the limitations, caveats, or gaps in this data?\n"
    "- What is the CUMULATIVE picture emerging from all findings so far?\n\n"
    "**Then plan your next action strategically:**\n"
    "- What specific question am I answering? How does this advance my goal?\n"
    "- What alternatives exist? Why is my chosen approach superior?\n"
    "- If calling tools: which tools, what parameters, and WHY these specific choices?\n"
    "- What do I expect to learn? How will I use this information?\n\n"
    "**Self-Critique & Quality Check:**\n"
    "- Am I on the right track? Do I need to edit the plan (using edit_plan)?\n"
    "- How am I doing? Am I calling the right tools?\n"
    "- Am I thinking and reasoning enough?\n"
    "- Am I being thorough enough? Any unjustified assumptions? Overlooked angles?\n\n"
    "- Am I writing enough notes? Are my notes comprehensive and detailed?\n"
    "- Am I using the retrieve_notes tool enough? Are my notes being retrieved at the right time and frequency?\n"
    "**Plan Management:**\n"
    "- Are all of my tasks that I have finished marked as complete?\n"
    "- Are all of my subtasks that I have finished marked as complete?\n"
    "Be COMPREHENSIVE in analysis, STRATEGIC in planning, and RIGOROUS in self-evaluation.\n"
    "Depth and precision over speed. Think like an expert analyst, not a task-completion robot.\n"
)


def get_finalize_rejected_message(progress: str) -> str:
    """Generate finalize rejected message with remaining tasks.

    Args:
        progress: String showing the remaining incomplete tasks

    Returns:
        Formatted rejection message
    """
    return (
        "## FINALIZE REJECTED - INCOMPLETE TASKS DETECTED\n\n"
        "You attempted to call the finalize tool but your plan has INCOMPLETE TASKS.\n"
        "This is NOT allowed. You MUST complete ALL tasks before finalizing.\n\n"
        f"**Remaining Tasks:**\n{progress}\n\n"
        "**REQUIRED ACTIONS - YOU MUST DO ONE OF THE FOLLOWING:**\n\n"
        "**OPTION 1:** If you already completed the work but forgot to update task status:\n"
        "- Call update_tasks() with status='complete' and work_summary for EACH task\n\n"
        "**OPTION 2:** If you have NOT completed the work:\n"
        "- Execute the remaining tasks NOW\n"
        "- Mark each task complete with update_tasks() after finishing\n"
        "- THEN call finalize\n\n"
        "**PROHIBITED ACTIONS:**\n"
        "- DO NOT call finalize again until ALL tasks show status='complete'\n"
        "- DO NOT skip tasks or mark them complete without doing the work\n"
        "- DO NOT attempt to bypass this check - it will be rejected every time\n"
    )
