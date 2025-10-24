"""Reasoning prompts builder for Base Agent V2.

Builds prompts that encourage the Think → Act → Observe → Reason cycle.
"""

from typing import Dict, Any, List


class ReasoningPrompter:
    """Builds prompts to encourage Think → Act → Observe → Reason cycle at each phase."""

    def build_thinking_prompt(self, task_description: str) -> str:
        """
        Prompt agent to think before acting.

        Encourages pre-action planning and approach formulation.

        Args:
            task_description: Description of current task/subtask

        Returns:
            Prompt string encouraging agent to think out loud
        """
        return f"""
Plan your approach for the current objective:

CURRENT OBJECTIVE: {task_description}

PLANNING:
- What specific aspects need to be analyzed?
- What data or metrics do you need?
- Which tools will you use and in what order?
- What's your strategy for accomplishing this?

Then execute your plan immediately.
"""

    def build_observation_prompt(self, tool_results_summary: str, num_tools_called: int) -> str:
        """
        Prompt agent to observe and summarize findings after tool calls.

        Encourages agent to step back and make sense of the data before reasoning.

        Args:
            tool_results_summary: Formatted summary of recent tool results
            num_tools_called: Number of tools that were just called

        Returns:
            Prompt string encouraging agent to observe findings
        """
        return f"""
You executed {num_tools_called} tool call(s). Summarize what you found:

{tool_results_summary}

OBSERVE:
- What did the data show? (factual summary)
- What patterns or key metrics stand out?
- Any surprises or anomalies?

Keep it concise. Then decide your next action.
"""

    def build_reasoning_prompt(self, has_observations: bool = False) -> str:
        """
        Prompt agent to reason about what to do next.

        Encourages synthesis, decision-making, and planning next steps.

        Args:
            has_observations: Whether agent has made observations (affects prompt)

        Returns:
            Prompt string encouraging agent to reason
        """
        if has_observations:
            base = "Based on your observations, decide your next action:"
        else:
            base = "Decide your next action:"

        return f"""
{base}

ANALYSIS:
- What do these findings mean for your analysis?
- What insights can you draw from the data patterns?
- Does this give you enough information to complete the current objective?

DECISION - Choose ONE:
1. If objective is complete → Use advance_to_next_subtask tool NOW
2. If you need specific data → Execute tools to get it NOW
3. If ready for final answer → Provide Final Answer NOW

DO NOT ask questions. DO NOT wait for approval. DECIDE and ACT.
"""

    def build_task_context_prompt(self, task_context: Dict[str, Any]) -> str:
        """
        Build prompt showing current task context.

        Shows agent where they are in the plan.

        Args:
            task_context: Dict from tracker.get_current_context()

        Returns:
            Formatted prompt with task context
        """
        if task_context.get("status") == "completed":
            return f"""
PLAN STATUS: All tasks completed!

{task_context.get('message', '')}

Progress: {task_context.get('overall_progress', {}).get('percentage', 100)}%

You have completed all tasks in your plan. Provide your Final Answer now.
"""

        main_task = task_context.get("current_main_task", {})
        subtask = task_context.get("current_subtask")
        progress = task_context.get("overall_progress", {})

        prompt = f"""
CURRENT TASK CONTEXT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Main Task {main_task.get('id')}: {main_task.get('description')}
  Status: {main_task.get('status')}
  Has subtasks: {main_task.get('has_subtasks', False)}
"""

        if subtask:
            prompt += f"""
Current Subtask: {subtask.get('id')} - {subtask.get('description')}
  Completed: {subtask.get('completed', False)}
"""

            # Show next subtask if exists
            next_subtask = task_context.get('next_subtask')
            if next_subtask:
                prompt += f"""
Next Subtask: {next_subtask.get('id')} - {next_subtask.get('description')}
"""

        # Show next main task if exists
        next_main_task = task_context.get('next_main_task')
        if next_main_task:
            prompt += f"""
Next Main Task: {next_main_task.get('id')} - {next_main_task.get('description')}
"""

        prompt += f"""
Overall Progress: {progress.get('main_tasks_completed', 0)}/{progress.get('main_tasks_total', 0)} main tasks completed ({progress.get('percentage', 0)}%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You are AUTONOMOUS. Make decisions and take action. Do NOT ask questions or wait for approval.
"""

        return prompt

    def build_advancement_reminder_prompt(self, task_type: str = "subtask") -> str:
        """
        Remind agent to advance when they seem done.

        Args:
            task_type: "subtask" or "main_task"

        Returns:
            Reminder prompt
        """
        if task_type == "subtask":
            return """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPORTANT: YOU control task progression.

When you have enough information to complete the current subtask:
→ Call advance_to_next_subtask tool IMMEDIATELY

Arguments:
  completion_reasoning: Brief reason why subtask is done
  key_findings: What you learned

DO NOT ask for permission. DO NOT wait. ADVANCE when ready.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:  # main_task
            return """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPORTANT: YOU control task progression.

When all subtasks are complete for the current main task:
→ Call advance_to_next_main_task tool IMMEDIATELY

Arguments:
  completion_reasoning: Brief reason why task is done
  key_findings: Main discoveries from this task

DO NOT ask for permission. DO NOT wait. ADVANCE when ready.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    def build_comprehensive_iteration_prompt(
        self,
        task_context: Dict[str, Any],
        phase: str = "working",
        recent_tool_results: List[Dict] = None
    ) -> str:
        """
        Build a comprehensive prompt for an iteration based on current phase.

        Args:
            task_context: Current task context from tracker
            phase: Current phase - "starting", "post_tools", "working"
            recent_tool_results: Recent tool results (if phase="post_tools")

        Returns:
            Complete prompt for this iteration
        """
        # Always start with task context
        prompt = self.build_task_context_prompt(task_context)

        # Add phase-specific prompts
        if phase == "starting":
            # Just started new task/subtask - encourage thinking
            current_desc = (
                task_context.get('current_subtask', {}).get('description')
                if task_context.get('current_subtask')
                else task_context.get('current_main_task', {}).get('description')
            )
            prompt += "\n" + self.build_thinking_prompt(current_desc)

        elif phase == "post_tools" and recent_tool_results:
            # Just executed tools - encourage observation
            num_tools = len(recent_tool_results)
            # Tool results summary will be formatted elsewhere
            tool_summary = f"[{num_tools} tool results - see above]"
            prompt += "\n" + self.build_observation_prompt(tool_summary, num_tools)

        elif phase == "post_observation":
            # Just made observations - encourage reasoning
            prompt += "\n" + self.build_reasoning_prompt(has_observations=True)

        else:
            # General working phase
            prompt += "\nContinue working on your current objective systematically."

        return prompt