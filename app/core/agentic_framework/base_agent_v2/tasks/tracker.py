"""Lightweight task tracker for Base Agent V2.

Simple task tracking with NO automatic advancement.
Agent controls progression via explicit tool calls.
"""

from typing import Optional, Dict, Any, List
from .models import TodoList, MainTask, SubTask, TaskStatus


class LightweightTaskTracker:
    """
    Simple task tracking for V2 agent.

    Key principles:
    - NO automatic advancement (agent controls via tools)
    - Minimal overhead (just track current state)
    - Record reasoning at each phase
    - Agent decides when ready to progress
    """

    def __init__(self, todo_list: TodoList):
        """
        Initialize tracker with a TodoList from planning tool.

        Args:
            todo_list: Structured plan with main tasks and subtasks
        """
        self.todo_list = todo_list
        self.current_main_task_id: Optional[int] = None
        self.current_subtask_id: Optional[str] = None

        # Initialize first task as current
        self._initialize_first_task()

    def _initialize_first_task(self) -> None:
        """Set the first task/subtask as current and mark as in_progress."""
        if not self.todo_list.tasks:
            return

        # Set first main task as current
        first_task = self.todo_list.tasks[0]
        self.current_main_task_id = first_task.id
        first_task.status = TaskStatus.IN_PROGRESS

        # If it has subtasks, set first subtask as current
        if first_task.subtasks:
            self.current_subtask_id = first_task.subtasks[0].id

    def get_current_context(self) -> Dict[str, Any]:
        """
        Get current task/subtask context for agent awareness.

        Returns:
        {
            "status": "executing" | "completed",
            "current_main_task": {
                "id": 2,
                "description": "Comprehensive fundamental analysis",
                "status": "in_progress",
                "has_subtasks": true,
                "current_subtask_index": 0,
                "total_subtasks": 3
            },
            "current_subtask": {
                "id": "2a",
                "description": "Analyze quality (ROIC, margins, FCF)",
                "completed": false
            },
            "overall_progress": {
                "main_tasks_completed": 1,
                "main_tasks_total": 5,
                "percentage": 20
            },
            "next_subtask": {
                "id": "2b",
                "description": "Assess valuation..."
            } | null,
            "next_main_task": {
                "id": 3,
                "description": "Risk analysis"
            } | null
        }
        """
        # Check if all tasks complete
        all_complete = all(task.status == TaskStatus.COMPLETED for task in self.todo_list.tasks)

        if all_complete:
            return {
                "status": "completed",
                "message": "All tasks completed. Ready for final answer.",
                "overall_progress": self._get_overall_progress()
            }

        # Get current main task
        current_task = self._get_current_main_task()
        if not current_task:
            return {"status": "error", "message": "No current task found"}

        context = {
            "status": "executing",
            "current_main_task": {
                "id": current_task.id,
                "description": current_task.description,
                "status": current_task.status.value,
                "has_subtasks": len(current_task.subtasks) > 0,
                "total_subtasks": len(current_task.subtasks)
            },
            "overall_progress": self._get_overall_progress()
        }

        # Add current subtask info if exists
        if self.current_subtask_id:
            current_subtask = self._get_current_subtask()
            if current_subtask:
                context["current_subtask"] = {
                    "id": current_subtask.id,
                    "description": current_subtask.description,
                    "completed": current_subtask.completed
                }

                # Add current subtask index
                subtask_index = next(
                    (i for i, st in enumerate(current_task.subtasks) if st.id == current_subtask.id),
                    None
                )
                if subtask_index is not None:
                    context["current_main_task"]["current_subtask_index"] = subtask_index

                # Get next subtask if exists
                if subtask_index is not None and subtask_index + 1 < len(current_task.subtasks):
                    next_st = current_task.subtasks[subtask_index + 1]
                    context["next_subtask"] = {
                        "id": next_st.id,
                        "description": next_st.description
                    }
                else:
                    context["next_subtask"] = None
        else:
            context["current_subtask"] = None
            context["next_subtask"] = None

        # Get next main task if exists
        task_index = next(
            (i for i, t in enumerate(self.todo_list.tasks) if t.id == current_task.id),
            None
        )
        if task_index is not None and task_index + 1 < len(self.todo_list.tasks):
            next_task = self.todo_list.tasks[task_index + 1]
            context["next_main_task"] = {
                "id": next_task.id,
                "description": next_task.description
            }
        else:
            context["next_main_task"] = None

        return context

    def advance_subtask(self, completion_reasoning: str, key_findings: str) -> Dict[str, Any]:
        """
        Advance to next subtask (called by agent tool).

        Agent must explicitly call this - NO automatic advancement.

        Args:
            completion_reasoning: Why agent thinks subtask is complete
            key_findings: Main insights from this subtask

        Returns:
            {
                "success": true,
                "message": "Advanced to subtask 2b",
                "old_subtask": {"id": "2a", "completed": true},
                "new_subtask": {"id": "2b", "description": "..."},
                "remaining_subtasks": 2
            }
        """
        current_task = self._get_current_main_task()
        if not current_task:
            return {"success": False, "error": "No current main task"}

        if not self.current_subtask_id:
            return {"success": False, "error": "No current subtask to advance"}

        current_subtask = self._get_current_subtask()
        if not current_subtask:
            return {"success": False, "error": "Current subtask not found"}

        # Mark current subtask complete
        current_subtask.completed = True

        # Record agent's reasoning for completion
        current_subtask.reasoning_log.append(
            f"[COMPLETION] {completion_reasoning}"
        )

        # Store key findings
        if key_findings:
            current_subtask.observations.append(
                f"[KEY FINDINGS] {key_findings}"
            )

        # Get current subtask index
        subtask_index = next(
            (i for i, st in enumerate(current_task.subtasks) if st.id == current_subtask.id),
            None
        )

        if subtask_index is None:
            return {"success": False, "error": "Could not find subtask index"}

        # Check if there's a next subtask
        if subtask_index + 1 < len(current_task.subtasks):
            # Advance to next subtask
            next_subtask = current_task.subtasks[subtask_index + 1]
            self.current_subtask_id = next_subtask.id

            return {
                "success": True,
                "message": f"Advanced to subtask {next_subtask.id}",
                "old_subtask": {
                    "id": current_subtask.id,
                    "completed": True,
                    "findings": key_findings
                },
                "new_subtask": {
                    "id": next_subtask.id,
                    "description": next_subtask.description,
                    "completed": False
                },
                "remaining_subtasks": len(current_task.subtasks) - (subtask_index + 1)
            }
        else:
            # No more subtasks - ready to advance main task
            self.current_subtask_id = None
            return {
                "success": True,
                "message": "All subtasks complete. Ready to advance main task.",
                "old_subtask": {
                    "id": current_subtask.id,
                    "completed": True,
                    "findings": key_findings
                },
                "new_subtask": None,
                "ready_for_main_task_advancement": True
            }

    def advance_main_task(self, completion_reasoning: str, key_findings: str) -> Dict[str, Any]:
        """
        Advance to next main task (called by agent tool).

        Agent must explicitly call this - NO automatic advancement.

        Args:
            completion_reasoning: Why agent thinks task is complete
            key_findings: Main insights and discoveries from this task

        Returns:
            {
                "success": true,
                "message": "Advanced to task 3",
                "old_task": {"id": 2, "completed": true},
                "new_task": {"id": 3, "description": "..."},
                "remaining_tasks": 2
            }
        """
        current_task = self._get_current_main_task()
        if not current_task:
            return {"success": False, "error": "No current main task"}

        # Validate all subtasks are complete (if has subtasks)
        if current_task.subtasks:
            incomplete_subtasks = [st for st in current_task.subtasks if not st.completed]
            if incomplete_subtasks:
                return {
                    "success": False,
                    "error": f"Cannot advance: {len(incomplete_subtasks)} subtasks incomplete",
                    "incomplete_subtasks": [st.id for st in incomplete_subtasks]
                }

        # Mark current task complete
        current_task.status = TaskStatus.COMPLETED
        current_task.completion_reasoning = completion_reasoning
        current_task.key_findings = key_findings

        # Get current task index
        task_index = next(
            (i for i, t in enumerate(self.todo_list.tasks) if t.id == current_task.id),
            None
        )

        if task_index is None:
            return {"success": False, "error": "Could not find task index"}

        # Check if there's a next task
        if task_index + 1 < len(self.todo_list.tasks):
            # Advance to next main task
            next_task = self.todo_list.tasks[task_index + 1]
            self.current_main_task_id = next_task.id
            next_task.status = TaskStatus.IN_PROGRESS

            # If next task has subtasks, set first as current
            if next_task.subtasks:
                self.current_subtask_id = next_task.subtasks[0].id
            else:
                self.current_subtask_id = None

            return {
                "success": True,
                "message": f"Advanced to task {next_task.id}",
                "old_task": {
                    "id": current_task.id,
                    "completed": True,
                    "key_findings": key_findings
                },
                "new_task": {
                    "id": next_task.id,
                    "description": next_task.description,
                    "has_subtasks": len(next_task.subtasks) > 0,
                    "total_subtasks": len(next_task.subtasks)
                },
                "remaining_tasks": len(self.todo_list.tasks) - (task_index + 1)
            }
        else:
            # No more tasks - all complete!
            self.current_main_task_id = None
            self.current_subtask_id = None

            return {
                "success": True,
                "message": "All main tasks completed! Ready for final answer.",
                "old_task": {
                    "id": current_task.id,
                    "completed": True,
                    "key_findings": key_findings
                },
                "new_task": None,
                "all_tasks_complete": True
            }

    def record_thinking(self, thinking_text: str) -> None:
        """Record agent's thinking in current subtask (THINK phase)."""
        subtask = self._get_current_subtask()
        if subtask:
            subtask.thinking_notes.append(thinking_text)

    def record_observation(self, observation_text: str) -> None:
        """Record agent's observation in current subtask (OBSERVE phase)."""
        subtask = self._get_current_subtask()
        if subtask:
            subtask.observations.append(observation_text)

    def record_reasoning(self, reasoning_text: str) -> None:
        """Record agent's reasoning in current subtask (REASON phase)."""
        subtask = self._get_current_subtask()
        if subtask:
            subtask.reasoning_log.append(reasoning_text)

    def increment_tool_calls(self, count: int = 1) -> None:
        """Increment tool call counter for current subtask (ACT phase)."""
        subtask = self._get_current_subtask()
        if subtask:
            subtask.tool_calls_made += count

    def get_reasoning_density(self) -> float:
        """
        Calculate reasoning density across all completed subtasks.

        Reasoning density = reasoning iterations / total iterations
        Where:
        - Reasoning iterations = thinking + reasoning entries
        - Total iterations = thinking + tool calls + observations + reasoning

        Target: 30-40%
        """
        total_reasoning = 0
        total_iterations = 0

        for task in self.todo_list.tasks:
            for subtask in task.subtasks:
                reasoning_count = len(subtask.thinking_notes) + len(subtask.reasoning_log)
                iteration_count = (
                    len(subtask.thinking_notes) +
                    subtask.tool_calls_made +
                    len(subtask.observations) +
                    len(subtask.reasoning_log)
                )

                total_reasoning += reasoning_count
                total_iterations += iteration_count

        if total_iterations == 0:
            return 0.0

        return total_reasoning / total_iterations

    def _get_current_main_task(self) -> Optional[MainTask]:
        """Get the current main task."""
        if self.current_main_task_id is None:
            return None
        return self.todo_list.get_task_by_id(self.current_main_task_id)

    def _get_current_subtask(self) -> Optional[SubTask]:
        """Get the current subtask."""
        if self.current_subtask_id is None or self.current_main_task_id is None:
            return None
        return self.todo_list.get_subtask_by_id(self.current_main_task_id, self.current_subtask_id)

    def _get_overall_progress(self) -> Dict[str, Any]:
        """Calculate overall progress through the plan."""
        completed = sum(1 for task in self.todo_list.tasks if task.status == TaskStatus.COMPLETED)
        total = len(self.todo_list.tasks)
        percentage = (completed / total * 100) if total > 0 else 0

        return {
            "main_tasks_completed": completed,
            "main_tasks_total": total,
            "percentage": round(percentage, 1)
        }

    def get_task_state_for_persistence(self) -> Dict[str, Any]:
        """
        Get complete task state for saving to disk.

        Returns the full TodoList as dict with all reasoning data.
        Uses mode='json' to properly serialize enums.
        """
        return {
            "current_main_task_id": self.current_main_task_id,
            "current_subtask_id": self.current_subtask_id,
            "todo_list": self.todo_list.model_dump(mode='json'),  # mode='json' converts enums to strings
            "reasoning_density": self.get_reasoning_density(),
            "progress": self._get_overall_progress()
        }
