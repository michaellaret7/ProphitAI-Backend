"""
Task management for Base Agent V2

This module provides LIGHTWEIGHT task tracking and control:

- models.py: Enhanced Pydantic models (adapted from V1)
  - TodoList, MainTask, SubTask, TaskStatus
  - NEW fields: reasoning_log, observations, thinking_notes
  - Captures agent's reasoning at each phase

- tracker.py: NEW - Lightweight task tracking
  - Simple tracking of current task/subtask
  - NO automatic advancement
  - Agent controls progression via tools

- tools/: NEW - Task control tools for agent
  - task_info.py: Get current task context
  - advancement.py: Manual task/subtask advancement tools

Key principle: Agent is in control. Tasks advance ONLY when agent explicitly calls
the advancement tools with reasoning for completion.
"""

from .models import TodoList, MainTask, SubTask, TaskStatus
from .tracker import LightweightTaskTracker

__all__ = [
    "TodoList",
    "MainTask",
    "SubTask",
    "TaskStatus",
    "LightweightTaskTracker"
]
