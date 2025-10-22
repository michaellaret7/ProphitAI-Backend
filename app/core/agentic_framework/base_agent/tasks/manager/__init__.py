"""TaskManager with composition-based architecture.

This module provides the main TaskManager class that composes specialized
components for different task management responsibilities.

Architecture:
- Core: State management and data access
- Status: Task/subtask status updates
- Evidence: Evidence and observation tracking
- Progress: Progress reporting and summaries
- Advanced: Add/remove/fail/retry operations
- Persistence: State save/load operations
"""

from .task_manager import TaskManager

__all__ = ['TaskManager']
