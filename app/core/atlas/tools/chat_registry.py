"""
Chat Tool Registry - Registers agent-type-specific tools for chat agents.

AgentBase already registers default tools (calculator, think).
This registry adds ONLY the agent-type-specific tools on top:
- macro_research: Adds macro research search tool
- earnings_call: Adds earnings call search tool
- general: No additional tools (just defaults)
"""

from typing import TYPE_CHECKING

from app.core.atlas.tools.foundry.macro_research import MACRO_RESEARCH_SEARCH_TOOL
from app.core.atlas.tools.foundry.earnings_calls import EARNINGS_CALL_SEARCH_TOOL

if TYPE_CHECKING:
    from app.core.atlas.agents.base import AgentBase


def register_tools_for_agent_type(agent: "AgentBase", agent_type: str) -> None:
    """Register agent-type-specific tools.

    Called ONCE when a chat session is created. Default tools (calculator, think)
    are already registered by AgentBase. This adds only the specialized tools.

    Args:
        agent: The agent instance to register tools on.
        agent_type: The type of agent determining which tools to add.
            - "macro_research": Adds macro research search
            - "earnings_call": Adds earnings call search
            - "general": No additional tools
    """
    if agent_type == "macro_research":
        agent.add_tool(**MACRO_RESEARCH_SEARCH_TOOL)
    elif agent_type == "earnings_call":
        agent.add_tool(**EARNINGS_CALL_SEARCH_TOOL)
