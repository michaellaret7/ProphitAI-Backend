"""DependencyManager - Task dependency tracking and availability.

Responsibilities:
- Track task dependencies (which tasks must complete before others)
- Check if task dependencies are satisfied
- Find next available task for execution
- Find tasks ready for parallel execution
- Manage BLOCKED task state transitions
"""

from typing import List, Optional, TYPE_CHECKING
from ..models import MainTask, TaskStatus

if TYPE_CHECKING:
    from .executor_core import ExecutorCore


class DependencyManager:
    """Manages task dependencies and availability."""

    def __init__(self, core: 'ExecutorCore'):
        """Initialize the dependency manager.

        Args:
            core: ExecutorCore instance for state access
        """
        self.core = core

    def get_task_dependencies(self, task_id: int) -> List[int]:
        """Get dependencies for a specific task.

        Args:
            task_id: ID of the task to check dependencies for

        Returns:
            List of task IDs that must be completed before this task
        """
        # For now, simple sequential dependency: task N depends on task N-1
        if task_id <= 1:
            return []
        return [task_id - 1]

    def check_task_dependencies_met(self, task_id: int) -> bool:
        """Check if all dependencies for a task are satisfied.

        Args:
            task_id: ID of task to check

        Returns:
            True if all dependencies are met
        """
        plan = self.core.task_store.get_current_structured_plan()
        if not plan:
            return True

        dependencies = self.get_task_dependencies(task_id)

        # Check each dependency
        for dep_id in dependencies:
            # Find the dependent task
            dep_task = None
            for task in plan.tasks:
                if task.id == dep_id:
                    dep_task = task
                    break

            # If dependency not found or not completed, dependencies not met
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                if self.core.verbose:
                    print(f"  ⚠️ Task {task_id} blocked: dependency {dep_id} not completed")
                return False

        return True

    def get_next_available_task(self) -> Optional[MainTask]:
        """Get the next task that can be started based on dependencies.

        Returns:
            Next available MainTask or None
        """
        plan = self.core.task_store.get_current_structured_plan()
        if not plan:
            return None

        # Re-evaluate BLOCKED tasks: if dependencies are now met, unblock to PENDING
        for task in plan.tasks:
            if task.status == TaskStatus.BLOCKED:
                if self.check_task_dependencies_met(task.id):
                    self.core.task_store.update_main_task_status(
                        task.id,
                        TaskStatus.PENDING,
                        "Dependencies met; unblocked"
                    )

        # Find first pending task with satisfied dependencies
        for task in plan.tasks:
            if task.status == TaskStatus.PENDING:
                if self.check_task_dependencies_met(task.id):
                    return task
                else:
                    # Mark as blocked if dependencies not met
                    task.status = TaskStatus.BLOCKED

        return None

    def get_parallel_ready_tasks(self) -> List[MainTask]:
        """Get tasks that can be executed in parallel (no dependencies blocking).

        Returns:
            List of MainTasks ready for parallel execution
        """
        plan = self.core.task_store.get_current_structured_plan()
        if not plan:
            return []

        parallel_ready = []

        for task in plan.tasks:
            if task.status == TaskStatus.PENDING:
                # Check if dependencies are met
                if self.check_task_dependencies_met(task.id):
                    parallel_ready.append(task)

        return parallel_ready
