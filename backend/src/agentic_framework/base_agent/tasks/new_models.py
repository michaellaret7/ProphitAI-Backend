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
    completed: bool = False
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


import instructor
from openai import OpenAI

# Patch OpenAI client with instructor
client = instructor.from_openai(OpenAI())

# Direct Pydantic model output
todo_list = client.chat.completions.create(
    model="gpt-5-nano",
    messages=[
        {
            "role": "system",
            "content": "Format subtask IDs as: main_task_number + letter. Examples: 1a, 1b, 2a, 3a, 5a, 5b, 5c. NOT '5.1' or just 'a'"
        },
        {"role": "user", "content": "Create a todo list for implementing OAuth, use subtasks and create fake tools for the tool use section. Make sure to structure it as Big main tasks and then the small subtasks to complete the large/main task"}
    ],
    response_model=TodoList,  # Pass Pydantic model directly
    max_retries=2  # Retry if validation fails
)

# todo_list is already a validated TodoList instance
json_output = todo_list.model_dump_json(indent=2)
print("\n=== JSON Output ===")
print(json_output)