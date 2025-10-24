"""
Execution engine for Base Agent V2

This module handles the core execution loop and iteration management:

- reasoning_loop.py: NEW - Core execution loop with reasoning cycle
  - Think → Act → Observe → Reason pattern
  - Reasoning prompts at each iteration
  - NO automatic task advancement
  - High reasoning density focus

- tool_handler.py: Tool execution (adapted from V1)
  - Execute tool calls
  - Handle errors gracefully
  - Format results consistently

- iteration_tracker.py: NEW - Simple iteration tracking
  - Record iteration types (thinking, action, observation, reasoning)
  - Calculate reasoning density
  - Track progress without heavy overhead

Key difference from V1: Agent drives the workflow, not automatic systems.
"""

from .iteration_tracker import IterationTracker, Iteration
from .tool_handler import ToolHandler, ToolResult
from .reasoning_loop import ReasoningExecutionLoop

__all__ = [
    "IterationTracker",
    "Iteration",
    "ToolHandler",
    "ToolResult",
    "ReasoningExecutionLoop"
]
