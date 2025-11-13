"""Execution utilities for the ExecutionLoop.

Contains helper functions for:
- Final answer extraction
- Plan context building
"""

from typing import TYPE_CHECKING
from app.core.agentic_framework.base_agent.utils.models import TaskStatus
from app.core.agentic_framework.base_agent.logging.task_state_logger import format_plan_state

if TYPE_CHECKING:
    from ..agent import BaseAgent


def are_all_tasks_complete(plan) -> bool:
    """Check if ALL tasks and subtasks are complete.

    Args:
        plan: The Plan object containing tasks and subtasks

    Returns:
        True only if every task and every subtask has status=COMPLETE
    """
    if not plan or not plan.tasks:
        return False

    for task in plan.tasks:
        # Check main task status
        if task.status != TaskStatus.COMPLETE:
            return False

        # Check all subtasks if they exist
        if task.subtasks:
            for subtask in task.subtasks:
                if subtask.status != TaskStatus.COMPLETE:
                    return False

    return True


def extract_final_answer(text: str) -> str:
    """Extract final answer text after marker.

    Args:
        text: Full assistant response

    Returns:
        Text after "Final Answer:" marker
    """
    text = text.strip()
    lower_text = text.lower()
    final_idx = lower_text.find("final answer:")

    if final_idx >= 0:
        return text[final_idx + 13:].strip()

    return text


def build_plan_context(agent: 'BaseAgent', is_first_execution: bool = False) -> str:
    """Build a plan context message to inject into the conversation.

    Args:
        agent: The BaseAgent instance with plan and tasks
        is_first_execution: Whether this is the first execution iteration (after planning)

    Returns:
        Formatted string with current plan status including all subtasks
    """
    if not agent.plan or not agent.plan.tasks:
        return ""

    # Count overall progress
    total_tasks = len(agent.plan.tasks)
    completed_tasks = sum(1 for t in agent.plan.tasks if t.status == TaskStatus.COMPLETE)

    context = "## Current Plan Status\n\n"
    context += f"Progress: {completed_tasks}/{total_tasks} main tasks completed\n\n"

    # Check if ALL tasks AND subtasks are complete - if so, prompt for final answer
    # CRITICAL: Must check both main tasks and all subtasks to prevent premature finalization
    all_tasks_complete = are_all_tasks_complete(agent.plan)

    if all_tasks_complete:
        context += "**ALL TASKS COMPLETE**\n\n"
        context += "You have completed all planned tasks. Now you MUST provide your final answer.\n\n"
        context += "**REQUIRED ACTION:** Provide a comprehensive final answer by starting your response with 'Final Answer:' followed by your complete analysis and recommendations.\n\n"
        context += "Example format:\n"
        context += "Final Answer:\n"
        context += "[Your comprehensive analysis here...]\n\n"
        return context  # Early return - no need to show task lists when done

    # Use the same formatting as task_state.yaml - keep tasks in order with work summaries
    formatted_tasks = format_plan_state(agent.plan)
    context += formatted_tasks
    context += "\n"


    context += "\n## 🎯 EXECUTION WORKFLOW\n\n"
    context += "**The following is how an iteration should look for this workflow:**\n\n"
    context += "1. Brief 'Thinking:' (1-3 sentences: what and why)\n"
    context += "2. Identify current task/subtask and mark in progress (use update_tasks)\n"
    context += "3. Complete the work item (use tools if needed)\n"
    context += "4. Analyze tool result (1-3 sentences: findings → implication → next step)\n"
    context += "5. Mark subtask complete with evidence (use update_tasks)\n"
    context += "6. Continue to the next subtask or main task\n"
    context += "7. Before finalizing: Verify ALL tasks/subtasks are marked complete\n"
    context += "8. If any task is 'in progress', complete it first using update_tasks()\n"
    context += "9. Only call finalize() after every task shows status='complete'\n"
    context += "10. Provide your final answer using the finalize tool\n\n"
    context += "**⚠️ CRITICAL RULES [If you break any of these rules, you will be penalized harshly]:**\n\n"
    context += "- You are NOT allowed to mark a main task as complete until ALL subtasks are complete\n"
    context += "- You MUST mark the task/subtask as in progress BEFORE you start working on it\n"
    context += "- You may ONLY mark tasks as complete AFTER you have actually done the work\n"
    context += "- **COMPLETE SUBTASKS ONE AT A TIME**: When you finish a subtask, mark it status='complete' immediately. DO NOT batch multiple subtasks with status='in_progress' and say 'Completed 2a, 2b, 2c' in work_summary. Each subtask gets its own complete call.\n"
    context += "- **NEVER CALL FINALIZE WITH INCOMPLETE TASKS**: Before calling finalize(), verify EVERY task and subtask is marked 'complete'. If any work remains, complete it first with update_tasks().\n"
    context += "- You MUST always think out loud and provide your reasoning for the actions you take\n"
    context += "- You must NEVER leave the content field blank when calling update_tasks\n\n"
    context += "**Examples:**\n"
    context += "✅ CORRECT: update_tasks(main_task='2', subtasks=['2a'], status='complete', work_summary='Analyzed data using tool X...')\n"
    context += "❌ WRONG: update_tasks(main_task='2', subtasks=['2a','2b','2c'], status='in_progress', work_summary='Completed all subtasks')\n\n"
    context += "You are never allowed to skip any main or sub tasks under any circumstances! Violating this rule will result in severe consequences.\n"


    return context
