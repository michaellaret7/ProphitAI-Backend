"""Task state persistence operations."""

import json
from datetime import datetime
from .core import TaskManagerCore


class TaskPersistenceManager:
    """Manages task state persistence to disk.

    Responsibilities:
    - Save current task state to JSON
    - Track execution history
    """

    def __init__(self, core: TaskManagerCore):
        """Initialize persistence manager.

        Args:
            core: Core task manager for state access
        """
        self.core = core

    def save_state(self) -> None:
        """Save current task state to JSON file.

        Saves:
        - Current timestamp
        - Structured plan (if exists)
        - Last 50 execution history entries
        """
        state_data = {
            'timestamp': datetime.now().isoformat(),
            'structured_plan': self.core.structured_plan.model_dump(mode='json') if self.core.structured_plan else None,
            'execution_history': self.core.execution_history[-50:]  # Keep last 50 entries
        }

        try:
            with open(self.core.state_path, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            if self.core.verbose:
                print(f"⚠️ Failed to save task state: {e}")
