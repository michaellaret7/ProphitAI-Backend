"""Execution utilities for the ExecutionLoop.

Contains helper functions for:
- Final answer extraction
- Plan context building
"""

from typing import TYPE_CHECKING
from app.core.agentic_framework.base_agent_v2.utils.models import TaskStatus
from app.core.agentic_framework.base_agent_v2.logging.task_state_logger import format_plan_state

if TYPE_CHECKING:
    from ..agent import BaseAgent

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

    # Check if ALL tasks are complete - if so, prompt for final answer
    all_tasks_complete = (completed_tasks == total_tasks)

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
    context += "7. Before finalizing: Reflect (2-4 sentences), then provide the Final Answer\n\n"
    context += "**⚠️ CRITICAL RULES [If you break any of these rules, you will be penalized harshly]:**\n\n"
    context += "- You are NOT allowed to mark a main task as complete until ALL subtasks are complete\n"
    context += "- You MUST mark the task/subtask as in progress BEFORE you start working on it\n"
    context += "- You may ONLY mark tasks as complete AFTER you have actually done the work\n"
    context += "- You MUST always think out loud and provide your reasoning for the actions you take\n"
    context += "- You must NEVER leave the content field blank when calling update_tasks\n\n"
    context += "**Example:** update_tasks(main_task='2', subtasks=['2b'], status='in_progress', content='Starting work on data collection')\n"
    context += "You are never allowed to skip any main or sub tasks under any circumstances! Violating this rule will result in severe consequences.\n"


    return context
