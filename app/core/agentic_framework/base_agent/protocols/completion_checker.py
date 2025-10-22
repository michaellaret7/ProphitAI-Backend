"""CompletionChecker Protocol for task completion validation.

Enables dependency inversion: Executor depends on CompletionChecker protocol,
not concrete validator implementation.
"""

from typing import Protocol
from ..tasks.models import MainTask, SubTask


class CompletionChecker(Protocol):
    """Protocol for task completion validation.

    Any class implementing these methods satisfies this protocol,
    enabling dependency injection and testing with mocks.

    IMPORTANT: Implementations should return simple boolean values,
    not confidence scores or complex tuples.
    """

    def is_subtask_complete(self, subtask: SubTask) -> bool:
        """Check if a subtask is complete.

        Args:
            subtask: The SubTask to validate

        Returns:
            True if subtask is complete, False otherwise
        """
        ...

    def is_main_task_complete(self, task: MainTask) -> bool:
        """Check if a main task is complete.

        Args:
            task: The MainTask to validate

        Returns:
            True if task is complete, False otherwise
        """
        ...
