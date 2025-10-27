"""Context and prompt building for agent iterations.

This module provides the ContextBuilder class which handles all prompt
construction logic for the agent, including initial message setup,
task-aware prompts, periodic status updates, and rejection messages.
"""

from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..agent import BaseAgent


class ContextBuilder:
    """Builds prompts and context messages for agent iterations.

    This class encapsulates all prompt building logic that was previously
    scattered throughout agent.py, providing a clean separation of concerns
    for context injection and prompt generation.
    """

    def __init__(self, agent: 'BaseAgent'):
        """Initialize context builder.

        Args:
            agent: The BaseAgent instance that owns this builder
        """
        self.agent = agent

    def build_initial_messages(
        self,
        system_prompt: str,
        user_prompt: str,
        plan_first: bool,
        domain_memory: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """Build initial message list for agent execution.

        Args:
            system_prompt: System-level instructions for the agent
            user_prompt: User's query or task description
            plan_first: Whether to inject plan-first instructions
            domain_memory: Optional domain memory to inject

        Returns:
            List of message dictionaries with system and user content
        """
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self.agent.utilities.system_rules()},
        ]

        # Inject domain memories if available
        if domain_memory:
            memory_context = domain_memory.format_memories_for_prompt()
            if memory_context:
                messages.append({"role": "system", "content": memory_context})

        messages.extend([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])

        if plan_first:
            # Inject structured planning instructions
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "🎯 PLAN-DRIVEN EXECUTION MODE:\n\n"
                        "1. First, create a comprehensive structured plan using the 'create_structured_plan' tool.\n"
                        "2. This will generate a detailed TodoList with main tasks and subtasks.\n"
                        "3. Once the plan is loaded, you will ALWAYS see your current task context.\n"
                        "4. Work systematically through the plan - focus on the current task/subtask shown.\n"
                        "5. The system will automatically track your progress and advance tasks when complete.\n"
                        "6. Use task management tools (get_current_task_info, get_completion_analysis) to stay aware.\n\n"
                        "Call the 'create_structured_plan' tool now to begin systematic execution."
                    ),
                }
            )

        return messages

    def build_task_prompt(self, iteration: int) -> str:
        """Generate enhanced plan-driven task awareness prompt.

        Args:
            iteration: Current iteration number

        Returns:
            Enhanced task prompt with comprehensive context, or empty string if no plan
        """
        if not self.agent.execution_engine.plan_loaded:
            return ""

        task_context = self.agent.execution_engine.get_current_task_context()
        if task_context.get("status") != "executing":
            return ""

        # Build comprehensive task awareness prompt
        task_prompt = (
            f"\n🎯 PLAN-DRIVEN EXECUTION STATUS (Iteration {iteration}):\n"
            f"📋 Main Task {task_context['main_task']['id']}: {task_context['main_task']['description']}"
        )

        if 'subtask' in task_context:
            subtask = task_context['subtask']
            task_prompt += f"\n  → Current SubTask: {subtask['description']}"

        # Add predicted tools guidance
        predicted_tools = task_context['main_task'].get('predicted_tools', [])
        if predicted_tools:
            task_prompt += f"\n  🛠️ Expected Tools: {', '.join(predicted_tools)}"

        # Add progress visualization
        progress = task_context['progress']
        completed = progress['main_tasks_completed']
        total = progress['main_tasks_total']
        percentage = progress['percentage']
        progress_bar = "█" * (percentage // 10) + "░" * (10 - (percentage // 10))
        task_prompt += f"\n  📈 Plan Progress: [{progress_bar}] {completed}/{total} ({percentage}%)"

        # Add task-specific guidance
        if 'subtask' in task_context:
            task_prompt += (
                f"\n\n💡 Focus: Complete SubTask {task_context['subtask']['id']} systematically. "
                f"The system will automatically detect completion and advance you to the next step."
            )
        else:
            task_prompt += (
                f"\n\n💡 Focus: Work on Main Task {task_context['main_task']['id']} systematically. "
                f"Use the expected tools to make measurable progress."
            )

        return task_prompt

    def build_plan_context(self, iteration: int) -> str:
        """Build periodic plan status update for task awareness.

        Args:
            iteration: Current iteration number

        Returns:
            Plan status update message, or empty string if not applicable
        """
        if not self.agent.execution_engine.plan_loaded:
            return ""

        task_context = self.agent.execution_engine.get_current_task_context()
        if task_context.get("status") != "executing":
            return ""

        plan_prompt = (
            f"📋 PLAN STATUS UPDATE (Iteration {iteration}):\n"
            f"Current Task: {task_context['main_task']['description']}"
        )

        if 'subtask' in task_context:
            plan_prompt += f"\nCurrent SubTask: {task_context['subtask']['description']}"

        plan_prompt += f"\nOverall Progress: {task_context['progress']['main_tasks_completed']}/{task_context['progress']['main_tasks_total']} main tasks completed"
        plan_prompt += "\n\nContinue working on your current task systematically."

        return plan_prompt

    def build_periodic_status_update(self, iteration: int) -> str:
        """Build periodic status update message.

        This is an alias for build_plan_context for API consistency.

        Args:
            iteration: Current iteration number

        Returns:
            Plan status update message
        """
        return self.build_plan_context(iteration)

    def build_rejection_message(self, completion_status: Dict[str, Any]) -> str:
        """Generate rejection message when finality is attempted prematurely.

        Args:
            completion_status: Dictionary with plan completion status

        Returns:
            Formatted rejection message explaining why final answer was rejected
        """
        if not self.agent.execution_engine.plan_loaded:
            # Fallback to old task manager approach
            incomplete = self.agent.task_manager.get_incomplete_tasks()
            reject_msg = (
                "❌ Cannot accept Final Answer yet - task list is incomplete!\n\n"
                "You must complete ALL tasks before finalizing.\n"
                "Incomplete tasks:\n"
            )
            for task in incomplete:
                status_marker = "→" if task.get("status") == "in_progress" else " "
                task_id = task.get('id', task.get('step', 'Unknown'))
                reject_msg += f"{status_marker} Task {task_id}: {task['description']} ({task.get('status', 'unknown').upper()})\n"
            reject_msg += "\nPlease continue working through your task list."
            return reject_msg

        # Build rejection message with execution engine context
        task_context = self.agent.execution_engine.get_current_task_context()
        execution_summary = self.agent.execution_engine.get_execution_summary()

        reject_msg = (
            "❌ Cannot accept Final Answer yet - structured plan is not complete!\n\n"
            f"📋 Current Status: {execution_summary.get('completed_main_tasks', 0)}/{execution_summary.get('total_main_tasks', 0)} main tasks completed\n"
        )

        if task_context.get("status") == "executing":
            reject_msg += f"▶️ Currently working on: Task {task_context['main_task']['id']}: {task_context['main_task']['description']}\n"
            if 'subtask' in task_context:
                reject_msg += f"  → SubTask: {task_context['subtask']['description']}\n"

        reject_msg += "\nPlease continue working through your structured plan before providing a Final Answer."
        return reject_msg

    def build_memory_refresh(self, iteration: int, memory_refresh_interval: int) -> Optional[str]:
        """Build domain memory refresh prompt.

        Args:
            iteration: Current iteration number
            memory_refresh_interval: How often to refresh memory

        Returns:
            Memory refresh message, or None if not applicable
        """
        if not self.agent.domain_memory:
            return None

        if memory_refresh_interval <= 0:
            return None

        if iteration <= 1 or iteration % memory_refresh_interval != 0:
            return None

        # Use concise format for refresh to avoid context bloat
        memory_refresh = self.agent.domain_memory.format_memories_for_prompt(concise=False)
        if not memory_refresh:
            return None

        refresh_msg = (
            f"📌 REMINDER - Key principles to maintain (iteration {iteration}):\n"
            f"{memory_refresh}\n"
            "Continue applying these principles in your analysis."
        )

        return refresh_msg

    def build_reasoning_checkpoint(self, checkpoint_type: str, context: Dict[str, Any] = None) -> str:
        """Build phase-specific reasoning checkpoint prompts.

        These prompts explicitly cue the agent to engage reasoning circuits
        at critical decision points during portfolio optimization.

        Args:
            checkpoint_type: Type of checkpoint (post_analytics, post_screening, refinement, etc.)
            context: Additional context for the prompt (e.g., attempt numbers)

        Returns:
            Reasoning checkpoint prompt, or empty string if checkpoint type not recognized
        """
        context = context or {}

        checkpoints = {
            "post_analytics": (
                "\n\n💭 REASONING CHECKPOINT: Analysis Complete\n"
                "═══════════════════════════════════════════\n"
                "You've gathered extensive analytical data across multiple tools.\n\n"
                "BEFORE proceeding to next phase:\n"
                "1. Use 'synthesize_observations' to connect insights across all metrics\n"
                "2. Identify the 2-3 most critical issues or opportunities\n"
                "3. Form a hypothesis about optimal strategy (use 'form_hypothesis')\n"
                "4. Let your synthesis guide the next phase—don't just execute the next subtask mechanically\n\n"
                "Remember: The goal is INSIGHT, not just completing subtasks.\n"
                "═══════════════════════════════════════════"
            ),

            "post_screening": (
                "\n\n💭 REASONING CHECKPOINT: Candidate Selection\n"
                "═══════════════════════════════════════════\n"
                "You've run stock screens and have candidate replacements.\n\n"
                "BEFORE finalizing selections:\n"
                "1. Use 'compare_alternatives' to systematically evaluate candidates\n"
                "2. Don't just pick the first N results—think strategically:\n"
                "   - How do these fit with portfolio goals?\n"
                "   - What correlations do they have with existing holdings?\n"
                "   - Do they address the weaknesses you identified?\n"
                "3. Consider portfolio-level effects, not just individual ticker metrics\n"
                "4. Justify why these SPECIFIC tickers are optimal\n\n"
                "Quality over quantity—better to have high-conviction picks than fill a quota.\n"
                "═══════════════════════════════════════════"
            ),

            "refinement_start": (
                "\n\n💭 DEEP REFINEMENT MODE ACTIVATED\n"
                "═══════════════════════════════════════════\n"
                "You now enter the most critical phase: ITERATIVE REFINEMENT.\n\n"
                "You have UP TO 3 refinement attempts. Use them wisely:\n\n"
                "REFINEMENT CYCLE:\n"
                "1. ANALYZE: Why did metrics change? Don't just observe—EXPLAIN the cause\n"
                "2. HYPOTHESIZE: Use 'form_hypothesis' to predict what adjustment would improve metrics\n"
                "3. TEST: Make the adjustment and measure impact\n"
                "4. EVALUATE: Did hypothesis validate? If not, why? What did you learn?\n"
                "5. ITERATE: Form new hypothesis based on learnings, test again\n\n"
                "STOP CONDITIONS:\n"
                "- You've exhausted improvement ideas (genuinely tried multiple approaches)\n"
                "- You're seeing diminishing returns (changes aren't improving metrics)\n"
                "- You've used all 3 attempts\n\n"
                "AVOID:\n"
                "❌ Making 1 superficial change and accepting result\n"
                "❌ Not analyzing WHY changes had their effect\n"
                "❌ Giving up after first attempt\n\n"
                "Aim for GENUINE optimization through hypothesis-driven iteration.\n"
                "═══════════════════════════════════════════"
            ),

            "refinement_iteration": (
                "\n\n💭 REFINEMENT CHECKPOINT: Attempt {attempt_num}\n"
                "═══════════════════════════════════════════\n"
                "You've completed refinement attempt {attempt_num}.\n\n"
                "Use 'reflect_on_strategy' to evaluate:\n"
                "1. What changed? Why?\n"
                "2. Did your hypothesis validate?\n"
                "3. What did you LEARN from this iteration?\n"
                "4. Should you try a different approach? Or refine current approach?\n"
                "5. What's your hypothesis for next iteration?\n\n"
                "Attempts remaining: {attempts_remaining}\n"
                "═══════════════════════════════════════════"
            ).format(
                attempt_num=context.get('attempt_num', '?'),
                attempts_remaining=context.get('attempts_remaining', '?')
            ),

            "pre_construction": (
                "\n\n💭 REASONING CHECKPOINT: Portfolio Construction\n"
                "═══════════════════════════════════════════\n"
                "You're about to construct the new portfolio.\n\n"
                "Use 'synthesize_observations' to review:\n"
                "1. What are the key weaknesses you identified?\n"
                "2. What replacements did you select and WHY?\n"
                "3. How will the new portfolio address weaknesses?\n"
                "4. What trade-offs are you making?\n\n"
                "Construct the portfolio with clear intent, not just mechanical assembly.\n"
                "═══════════════════════════════════════════"
            )
        }

        return checkpoints.get(checkpoint_type, "")

    def should_inject_checkpoint(self, iteration: int) -> Optional[str]:
        """Determine if a reasoning checkpoint should be injected.

        Checks task completion state to identify phase transitions in the
        portfolio optimization workflow.

        Args:
            iteration: Current iteration number

        Returns:
            Checkpoint type to inject (str), or None if no checkpoint needed
        """
        if not self.agent.execution_engine.plan_loaded:
            return None

        # Get current task context
        task_context = self.agent.execution_engine.get_current_task_context()
        if task_context.get("status") != "executing":
            return None

        # Get current task details
        current_main_task = task_context.get('main_task')
        if not current_main_task:
            return None

        current_task_id = current_main_task['id']
        current_task_desc = current_main_task['description'].lower()

        # Get execution summary to check recently completed tasks
        execution_summary = self.agent.execution_engine.get_execution_summary()
        completed_tasks = execution_summary.get('completed_main_tasks', 0)

        # Heuristic-based checkpoint detection
        # These heuristics are based on typical OptimizerAgent task structure
        # Adjust if your plan structure differs

        # Post-Analytics: Just completed comprehensive analytics (typically Task 2)
        # Trigger when we just finished Task 2 and moved to Task 3
        if current_task_id == 3 and completed_tasks == 2:
            # Check if this is the first iteration of Task 3
            if 'subtask' in task_context:
                subtask = task_context['subtask']
                # If we're on the first subtask of Task 3, inject post_analytics
                if subtask['id'].endswith('a'):
                    return "post_analytics"

        # Post-Screening: Just completed stock screening (typically Task 3)
        # Trigger when we just finished Task 3 and moved to Task 4
        if current_task_id == 4 and completed_tasks == 3:
            if 'subtask' in task_context:
                subtask = task_context['subtask']
                if subtask['id'].endswith('a'):
                    return "post_screening"

        # Pre-Construction: About to build portfolio (typically Task 4)
        # Trigger when starting Task 4 if it mentions "construct" or "build"
        if 'construct' in current_task_desc or 'build' in current_task_desc:
            if current_task_id == 4:
                if 'subtask' in task_context:
                    subtask = task_context['subtask']
                    if subtask['id'].endswith('a'):
                        return "pre_construction"

        # Refinement Start: Entering iterative refinement phase (typically Task 5)
        # Trigger when starting Task 5 if it mentions "refine" or "iterative"
        if 'refine' in current_task_desc or 'iterative' in current_task_desc or 'refinement' in current_task_desc:
            if 'subtask' in task_context:
                subtask = task_context['subtask']
                # Only inject on first subtask of refinement task
                if subtask['id'].endswith('a'):
                    return "refinement_start"

        # Refinement Iteration: During refinement attempts
        # This is harder to detect automatically; for now, we skip this
        # In future, could track refinement iterations via execution engine

        return None
