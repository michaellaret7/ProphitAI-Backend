"""Simple Base Agent V2 - Phase 1

Minimal autonomous agent framework with:
- SimpleAgent: Main orchestrator
- ExecutionLoop: ReAct iteration loop
- ToolHandler: Tool execution and formatting

Total: ~200 lines, clean separation of concerns.
"""

from app.core.agentic_framework.base_agent_v2.agent import SimpleAgent
from app.core.agentic_framework.base_agent_v2.execution.execution_loop import ExecutionLoop
from app.core.agentic_framework.base_agent_v2.execution.tool_handler import ToolHandler

__all__ = ['SimpleAgent', 'ExecutionLoop', 'ToolHandler']
