"""Core task manager state and data access."""

from typing import List, Optional
from pathlib import Path
from ..models import TodoList, MainTask, SubTask


class TaskManagerCore:
    """Core task manager responsible for state and data access.

    Manages:
    - Structured plan storage
    - Task/subtask retrieval by ID
    - Execution history tracking
    """

    def __init__(self, verbose: bool = True, output_dir: Path = None):
        """Initialize core task manager.

        Args:
            verbose: Print status messages
            output_dir: Directory for storing task state
        """
        if not output_dir:
            raise ValueError("output_dir is required for TaskManager")

        self.verbose = verbose
        self.output_dir = output_dir
        self.execution_history: List[dict] = []
        self.structured_plan: Optional[TodoList] = None
        self.state_path = output_dir / "task_state.json"

        # Ensure directory exists
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def add_structured_plan(self, plan: TodoList) -> None:
        """Add a structured plan from the planning tool.

        Args:
            plan: TodoList containing main tasks and subtasks
        """
        self.structured_plan = plan

        if self.verbose:
            print(f"Added structured plan with {len(plan.tasks)} main tasks")

    def get_current_structured_plan(self) -> Optional[TodoList]:
        """Get the current structured plan.

        Returns:
            Current TodoList or None if no plan loaded
        """
        return self.structured_plan

    def get_main_task_by_id(self, task_id: int) -> Optional[MainTask]:
        """Get a main task from the structured plan by ID.

        Args:
            task_id: Main task ID

        Returns:
            MainTask if found, None otherwise
        """
        if not self.structured_plan:
            return None

        for task in self.structured_plan.tasks:
            if task.id == task_id:
                return task
        return None

    def get_subtask_by_id(self, main_task_id: int, subtask_id: str) -> Optional[SubTask]:
        """Get a subtask from a main task by ID.

        Args:
            main_task_id: Parent main task ID
            subtask_id: Subtask ID (e.g., '1a')

        Returns:
            SubTask if found, None otherwise
        """
        main_task = self.get_main_task_by_id(main_task_id)
        if not main_task:
            return None

        for subtask in main_task.subtasks:
            if subtask.id == subtask_id:
                return subtask
        return None

    def all_tasks_complete(self) -> bool:
        """Check if all main tasks are complete.

        Returns:
            True if all main tasks have COMPLETED status
        """
        if not self.structured_plan:
            return True

        from ..models import TaskStatus
        return all(task.status == TaskStatus.COMPLETED for task in self.structured_plan.tasks)

    def get_incomplete_tasks(self) -> List[dict]:
        """Get list of incomplete main tasks.

        Returns:
            List of dicts with id, description, status for incomplete tasks
        """
        incomplete = []

        if self.structured_plan:
            from ..models import TaskStatus
            for task in self.structured_plan.tasks:
                if task.status != TaskStatus.COMPLETED:
                    incomplete.append({
                        "id": task.id,
                        "description": task.description,
                        "status": task.status.value
                    })

        return incomplete
