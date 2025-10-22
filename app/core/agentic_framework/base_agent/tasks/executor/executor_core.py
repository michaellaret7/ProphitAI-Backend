"""ExecutorCore - Core state management for plan execution.

Responsibilities:
- Initialize executor with task_store and callbacks
- Load and reset structured plans
- Track current execution state (main task, subtask)
- Provide execution context for agent prompting
"""

from typing import Optional, Dict, Any, Callable
from ...protocols.task_store import TaskStore
from ..validator import TaskValidator
from ..models import TodoList, MainTask, SubTask, TaskStatus


class ExecutorCore:
    """Core state management for plan execution."""

    def __init__(
        self,
        task_store: TaskStore,
        on_task_complete: Optional[Callable[[int], None]] = None,
        on_task_advance: Optional[Callable[[int, str], None]] = None,
        verbose: bool = True
    ):
        """Initialize the executor core.

        Args:
            task_store: TaskStore protocol implementation for accessing task state
            on_task_complete: Optional callback when a task completes
            on_task_advance: Optional callback when execution advances to next task
            verbose: Whether to print execution messages
        """
        self.task_store = task_store
        self.on_task_complete = on_task_complete
        self.on_task_advance = on_task_advance
        self.verbose = verbose
        self.current_main_task: Optional[MainTask] = None
        self.current_subtask: Optional[SubTask] = None
        self.plan_loaded: bool = False

        # Initialize task validator for intelligent completion detection
        self.task_validator = TaskValidator(verbose=verbose)

    def load_plan(self, plan: TodoList) -> bool:
        """Load a structured plan into the execution engine.

        Args:
            plan: The TodoList to execute

        Returns:
            True if plan loaded successfully
        """
        try:
            # CRITICAL: Reset all task completion states to ensure fresh execution
            # This prevents the circular validation bug where pre-marked tasks skip execution
            for task in plan.tasks:
                task.status = TaskStatus.PENDING
                task.completion_evidence = []
                task.observations = []
                for subtask in task.subtasks:
                    subtask.completed = False
                    subtask.completion_evidence = []
                    subtask.observations = []

            # Store the plan in task store
            self.task_store.add_structured_plan(plan)

            # Initialize first task if available
            if plan.tasks:
                # Set first main task as current
                self.current_main_task = plan.tasks[0]
                self.task_store.update_main_task_status(
                    self.current_main_task.id,
                    TaskStatus.IN_PROGRESS,
                    "Plan execution started"
                )

                # Set first subtask if available
                if self.current_main_task.subtasks:
                    self.current_subtask = self.current_main_task.subtasks[0]
                    # Ensure subtask starts as not completed
                    self.task_store.update_subtask_status(
                        self.current_main_task.id,
                        self.current_subtask.id,
                        False,
                        "Subtask initialized"
                    )

                self.plan_loaded = True

                if self.verbose:
                    print(f"📋 Execution Engine loaded plan with {len(plan.tasks)} main tasks")
                    print(f"▶️ Starting with Task {self.current_main_task.id}: {self.current_main_task.description}")
                    if self.current_subtask:
                        print(f"  → SubTask {self.current_subtask.id}: {self.current_subtask.description}")

                return True
            else:
                if self.verbose:
                    print("⚠️ Plan has no tasks to execute")
                return False

        except Exception as e:
            if self.verbose:
                print(f"❌ Failed to load plan: {e}")
            return False

    def get_current_task(self) -> Optional[MainTask]:
        """Get the current main task being executed.

        Returns:
            The current MainTask or None if no plan loaded
        """
        if not self.plan_loaded:
            return None
        return self.current_main_task

    def get_current_subtask(self) -> Optional[SubTask]:
        """Get the current subtask being executed.

        Returns:
            The current SubTask or None if no subtask active
        """
        if not self.plan_loaded:
            return None
        return self.current_subtask

    def get_current_task_context(self) -> Dict[str, Any]:
        """Get context about the current task for agent prompting.

        Returns:
            Dictionary with current task information
        """
        if not self.plan_loaded or not self.current_main_task:
            return {"status": "no_plan"}

        context = {
            "status": "executing",
            "main_task": {
                "id": self.current_main_task.id,
                "description": self.current_main_task.description,
                "status": self.current_main_task.status.value,
                "predicted_tools": self.current_main_task.predicted_tool_use
            }
        }

        if self.current_subtask:
            context["subtask"] = {
                "id": self.current_subtask.id,
                "description": self.current_subtask.description,
                "completed": self.current_subtask.completed
            }

        # Add progress information
        plan = self.task_store.get_current_structured_plan()
        if plan:
            completed_main = sum(1 for t in plan.tasks if t.status == TaskStatus.COMPLETED)
            total_main = len(plan.tasks)
            context["progress"] = {
                "main_tasks_completed": completed_main,
                "main_tasks_total": total_main,
                "percentage": int((completed_main / total_main) * 100) if total_main > 0 else 0
            }

        return context
