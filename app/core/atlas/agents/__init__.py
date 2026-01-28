"""Agent implementations for the Atlas framework.

Exports:
    AgentBase: Abstract base class for all agents

Future exports (after migration):
    DeepAgent: Complex long-running task execution agent (from base_agent)
    ChatAgent: Lightweight conversational agent (from chat_agent)
"""

from .base import AgentBase

__all__ = ["AgentBase"]
