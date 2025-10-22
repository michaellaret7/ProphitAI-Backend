"""AdvancementManager - Task progression and advancement logic.

Responsibilities:
- Orchestrate task progression (subtask → subtask, task → task)
- Complete current subtasks/tasks and move to next
- Handle task completion callbacks
- Manage plan completion detection
"""

from typing import Tuple, Optional, TYPE_CHECKING
from ..models import TaskStatus

if TYPE_CHECKING:
    from .executor_core import ExecutorCore
    from .dependencies import DependencyManager


class AdvancementManager:
    """Manages task progression and advancement logic."""

    def __init__(self, core: 'ExecutorCore', dependencies: 'DependencyManager'):
        """Initialize the advancement manager.

        Args:
            core: ExecutorCore instance for state access
            dependencies: DependencyManager for finding next available tasks
        """
        self.core = core
        self.dependencies = dependencies

    def advance_task_progression(self) -> Tuple[bool, str]:
        """Move to next subtask or main task.

        Returns:
            Tuple of (success, message) indicating what happened
        """
        if not self.core.plan_loaded:
            return False, "No plan loaded"

        plan = self.core.task_store.get_current_structured_plan()
        if not plan:
            return False, "No structured plan available"

        # If we have a current subtask, try to advance to next subtask
        if self.core.current_subtask and self.core.current_main_task:
            current_subtask_idx = -1
            for i, st in enumerate(self.core.current_main_task.subtasks):
                if st.id == self.core.current_subtask.id:
                    current_subtask_idx = i
                    break

            # Check if there's a next subtask
            if current_subtask_idx >= 0 and current_subtask_idx < len(self.core.current_main_task.subtasks) - 1:
                # Mark current subtask as completed using TaskManager
                self.core.task_store.update_subtask_status(
                    self.core.current_main_task.id,
                    self.core.current_subtask.id,
                    True,
                    "Auto-completed via task progression"
                )

                # Move to next subtask
                self.core.current_subtask = self.core.current_main_task.subtasks[current_subtask_idx + 1]

                if self.core.verbose:
                    print(f"  ✅ Completed SubTask {self.core.current_main_task.subtasks[current_subtask_idx].id}")
                    print(f"  → Moving to SubTask {self.core.current_subtask.id}: {self.core.current_subtask.description}")

                return True, f"Advanced to subtask {self.core.current_subtask.id}"
            else:
                # No more subtasks, complete main task
                if self.core.current_subtask:
                    self.core.task_store.update_subtask_status(
                        self.core.current_main_task.id,
                        self.core.current_subtask.id,
                        True,
                        "Final subtask completed"
                    )

                # Complete main task using TaskManager
                self.core.task_store.update_main_task_status(
                    self.core.current_main_task.id,
                    TaskStatus.COMPLETED,
                    "All subtasks completed"
                )

                # Try to advance to next main task
                return self._advance_to_next_main_task()

        # No subtask, try to advance main task
        if self.core.current_main_task:
            self.core.task_store.update_main_task_status(
                self.core.current_main_task.id,
                TaskStatus.COMPLETED,
                "Task completed without subtasks"
            )
            return self._advance_to_next_main_task()

        return False, "No current task to advance"

    def _advance_to_next_main_task(self) -> Tuple[bool, str]:
        """Advance to the next available main task in the plan based on dependencies.

        Returns:
            Tuple of (success, message)
        """
        plan = self.core.task_store.get_current_structured_plan()
        if not plan or not self.core.current_main_task:
            return False, "No plan or current task"

        # Mark current task as completed using TaskManager
        completed_task_id = self.core.current_main_task.id
        self.core.task_store.update_main_task_status(
            completed_task_id,
            TaskStatus.COMPLETED,
            "Advanced to next main task"
        )

        if self.core.verbose:
            print(f"✅ Completed Task {completed_task_id}: {self.core.current_main_task.description}")

        # Invoke task completion callback
        if self.core.on_task_complete:
            self.core.on_task_complete(completed_task_id)

        # Find next available task based on dependencies
        next_task = self.dependencies.get_next_available_task()

        if next_task:
            # Move to next available task
            self.core.current_main_task = next_task
            self.core.task_store.update_main_task_status(
                self.core.current_main_task.id,
                TaskStatus.IN_PROGRESS,
                "Started next available task"
            )

            # Set first subtask if available
            if self.core.current_main_task.subtasks:
                self.core.current_subtask = self.core.current_main_task.subtasks[0]
                # Initialize first subtask
                self.core.task_store.update_subtask_status(
                    self.core.current_main_task.id,
                    self.core.current_subtask.id,
                    False,
                    "Subtask activated"
                )
            else:
                self.core.current_subtask = None

            if self.core.verbose:
                print(f"▶️ Starting Task {self.core.current_main_task.id}: {self.core.current_main_task.description}")
                if self.core.current_subtask:
                    print(f"  → SubTask {self.core.current_subtask.id}: {self.core.current_subtask.description}")

            # Invoke task advance callback
            if self.core.on_task_advance:
                self.core.on_task_advance(self.core.current_main_task.id, f"Started: {self.core.current_main_task.description}")

            return True, f"Advanced to main task {self.core.current_main_task.id}"
        else:
            # Check if all tasks are complete or if some are blocked
            pending_tasks = [t for t in plan.tasks if t.status == TaskStatus.PENDING]
            blocked_tasks = [t for t in plan.tasks if t.status == TaskStatus.BLOCKED]

            if blocked_tasks and not pending_tasks:
                # All remaining tasks are blocked
                if self.core.verbose:
                    print(f"⚠️ All remaining tasks are blocked by dependencies")
                    for task in blocked_tasks:
                        print(f"  - Task {task.id}: {task.description}")

                return False, f"All remaining {len(blocked_tasks)} tasks are blocked by dependencies"

            elif not pending_tasks and not blocked_tasks:
                # All tasks completed
                self.core.current_main_task = None
                self.core.current_subtask = None

                if self.core.verbose:
                    print("🎉 All tasks in plan completed!")
                return True, "Plan execution completed"

            else:
                # This shouldn't happen but handle gracefully
                return False, "No next task available but plan not complete"
