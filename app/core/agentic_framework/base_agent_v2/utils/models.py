"""Print mode configuration for agent output verbosity.

Three levels of output verbosity:
- production: Minimal output (only tool calls)
- verbose: Standard output (iteration status, tool calls, results)
- debug: Maximum output (full LLM responses + all verbose output)
"""

from enum import Enum
from pydantic import BaseModel
from typing import List
from typing import List
from pydantic import BaseModel, Field

# Print mode models
class PrintMode(str, Enum):
    """Agent print mode for controlling output verbosity."""

    PRODUCTION = "production"
    VERBOSE = "verbose"
    DEBUG = "debug"

# Plan status enum
class TaskStatus(str, Enum):
    """Status of a task or subtask in a plan."""

    NOT_STARTED = "not started"
    IN_PROGRESS = "in progress"
    COMPLETE = "complete"

# Plan models
class PlanSubtask(BaseModel):
    id: str = Field(..., description="Subtask identifier, e.g., '1a'")
    description: str = Field(..., description="What the subtask will do")
    status: TaskStatus = Field(default=TaskStatus.NOT_STARTED, description="Current status of the subtask")
    work_summary: str = Field(default="", description="Evidence of work completed for this subtask")


class PlanTask(BaseModel):
    id: str = Field(..., description="Task identifier, e.g., '1'")
    description: str = Field(..., description="What the task will do")
    status: TaskStatus = Field(default=TaskStatus.NOT_STARTED, description="Current status of the task")
    subtasks: List[PlanSubtask] = Field(default_factory=list, description="Nested subtasks")
    work_summary: str = Field(default="", description="Evidence of work completed for this task")


class Plan(BaseModel):
    tasks: List[PlanTask] = Field(default_factory=list, description="Top-level task list")

