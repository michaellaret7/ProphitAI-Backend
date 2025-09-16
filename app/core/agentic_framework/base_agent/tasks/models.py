"""Task models using Pydantic for structured planning in BaseAgent."""

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
    id: str = Field(
        ..., 
        description="Format: number+letter (e.g., '1a', '2b', '5c')",
        examples=["1a", "2b", "5c"]
    )
    description: str
    completed: bool = False
    completion_evidence: List[str] = []
    observations: List[str] = []
    
    @field_validator('id')
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        """Ensure subtask ID follows pattern: number+letter (1a, 2b, 5c)"""
        if not re.match(r'^\d+[a-z]$', v):
            raise ValueError(f"Subtask ID must be number+letter (e.g., '1a', '2b', '5c'), got: {v}")
        return v

class MainTask(BaseModel):
    id: int  # e.g., 1, 2, 3
    description: str
    status: TaskStatus = TaskStatus.PENDING
    subtasks: List[SubTask] = []
    predicted_tool_use: List[str] = []  # All tools for this main task
    completion_evidence: List[str] = []
    observations: List[str] = []

class TodoList(BaseModel):
    tasks: List[MainTask] = []
    
    def add_main_task(self, task_id: int, description: str, predicted_tools: List[str] = None) -> MainTask:
        task = MainTask(
            id=task_id, 
            description=description,
            predicted_tool_use=predicted_tools or []
        )
        self.tasks.append(task)
        return task
    
    def add_subtask(self, main_task_id: int, subtask_id: str, description: str) -> Optional[SubTask]:
        for task in self.tasks:
            if task.id == main_task_id:
                subtask = SubTask(id=subtask_id, description=description)
                task.subtasks.append(subtask)
                return subtask
        return None


