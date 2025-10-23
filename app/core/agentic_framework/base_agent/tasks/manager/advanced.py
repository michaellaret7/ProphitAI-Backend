"""Advanced task management operations."""

from typing import List, Optional
from datetime import datetime
from ..models import MainTask, TaskStatus
from .core import TaskManagerCore


class TaskAdvancedManager:
    """Manages advanced task operations.

    Responsibilities:
    - Add new main tasks to plan
    - Remove tasks from plan
    - Mark tasks as failed
    - Retry failed tasks
    """

    def __init__(self, core: TaskManagerCore):
        """Initialize advanced manager.

        Args:
            core: Core task manager for state access
        """
        self.core = core

    def add_main_task_to_plan(
        self,
        task_id: int,
        description: str,
        predicted_tools: List[str] = None,
        insert_after: int = None
    ) -> bool:
        """Add a new main task to the structured plan.

        Args:
            task_id: ID for the new task
            description: Task description
            predicted_tools: Tools predicted for this task
            insert_after: Task ID to insert after (None = append to end)

        Returns:
            True if task added successfully
        """
        if not self.core.structured_plan:
            if self.core.verbose:
                print("Cannot add task: no structured plan loaded")
            return False

        # Check if task ID already exists
        for existing_task in self.core.structured_plan.tasks:
            if existing_task.id == task_id:
                if self.core.verbose:
                    print(f"Task {task_id} already exists")
                return False

        # Create new main task
        new_task = MainTask(
            id=task_id,
            description=description,
            predicted_tool_use=predicted_tools or []
        )

        # Insert at appropriate position
        if insert_after is None:
            # Append to end
            self.core.structured_plan.tasks.append(new_task)
        else:
            # Find insertion point
            insert_idx = -1
            for i, task in enumerate(self.core.structured_plan.tasks):
                if task.id == insert_after:
                    insert_idx = i + 1
                    break

            if insert_idx >= 0:
                self.core.structured_plan.tasks.insert(insert_idx, new_task)
            else:
                # If insert_after not found, append to end
                self.core.structured_plan.tasks.append(new_task)

        # Log addition
        self.core.execution_history.append({
            'timestamp': datetime.now().isoformat(),
            'type': 'main_task_added',
            'task_id': task_id,
            'description': description,
            'predicted_tools': predicted_tools,
            'insert_after': insert_after
        })

        if self.core.verbose:
            position = f"after Task {insert_after}" if insert_after else "at end"
            print(f"Added Main Task {task_id} {position}: {description}")

        return True

    def remove_main_task_from_plan(self, task_id: int, reason: str = "Manual removal") -> bool:
        """Remove a main task from the structured plan.

        Args:
            task_id: ID of task to remove
            reason: Reason for removal

        Returns:
            True if task removed successfully
        """
        if not self.core.structured_plan:
            return False

        # Find and remove task
        task_to_remove = None
        remove_idx = -1

        for i, task in enumerate(self.core.structured_plan.tasks):
            if task.id == task_id:
                task_to_remove = task
                remove_idx = i
                break

        if not task_to_remove:
            if self.core.verbose:
                print(f"Task {task_id} not found for removal")
            return False

        # Remove the task
        self.core.structured_plan.tasks.pop(remove_idx)

        # Log removal
        self.core.execution_history.append({
            'timestamp': datetime.now().isoformat(),
            'type': 'main_task_removed',
            'task_id': task_id,
            'description': task_to_remove.description,
            'reason': reason
        })

        if self.core.verbose:
            print(f"Removed Main Task {task_id}: {task_to_remove.description}")

        return True

    def mark_task_failed(
        self,
        task_id: int,
        error_message: str,
        recovery_suggestion: str = None
    ) -> bool:
        """Mark a task as failed and optionally suggest recovery.

        Args:
            task_id: ID of the failed task
            error_message: Description of the failure
            recovery_suggestion: Optional suggestion for recovery

        Returns:
            True if task marked as failed
        """
        main_task = self.core.get_main_task_by_id(task_id)
        if not main_task:
            return False

        # Update task status to failed
        old_status = main_task.status
        main_task.status = TaskStatus.FAILED

        # Add failure information to completion evidence
        failure_info = f"Task failed: {error_message}"
        if recovery_suggestion:
            failure_info += f" | Recovery suggestion: {recovery_suggestion}"

        main_task.completion_evidence.append(failure_info)

        # Log failure
        self.core.execution_history.append({
            'timestamp': datetime.now().isoformat(),
            'type': 'task_failed',
            'task_id': task_id,
            'old_status': old_status.value,
            'error_message': error_message,
            'recovery_suggestion': recovery_suggestion
        })

        if self.core.verbose:
            print(f"Task {task_id} marked as FAILED: {error_message}")
            if recovery_suggestion:
                print(f"  Recovery suggestion: {recovery_suggestion}")

        return True

    def retry_failed_task(self, task_id: int, retry_reason: str = "Manual retry") -> bool:
        """Retry a failed task by resetting it to pending.

        Args:
            task_id: ID of the failed task to retry
            retry_reason: Reason for retry

        Returns:
            True if task reset for retry
        """
        main_task = self.core.get_main_task_by_id(task_id)
        if not main_task:
            return False

        if main_task.status != TaskStatus.FAILED:
            if self.core.verbose:
                print(f"Task {task_id} is not in FAILED status (current: {main_task.status.value})")
            return False

        # Reset task status and clear failure evidence
        old_status = main_task.status
        main_task.status = TaskStatus.PENDING

        # Reset subtasks if any
        for subtask in main_task.subtasks:
            subtask.completed = False
            subtask.completion_evidence = []
            subtask.observations = []

        # Clear task evidence and observations for fresh start
        main_task.completion_evidence = []
        main_task.observations = []

        # Log retry
        self.core.execution_history.append({
            'timestamp': datetime.now().isoformat(),
            'type': 'task_retried',
            'task_id': task_id,
            'old_status': old_status.value,
            'retry_reason': retry_reason
        })

        if self.core.verbose:
            print(f"Task {task_id} reset for retry: {retry_reason}")

        return True
