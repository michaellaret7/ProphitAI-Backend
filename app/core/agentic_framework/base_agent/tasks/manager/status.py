"""Task status update operations."""

from typing import Optional, Callable, Dict, Any
from datetime import datetime
from ..models import TaskStatus
from .core import TaskManagerCore


class TaskStatusManager:
    """Manages task and subtask status updates.

    Responsibilities:
    - Update main task status with callbacks
    - Update subtask completion status
    """

    def __init__(self, core: TaskManagerCore, on_task_progression: Optional[Callable[[int], None]] = None):
        """Initialize status manager.

        Args:
            core: Core task manager for state access
            on_task_progression: Callback when task completes
        """
        self.core = core
        self.on_task_progression = on_task_progression

    def update_main_task(self, task_id: int, status: TaskStatus, reason: str = None) -> bool:
        """Update main task status with callback on completion.

        Args:
            task_id: Main task ID
            status: New TaskStatus
            reason: Optional reason for status change

        Returns:
            True if update successful
        """
        main_task = self.core.get_main_task_by_id(task_id)
        if not main_task:
            if self.core.verbose:
                print(f"Main task {task_id} not found")
            return False

        old_status = main_task.status
        main_task.status = status

        # Log to execution history
        self.core.execution_history.append({
            'timestamp': datetime.now().isoformat(),
            'type': 'main_task_status_update',
            'task_id': task_id,
            'old_status': old_status.value,
            'new_status': status.value,
            'reason': reason
        })

        if self.core.verbose:
            print(f"Main Task {task_id}: {old_status.value} -> {status.value}")

        # Trigger callback if task completed
        if status == TaskStatus.COMPLETED and self.on_task_progression:
            if self.core.verbose:
                print(f"Task {task_id} marked complete, triggering progression callback...")
            self.on_task_progression(task_id)

        return True

    def update_subtask(self, main_task_id: int, subtask_id: str, completed: bool, reason: str = None) -> bool:
        """Update subtask completion status.

        Args:
            main_task_id: Parent main task ID
            subtask_id: Subtask ID
            completed: Completion status
            reason: Optional reason for change

        Returns:
            True if update successful
        """
        subtask = self.core.get_subtask_by_id(main_task_id, subtask_id)
        if not subtask:
            if self.core.verbose:
                print(f"SubTask {subtask_id} in Task {main_task_id} not found")
            return False

        old_completed = subtask.completed
        subtask.completed = completed

        # Log to execution history
        self.core.execution_history.append({
            'timestamp': datetime.now().isoformat(),
            'type': 'subtask_status_update',
            'main_task_id': main_task_id,
            'subtask_id': subtask_id,
            'old_completed': old_completed,
            'new_completed': completed,
            'reason': reason
        })

        if self.core.verbose:
            status_icon = "[✓]" if completed else "[ ]"
            print(f"  {status_icon} SubTask {subtask_id}: {'completed' if completed else 'pending'}")

        return True
