"""Finality detection for agent iterations.

This module determines when an agent has completed its task and is ready
to provide a final answer.
"""

from typing import Tuple, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..agent import BaseAgent


class FinalityChecker:
    """Checks if agent iteration should finalize with a final answer.

    This class encapsulates the logic for detecting when an agent has
    completed its work and is ready to provide a final answer, including
    checking plan completion status.
    """

    def __init__(self, agent: 'BaseAgent'):
        """Initialize finality checker.

        Args:
            agent: The BaseAgent instance that owns this checker
        """
        self.agent = agent

    def check_finality(self, assistant_message: str) -> Tuple[bool, str]:
        """Check if assistant message indicates finality.

        Args:
            assistant_message: The assistant's message content

        Returns:
            Tuple of (is_final, final_text)
        """
        # Use agent's utility method to check for finality keywords
        if self.agent.utilities.looks_final(assistant_message):
            # Check plan completion status
            completion_status = self._check_plan_completion_status()

            if completion_status["can_finalize"]:
                if self.agent.verbose and completion_status.get("plan_loaded"):
                    print(f"✅ Plan execution complete: {completion_status['completed_tasks']}/{completion_status['total_tasks']} tasks finished")
                return True, assistant_message
            else:
                # Cannot finalize yet - plan incomplete
                return False, ""

        return False, ""

    def _check_plan_completion_status(self) -> Dict[str, Any]:
        """Check overall plan completion status and readiness for final answer.

        Returns:
            Dictionary with completion status and context
        """
        if not self.agent.execution_engine.plan_loaded:
            return {"plan_loaded": False, "can_finalize": True}

        task_context = self.agent.execution_engine.get_current_task_context()
        execution_summary = self.agent.execution_engine.get_execution_summary()

        # Check if all tasks are completed
        all_complete = (task_context.get("status") != "executing" or
                       execution_summary.get('completed_main_tasks', 0) == execution_summary.get('total_main_tasks', 0))

        return {
            "plan_loaded": True,
            "all_tasks_complete": all_complete,
            "can_finalize": all_complete,
            "progress_percentage": task_context.get('progress', {}).get('percentage', 0),
            "completed_tasks": execution_summary.get('completed_main_tasks', 0),
            "total_tasks": execution_summary.get('total_main_tasks', 0),
            "current_task": task_context.get('main_task', {}).get('id') if task_context.get("status") == "executing" else None
        }
