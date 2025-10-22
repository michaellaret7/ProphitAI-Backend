"""PlanExecutor - Composed from specialized managers.

The plan executor drives task execution based on structured plans, using
composition of focused manager components.

Components:
    - ExecutorCore: State management (plan, current task, callbacks)
    - DependencyManager: Task dependencies and availability
    - AdvancementManager: Task progression logic
    - ToolIntegrationManager: Tool result processing
    - CompletionManager: Completion checking and analytics
    - RecoveryManager: Error handling and failure recovery
"""

from typing import Optional, Callable, Dict, Any, List, Tuple
from ...protocols.task_store import TaskStore
from ..models import TodoList, MainTask, SubTask
from .executor_core import ExecutorCore
from .dependencies import DependencyManager
from .advancement import AdvancementManager
from .tool_integration import ToolIntegrationManager
from .completion import CompletionManager
from .recovery import RecoveryManager


class PlanExecutor:
    """Drives task execution based on structured plans using composition pattern."""

    def __init__(
        self,
        task_store: TaskStore,
        on_task_complete: Optional[Callable[[int], None]] = None,
        on_task_advance: Optional[Callable[[int, str], None]] = None,
        verbose: bool = True
    ):
        """Initialize the plan execution engine.

        Args:
            task_store: TaskStore protocol implementation for accessing task state
            on_task_complete: Optional callback when a task completes
            on_task_advance: Optional callback when execution advances to next task
            verbose: Whether to print execution messages
        """
        # Core state management
        self.core = ExecutorCore(
            task_store=task_store,
            on_task_complete=on_task_complete,
            on_task_advance=on_task_advance,
            verbose=verbose
        )

        # Specialized managers (each depends on core)
        self.dependencies = DependencyManager(self.core)
        self.advancement = AdvancementManager(self.core, self.dependencies)
        self.tool_integration = ToolIntegrationManager(self.core, self.advancement)
        self.completion = CompletionManager(self.core)
        self.recovery = RecoveryManager(self.core, self.advancement)

    # ============================================================================
    # Public API - Delegates to Manager Components
    # ============================================================================

    # --- Core State Methods ---

    def load_plan(self, plan: TodoList) -> bool:
        """Load a structured plan (delegates to core)."""
        return self.core.load_plan(plan)

    def get_current_task(self) -> Optional[MainTask]:
        """Get current main task (delegates to core)."""
        return self.core.get_current_task()

    def get_current_subtask(self) -> Optional[SubTask]:
        """Get current subtask (delegates to core)."""
        return self.core.get_current_subtask()

    def get_current_task_context(self) -> Dict[str, Any]:
        """Get current task context (delegates to core)."""
        return self.core.get_current_task_context()

    # --- Advancement Methods ---

    def advance_task_progression(self) -> Tuple[bool, str]:
        """Advance to next subtask/task (delegates to advancement)."""
        return self.advancement.advance_task_progression()

    # --- Tool Integration Methods ---

    def update_task_from_tool_result(self, tool_name: str, result: Any) -> bool:
        """Process tool result (delegates to tool_integration)."""
        return self.tool_integration.update_task_from_tool_result(tool_name, result)

    def collect_evidence_from_tool_result(self, tool_name: str, result: Any) -> List[str]:
        """Collect evidence from tool result (delegates to tool_integration)."""
        return self.tool_integration.collect_evidence_from_tool_result(tool_name, result)

    # --- Completion Methods ---

    def check_task_completion_conditions(self) -> Tuple[bool, str]:
        """Check if task should be completed (delegates to completion)."""
        return self.completion.check_task_completion_conditions()

    def get_execution_summary(self) -> Dict[str, Any]:
        """Get execution summary (delegates to completion)."""
        return self.completion.get_execution_summary()

    def get_intelligent_completion_analysis(self) -> Dict[str, Any]:
        """Get detailed completion analysis (delegates to completion)."""
        return self.completion.get_intelligent_completion_analysis()

    # --- Dependency Methods ---

    def get_task_dependencies(self, task_id: int) -> List[int]:
        """Get task dependencies (delegates to dependencies)."""
        return self.dependencies.get_task_dependencies(task_id)

    def check_task_dependencies_met(self, task_id: int) -> bool:
        """Check if dependencies are met (delegates to dependencies)."""
        return self.dependencies.check_task_dependencies_met(task_id)

    def get_next_available_task(self) -> Optional[MainTask]:
        """Get next available task (delegates to dependencies)."""
        return self.dependencies.get_next_available_task()

    def get_parallel_ready_tasks(self) -> List[MainTask]:
        """Get tasks ready for parallel execution (delegates to dependencies)."""
        return self.dependencies.get_parallel_ready_tasks()

    # --- Recovery Methods ---

    def handle_task_failure(self, error_message: str, recovery_strategy: str = "retry") -> Tuple[bool, str]:
        """Handle task failure (delegates to recovery)."""
        return self.recovery.handle_task_failure(error_message, recovery_strategy)

    def check_for_stagnation(self, recent_observations: List[Any], threshold: int = 3) -> Tuple[bool, str]:
        """Check for execution stagnation (delegates to recovery)."""
        return self.recovery.check_for_stagnation(recent_observations, threshold)

    # ============================================================================
    # Properties for Backward Compatibility (if needed)
    # ============================================================================

    @property
    def plan_loaded(self) -> bool:
        """Check if plan is loaded."""
        return self.core.plan_loaded

    @property
    def current_main_task(self) -> Optional[MainTask]:
        """Get current main task."""
        return self.core.current_main_task

    @property
    def current_subtask(self) -> Optional[SubTask]:
        """Get current subtask."""
        return self.core.current_subtask

    @property
    def verbose(self) -> bool:
        """Get verbose flag."""
        return self.core.verbose

    @property
    def task_store(self) -> TaskStore:
        """Get task store."""
        return self.core.task_store
