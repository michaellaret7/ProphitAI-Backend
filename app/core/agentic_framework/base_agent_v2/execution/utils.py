"""Execution utilities for the ExecutionLoop.

Contains helper functions for:
- Finality detection
- Final answer extraction
- Plan context building
- Message history persistence
"""

from typing import TYPE_CHECKING
from pathlib import Path
from app.core.agentic_framework.base_agent_v2.utils.models import TaskStatus

if TYPE_CHECKING:
    from ..agent import SimpleAgent


def is_final(text: str) -> bool:
    """Check if text contains finality marker.

    Args:
        text: Assistant response text

    Returns:
        True if text indicates final answer
    """
    if not text:
        return False
    text_lower = text.strip().lower()
    return text_lower.startswith("final answer:") or "final answer:" in text_lower


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


def build_plan_context(agent: 'SimpleAgent') -> str:
    """Build a plan context message to inject into the conversation.

    Args:
        agent: The SimpleAgent instance with plan and tasks

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
        context += "** ALL TASKS COMPLETE**\n\n"
        context += "You have completed all planned tasks. Now you MUST provide your final answer.\n\n"
        context += "**REQUIRED ACTION:** Provide a comprehensive final answer by starting your response with 'Final Answer:' followed by your complete analysis and recommendations.\n\n"
        context += "Example format:\n"
        context += "Final Answer:\n"
        context += "[Your comprehensive analysis here...]\n\n"
        return context  # Early return - no need to show task lists when done

    # Show all tasks grouped by status
    in_progress_tasks = [t for t in agent.plan.tasks if t.status == TaskStatus.IN_PROGRESS]
    not_started_tasks = [t for t in agent.plan.tasks if t.status == TaskStatus.NOT_STARTED]
    completed_tasks_list = [t for t in agent.plan.tasks if t.status == TaskStatus.COMPLETE]

    if in_progress_tasks:
        context += "**Currently Working On:**\n"
        for task in in_progress_tasks:
            context += f"- Task {task.id}: {task.description} [{task.status.value}]\n"
            if task.subtasks:
                for subtask in task.subtasks:
                    context += f"  - Subtask {subtask.id}: {subtask.description} [{subtask.status.value}]\n"
        context += "\n"

    if not_started_tasks:
        context += "**Not Yet Started:**\n"
        for task in not_started_tasks:
            context += f"- Task {task.id}: {task.description} [{task.status.value}]\n"
            if task.subtasks:
                for subtask in task.subtasks:
                    context += f"  - Subtask {subtask.id}: {subtask.description} [{subtask.status.value}]\n"
        context += "\n"

    if completed_tasks_list:
        context += "**Completed:**\n"
        for task in completed_tasks_list:
            context += f"- Task {task.id}: {task.description} [{task.status.value}]\n"
            if task.subtasks:
                for subtask in task.subtasks:
                    context += f"  - Subtask {subtask.id}: {subtask.description} [{subtask.status.value}]\n"
        context += "\n"

    # Add workflow instructions
    context += "\n**Workflow for this iteration:**\n"
    context += "1. Identify the next task/subtask to work on\n"
    context += "2. Use tools to complete the work for that task/subtask\n"
    context += "3. After completing the work, mark the task/subtask as 'complete' using the update_tasks tool\n"
    context += "4. Move to the next task/subtask\n\n"
    context += "**Example:** update_tasks(main_task='2', subtasks=['2b'], status='complete')\n\n"
    context += "**Note:** Only mark tasks as complete AFTER you have actually done the work."

    return context


def write_messages_to_file(agent: 'SimpleAgent') -> None:
    """Write complete message history to markdown file after execution.

    Args:
        agent: The SimpleAgent instance with messages to persist
    """
    try:
        # Get path to base_agent_v2 directory
        base_agent_v2_dir = Path(__file__).parent.parent
        output_file = base_agent_v2_dir / "l.md"

        # Build markdown content
        content = "# Agent Message History\n\n"
        content += f"Total Messages: {len(agent.messages)}\n\n"
        content += "---\n\n"

        for idx, message in enumerate(agent.messages, 1):
            role = message.get("role", "unknown")
            content += f"## Message {idx} - Role: {role}\n\n"

            # Handle content
            if message.get("content"):
                content += f"**Content:**\n```\n{message['content']}\n```\n\n"

            # Handle tool calls
            if message.get("tool_calls"):
                content += "**Tool Calls:**\n"
                for tool_call in message["tool_calls"]:
                    tool_name = tool_call.function.name
                    tool_args = tool_call.function.arguments
                    content += f"- Tool: `{tool_name}`\n"
                    content += f"  - ID: `{tool_call.id}`\n"
                    content += f"  - Arguments:\n```json\n{tool_args}\n```\n\n"

            # Handle tool call ID (for tool response messages)
            if message.get("tool_call_id"):
                content += f"**Tool Call ID:** `{message['tool_call_id']}`\n\n"

            content += "---\n\n"

        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"\n=� Message history written to: {output_file}")

    except Exception as e:
        print(f"\n� Failed to write message history: {e}")
