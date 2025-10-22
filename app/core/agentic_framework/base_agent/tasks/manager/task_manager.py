"""Main TaskManager class using composition pattern."""

from typing import Optional, Callable
from pathlib import Path
from .core import TaskManagerCore
from .status import TaskStatusManager
from .evidence import TaskEvidenceManager
from .progress import TaskProgressManager
from .advanced import TaskAdvancedManager
from .persistence import TaskPersistenceManager
from ..models import TodoList, MainTask, SubTask, TaskStatus


class TaskManager:
    """Unified task manager using composition pattern.

    Components:
        core: State management and getters
        status: Status update operations
        evidence: Evidence and observation tracking
        progress: Progress summaries
        advanced: Advanced operations (add/remove/fail/retry)
        persistence: State persistence

    Example:
        manager = TaskManager(verbose=True, output_dir=Path("./output"))
        manager.core.add_structured_plan(plan)
        manager.status.update_main_task(1, TaskStatus.COMPLETED)
        manager.persistence.save_state()
    """

    def __init__(
        self,
        verbose: bool = True,
        output_dir: Path = None,
        on_task_progression: Optional[Callable[[int], None]] = None
    ):
        """Initialize TaskManager with all components.

        Args:
            verbose: Print status messages
            output_dir: Directory for storing task state
            on_task_progression: Callback when task completes
        """
        # Core state management
        self.core = TaskManagerCore(verbose=verbose, output_dir=output_dir)

        # Specialized components
        self.status = TaskStatusManager(self.core, on_task_progression)
        self.evidence = TaskEvidenceManager(self.core)
        self.progress = TaskProgressManager(self.core)
        self.advanced = TaskAdvancedManager(self.core)
        self.persistence = TaskPersistenceManager(self.core)

    # ============================================================================
    # TaskStore Protocol Implementation (Dependency Inversion)
    # Delegates to composition components for ExecutionEngine compatibility
    # ============================================================================

    def add_structured_plan(self, plan: TodoList) -> None:
        """Add a structured plan (delegates to core)."""
        return self.core.add_structured_plan(plan)

    def get_current_structured_plan(self) -> Optional[TodoList]:
        """Get current plan (delegates to core)."""
        return self.core.get_current_structured_plan()

    def get_main_task_by_id(self, task_id: int) -> Optional[MainTask]:
        """Get main task (delegates to core)."""
        return self.core.get_main_task_by_id(task_id)

    def get_subtask_by_id(self, main_task_id: int, subtask_id: str) -> Optional[SubTask]:
        """Get subtask (delegates to core)."""
        return self.core.get_subtask_by_id(main_task_id, subtask_id)

    def update_main_task_status(self, task_id: int, status: TaskStatus, reason: str = None) -> bool:
        """Update main task status (delegates to status)."""
        return self.status.update_main_task(task_id, status, reason)

    def update_subtask_status(self, main_task_id: int, subtask_id: str, completed: bool, reason: str = None) -> bool:
        """Update subtask status (delegates to status)."""
        return self.status.update_subtask(main_task_id, subtask_id, completed, reason)

    def add_task_evidence(self, task_id: int, evidence: str, subtask_id: str = None) -> bool:
        """Add task evidence (delegates to evidence)."""
        return self.evidence.add_evidence(task_id, evidence, subtask_id)

    def add_task_observation(self, task_id: int, observation: str, subtask_id: str = None) -> bool:
        """Add task observation (delegates to evidence)."""
        return self.evidence.add_observation(task_id, observation, subtask_id)

    def mark_task_failed(self, task_id: int, failure_reason: str, subtask_id: str = None) -> bool:
        """Mark task as failed (delegates to advanced)."""
        return self.advanced.mark_task_failed(task_id, failure_reason, subtask_id)

    def retry_failed_task(self, task_id: int, retry_reason: str = "Manual retry") -> bool:
        """Retry a failed task (delegates to advanced)."""
        return self.advanced.retry_failed_task(task_id, retry_reason)
