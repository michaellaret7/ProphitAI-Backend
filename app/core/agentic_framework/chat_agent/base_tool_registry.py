"""ChatAgent tool registration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.agentic_framework.tool_lib.base_tools.calculator import (
    calculator,
    CALCULATOR_DESCRIPTION,
    CALCULATOR_PARAMETERS,
)
from app.core.agentic_framework.tool_lib.base_tools.think import (
    think,
    THINK_DESCRIPTION,
    THINK_PARAMETERS,
)
from app.core.agentic_framework.tool_lib.foundry_tools.earnings_calls import (
    EARNINGS_CALL_SEARCH_TOOL,
)
from app.core.agentic_framework.tool_lib.foundry_tools.macro_research import (
    MACRO_RESEARCH_SEARCH_TOOL,
)

if TYPE_CHECKING:
    from .agent import ChatAgent


def register_chat_tools(agent: ChatAgent) -> None:
    """Register tools for chat interactions."""

    agent.add_tool(
        name="calculator",
        description=CALCULATOR_DESCRIPTION,
        parameters=CALCULATOR_PARAMETERS,
        function=lambda expression, **kwargs: calculator(expression),
    )

    agent.add_tool(
        name="think",
        description=THINK_DESCRIPTION,
        parameters=THINK_PARAMETERS,
        function=lambda thought, **kwargs: think(thought=thought),
    )
