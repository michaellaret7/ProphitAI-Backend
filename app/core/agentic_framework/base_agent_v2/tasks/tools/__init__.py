"""
Task control tools - Agent-driven task progression

These tools allow the agent to control its own workflow:

- task_info.py: get_current_task_info()
  - Agent can call to see where they are in the plan
  - Returns current task, subtask, and progress

- advancement.py: Manual advancement tools
  - advance_to_next_subtask(completion_reasoning, key_findings)
  - advance_to_next_main_task(completion_reasoning, key_findings)
  - Agent must explicitly call to progress
  - Must provide reasoning for why complete

These tools are CRITICAL to the V2 philosophy:
- Agent drives workflow (not automatic system)
- Agent decides when ready to advance
- Agent provides reasoning for completion
"""

from .task_info import get_current_task_info, GET_CURRENT_TASK_INFO_SCHEMA
from .advancement import (
    advance_to_next_subtask,
    advance_to_next_main_task,
    ADVANCE_SUBTASK_SCHEMA,
    ADVANCE_MAIN_TASK_SCHEMA
)

__all__ = [
    "get_current_task_info",
    "GET_CURRENT_TASK_INFO_SCHEMA",
    "advance_to_next_subtask",
    "advance_to_next_main_task",
    "ADVANCE_SUBTASK_SCHEMA",
    "ADVANCE_MAIN_TASK_SCHEMA"
]
