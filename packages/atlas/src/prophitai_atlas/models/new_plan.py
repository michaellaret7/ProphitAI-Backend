"""Plan models for agent task execution."""

from enum import Enum
from typing import List
from pydantic import BaseModel, Field

class TaskStatus(str, Enum):
    """Status of a task or subtask in a plan."""

    NOT_STARTED = "not started"
    IN_PROGRESS = "in progress"
    COMPLETE = "complete"

class PlanTask(BaseModel):
    id: str = Field(..., description="Task identifier, e.g., '1'")
    step: int = Field(..., description="Step number — tasks sharing the same step run in parallel")
    description: str = Field(..., description="What the task will do")
    status: TaskStatus = Field(default=TaskStatus.NOT_STARTED, description="Current status of the task")

class Plan(BaseModel):
    tasks: List[PlanTask] = Field(default_factory=list, description="Top-level task list")
