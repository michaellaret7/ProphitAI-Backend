"""Task models using Pydantic for structured planning in Base Agent V2.

Enhanced from V1 with reasoning-focused fields to support:
- Think → Act → Observe → Reason cycle
- High reasoning density tracking
- Agent autonomy and decision-making
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal
from enum import Enum
import re

class TaskStatus(Enum):
    """Task status states."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"

class SubTask(BaseModel):
    """Subtask within a main task - represents a specific analytical checkpoint."""

    id: str = Field(
        ...,
        description="Format: number+letter (e.g., '1a', '2b', '5c')",
        examples=["1a", "2b", "5c"]
    )
    description: str = Field(
        ...,
        description="Analytical objective (WHAT to analyze, not HOW or which tools)"
    )
    completed: bool = False

    # REASONING CYCLE FIELDS (Think → Act → Observe → Reason)
    thinking_notes: List[str] = Field(
        default_factory=list,
        description="Agent's thinking before taking action - the THINK phase"
    )
    observations: List[str] = Field(
        default_factory=list,
        description="Agent's factual observations from tool results - the OBSERVE phase"
    )
    reasoning_log: List[str] = Field(
        default_factory=list,
        description="Agent's reasoning and synthesis - the REASON phase"
    )

    # ACTIVITY TRACKING
    tool_calls_made: int = Field(
        default=0,
        description="Number of tool calls made during this subtask (tracks ACT phase)"
    )

    @field_validator('id')
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        """Ensure subtask ID follows pattern: number+letter (1a, 2b, 5c)"""
        if not re.match(r'^\d+[a-z]$', v):
            raise ValueError(f"Subtask ID must be number+letter (e.g., '1a', '2b', '5c'), got: {v}")
        return v

class MainTask(BaseModel):
    """Main task containing one or more analytical phases (subtasks)."""

    id: int  # e.g., 1, 2, 3
    description: str = Field(
        ...,
        description="High-level analytical objective for this task"
    )
    status: TaskStatus = TaskStatus.PENDING
    subtasks: List[SubTask] = Field(default_factory=list)

    # TASK-LEVEL REASONING AND SYNTHESIS
    reasoning_summary: str = Field(
        default="",
        description="Summary of agent's reasoning throughout this task"
    )
    key_findings: str = Field(
        default="",
        description="Main insights and discoveries from this task"
    )
    completion_reasoning: str = Field(
        default="",
        description="Agent's reasoning for why this task is complete (provided when advancing)"
    )

class TodoList(BaseModel):
    """Collection of main tasks representing the agent's execution plan."""

    tasks: List[MainTask] = Field(default_factory=list)

    def add_main_task(self, task_id: int, description: str) -> MainTask:
        """Add a new main task to the plan."""
        task = MainTask(
            id=task_id,
            description=description
        )
        self.tasks.append(task)
        return task

    def add_subtask(self, main_task_id: int, subtask_id: str, description: str) -> Optional[SubTask]:
        """Add a subtask to an existing main task."""
        for task in self.tasks:
            if task.id == main_task_id:
                subtask = SubTask(id=subtask_id, description=description)
                task.subtasks.append(subtask)
                return subtask
        return None

    def get_task_by_id(self, task_id: int) -> Optional[MainTask]:
        """Get a main task by its ID."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def get_subtask_by_id(self, main_task_id: int, subtask_id: str) -> Optional[SubTask]:
        """Get a subtask by main task ID and subtask ID."""
        task = self.get_task_by_id(main_task_id)
        if task:
            for subtask in task.subtasks:
                if subtask.id == subtask_id:
                    return subtask
        return None


