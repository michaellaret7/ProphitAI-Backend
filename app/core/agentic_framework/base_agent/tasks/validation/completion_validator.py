"""Simple, boolean-based task completion validator.

Replaces the 592-line TaskValidator with a simple, context-aware approach
that returns clear boolean values instead of confidence scores.
"""

from typing import Dict, Any
from ..models import MainTask, SubTask, TaskStatus
from .error_detection import has_error_in_result


class CompletionValidator:
    """Simple validator for task completion (implements CompletionChecker protocol).

    Returns simple boolean values - NO confidence scores.
    Uses context-aware error detection to avoid false positives.
    """

    def __init__(self, verbose: bool = False):
        """Initialize the validator.

        Args:
            verbose: Print debug messages
        """
        self.verbose = verbose

    def is_subtask_complete(self, subtask: SubTask) -> bool:
        """Check if a subtask is complete.

        A subtask is complete if:
        1. Has completion evidence
        2. Evidence doesn't contain errors
        3. All expected tools have been executed (if specified)

        NOTE: We do NOT check subtask.completed flag here, as that flag is set
        by the advancement logic AFTER this validator confirms completion.
        Checking it would create a circular dependency.

        Args:
            subtask: The SubTask to validate

        Returns:
            True if subtask is complete, False otherwise
        """
        # Must have evidence
        if not subtask.completion_evidence:
            if self.verbose:
                print(f"   Subtask {subtask.id}: No completion evidence")
            return False

        # Check evidence for errors
        for evidence in subtask.completion_evidence:
            if has_error_in_result(evidence):
                if self.verbose:
                    print(f"   Subtask {subtask.id}: Error in evidence: {str(evidence)[:100]}")
                return False

        # If subtask has expected_tools, verify all have been executed
        if hasattr(subtask, 'expected_tools') and subtask.expected_tools:
            executed_tools = set()
            for evidence_str in subtask.completion_evidence:
                # Extract tool names from evidence like "Executed 'tool_name'"
                evidence_lower = str(evidence_str).lower()
                for tool in subtask.expected_tools:
                    tool_lower = str(tool).lower()
                    # Check if tool name appears in evidence
                    if tool_lower in evidence_lower:
                        executed_tools.add(tool_lower)

            # Check if all expected tools were executed
            expected_tools_lower = {str(t).lower() for t in subtask.expected_tools}
            if not expected_tools_lower.issubset(executed_tools):
                missing = expected_tools_lower - executed_tools
                if self.verbose:
                    print(f"   Subtask {subtask.id}: Missing expected tools: {missing}")
                return False

        if self.verbose:
            print(f"   Subtask {subtask.id}: Complete ✅")
        return True

    def is_main_task_complete(self, task: MainTask) -> bool:
        """Check if a main task is complete.

        A main task is complete if:
        1. Status is COMPLETED
        2. All subtasks are complete (if any)
        3. Has completion evidence
        4. Evidence doesn't contain errors

        Args:
            task: The MainTask to validate

        Returns:
            True if task is complete, False otherwise
        """
        # Check status
        if task.status != TaskStatus.COMPLETED:
            if self.verbose:
                print(f"   Task {task.id}: Status is {task.status.value}, not COMPLETED")
            return False

        # Check all subtasks if any exist
        if task.subtasks:
            for subtask in task.subtasks:
                if not self.is_subtask_complete(subtask):
                    if self.verbose:
                        print(f"   Task {task.id}: Subtask {subtask.id} not complete")
                    return False

        # Must have completion evidence
        if not task.completion_evidence:
            if self.verbose:
                print(f"   Task {task.id}: No completion evidence")
            return False

        # Check evidence for errors
        for evidence in task.completion_evidence:
            if has_error_in_result(evidence):
                if self.verbose:
                    print(f"   Task {task.id}: Error in evidence: {str(evidence)[:100]}")
                return False

        if self.verbose:
            print(f"   Task {task.id}: Complete ✅")
        return True

    def get_completion_status(self, task: MainTask) -> Dict[str, Any]:
        """Get detailed completion status for a task.

        This is a helper method for debugging and logging.

        Args:
            task: The MainTask to analyze

        Returns:
            Dict with completion details
        """
        status = {
            'task_id': task.id,
            'status': task.status.value,
            'is_complete': self.is_main_task_complete(task),
            'has_evidence': len(task.completion_evidence) > 0,
            'evidence_count': len(task.completion_evidence),
            'total_subtasks': len(task.subtasks) if task.subtasks else 0,
            'completed_subtasks': 0,
        }

        # Count completed subtasks
        if task.subtasks:
            status['completed_subtasks'] = sum(
                1 for st in task.subtasks if self.is_subtask_complete(st)
            )

        return status