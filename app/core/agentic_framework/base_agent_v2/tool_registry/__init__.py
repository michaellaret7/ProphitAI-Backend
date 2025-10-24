"""
Tool registry for Base Agent V2

This module manages tool registration and access:

- registry.py: Tool registration system (adapted from V1)
  - register_base_tools(): Core tools (search, calculator, planning, memory)
  - register_v2_task_control_tools(): V2 task control (to be implemented in Phase 3.3)

- reasoning_tools.py: NEW - Reasoning-specific tools (future)
  - Tools that help agent reason
  - Observation formatting tools
  - Pattern detection helpers

Simplified from V1 - removed heavy task management tools, kept essentials.
"""

from .registry import register_base_tools, register_v2_task_control_tools

__all__ = [
    "register_base_tools",
    "register_v2_task_control_tools"
]
