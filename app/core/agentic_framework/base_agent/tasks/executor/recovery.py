"""RecoveryManager - Error handling, failure recovery, and stagnation detection.

Responsibilities:
- Handle task failures with recovery strategies
- Retry failed tasks
- Skip or use alternative approaches
- Detect execution stagnation
- Track error patterns
"""

from typing import Tuple, List, Any, TYPE_CHECKING
from ..models import TaskStatus

if TYPE_CHECKING:
    from .executor_core import ExecutorCore
    from .advancement import AdvancementManager


class RecoveryManager:
    """Manages error handling and failure recovery."""

    def __init__(self, core: 'ExecutorCore', advancement: 'AdvancementManager'):
        """Initialize the recovery manager.

        Args:
            core: ExecutorCore instance for state access
            advancement: AdvancementManager for task progression
        """
        self.core = core
        self.advancement = advancement

    def handle_task_failure(self, error_message: str, recovery_strategy: str = "retry") -> Tuple[bool, str]:
        """Handle task failure with intelligent recovery strategies.

        Args:
            error_message: Description of the failure
            recovery_strategy: Strategy to use ('retry', 'skip', 'alternative')

        Returns:
            Tuple of (success, message)
        """
        if not self.core.current_main_task:
            return False, "No current task to handle failure for"

        task_id = self.core.current_main_task.id

        if recovery_strategy == "retry":
            # Mark as failed and suggest retry
            self.core.task_store.mark_task_failed(
                task_id,
                error_message,
                "Consider retrying with different approach or tools"
            )

            # Reset current task for retry
            success = self.core.task_store.retry_failed_task(task_id, f"Auto-retry after: {error_message}")

            if success:
                return True, f"Task {task_id} reset for retry"
            else:
                return False, f"Failed to reset task {task_id} for retry"

        elif recovery_strategy == "skip":
            # Mark as skipped and move to next
            self.core.task_store.update_main_task_status(
                task_id,
                TaskStatus.SKIPPED,
                f"Skipped due to failure: {error_message}"
            )

            # Advance to next task
            success, message = self.advancement.advance_task_progression()
            return success, f"Skipped failed task, {message}"

        elif recovery_strategy == "alternative":
            # Don't mark as failed - instead mark current subtask as complete with alternative approach
            # This allows progression to continue

            # Add evidence about using alternative approach
            self.core.task_store.add_task_evidence(
                task_id,
                f"Alternative approach used due to: {error_message}"
            )

            # If there's a current subtask, mark it as complete to allow progression
            if self.core.current_subtask:
                self.core.task_store.update_subtask_status(
                    self.core.current_main_task.id,
                    self.core.current_subtask.id,
                    True,  # Mark as complete
                    f"Completed with alternative approach: {error_message}"
                )

                # Now advance to next subtask
                success, message = self.advancement.advance_task_progression()
                if success:
                    return True, f"Task {task_id} continued with alternative approach, {message}"
                else:
                    return True, f"Task {task_id} used alternative approach, but no next subtask"

            return True, f"Task {task_id} marked for alternative approach"

        else:
            return False, f"Unknown recovery strategy: {recovery_strategy}"

    def check_for_stagnation(self, recent_observations: List[Any], threshold: int = 3) -> Tuple[bool, str]:
        """Check if task execution is stagnating.

        Args:
            recent_observations: Recent tool observations
            threshold: Number of similar observations that indicate stagnation

        Returns:
            Tuple of (is_stagnating, reason)
        """
        if not self.core.current_main_task or len(recent_observations) < threshold:
            return False, "Insufficient data for stagnation check"

        # Check for repeated similar observations
        recent_strings = [str(obs)[:100] for obs in recent_observations[-threshold:]]

        # Simple stagnation check: if all recent observations are very similar
        unique_observations = set(recent_strings)
        if len(unique_observations) == 1:
            return True, f"Last {threshold} observations are identical"

        # Check for error repetition
        error_count = sum(1 for obs in recent_strings if any(
            error_word in obs.lower() for error_word in ['error', 'failed', 'exception']
        ))

        if error_count >= threshold - 1:
            return True, f"Repeated errors detected in last {threshold} observations"

        # Check for no progress indicators
        progress_indicators = ['success', 'completed', 'returned', 'generated', 'retrieved']
        progress_count = sum(1 for obs in recent_strings if any(
            indicator in obs.lower() for indicator in progress_indicators
        ))

        if progress_count == 0 and len(recent_strings) >= threshold:
            return True, f"No progress indicators in last {threshold} observations"

        return False, "No stagnation detected"
