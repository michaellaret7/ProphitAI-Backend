"""TaskStore Protocol for task state management.

Enables dependency inversion: ExecutionEngine depends on TaskStore protocol,
not concrete TaskManager implementation.
"""

from typing import Protocol, Optional
from ..tasks.models import TodoList, MainTask, SubTask, TaskStatus


class TaskStore(Protocol):
    """Protocol for task state storage and retrieval.

    Any class implementing these methods satisfies this protocol,
    enabling dependency injection and testing with mocks.
    """

    def add_structured_plan(self, plan: TodoList) -> None:
        """Add a structured plan to the store.

        Args:
            plan: The TodoList containing all tasks and subtasks
        """
        ...

    def get_current_structured_plan(self) -> Optional[TodoList]:
        """Get the current structured plan.

        Returns:
            The current TodoList, or None if no plan is loaded
        """
        ...

    def get_main_task_by_id(self, task_id: int) -> Optional[MainTask]:
        """Get a main task by its ID.

        Args:
            task_id: The unique identifier for the main task

        Returns:
            The MainTask if found, None otherwise
        """
        ...

    def get_subtask_by_id(self, main_task_id: int, subtask_id: str) -> Optional[SubTask]:
        """Get a subtask by its ID within a main task.

        Args:
            main_task_id: The ID of the parent main task
            subtask_id: The unique identifier for the subtask

        Returns:
            The SubTask if found, None otherwise
        """
        ...

    def update_main_task_status(self, task_id: int, status: TaskStatus, reason: str = None) -> bool:
        """Update the status of a main task.

        Args:
            task_id: The ID of the main task
            status: The new TaskStatus
            reason: Optional reason for the status change

        Returns:
            True if update successful, False otherwise
        """
        ...

    def update_subtask_status(self, main_task_id: int, subtask_id: str, completed: bool, reason: str = None) -> bool:
        """Update the completion status of a subtask.

        Args:
            main_task_id: The ID of the parent main task
            subtask_id: The ID of the subtask
            completed: Whether the subtask is completed
            reason: Optional reason for the status change

        Returns:
            True if update successful, False otherwise
        """
        ...

    def add_task_evidence(self, task_id: int, evidence: str, subtask_id: str = None) -> bool:
        """Add completion evidence to a task or subtask.

        Args:
            task_id: The ID of the main task
            evidence: Evidence string to add
            subtask_id: Optional subtask ID if adding to subtask

        Returns:
            True if evidence added successfully, False otherwise
        """
        ...

    def add_task_observation(self, task_id: int, observation: str, subtask_id: str = None) -> bool:
        """Add an observation to a task or subtask.

        Args:
            task_id: The ID of the main task
            observation: Observation string to add
            subtask_id: Optional subtask ID if adding to subtask

        Returns:
            True if observation added successfully, False otherwise
        """
        ...