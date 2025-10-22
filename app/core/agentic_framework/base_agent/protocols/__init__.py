"""Protocols for dependency inversion and structural typing."""

from .task_store import TaskStore
from .task_executor import TaskExecutor
from .completion_checker import CompletionChecker

__all__ = ['TaskStore', 'TaskExecutor', 'CompletionChecker']
