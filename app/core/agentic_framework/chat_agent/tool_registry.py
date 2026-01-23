"""ChatAgent tool registration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.core.agentic_framework.tool_lib.base_tools.calculator import calculator
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


def _calculator_wrapper(expression: str, **kwargs: Any) -> str:
    """Wrapper for calculator."""
    return calculator(expression=expression)


def _think_wrapper(thought: str, **kwargs: Any) -> str:
    """Wrapper for think tool."""
    return think(thought=thought)


def register_chat_tools(agent: ChatAgent) -> None:
    """Register tools for chat interactions."""
    agent.add_tool(**EARNINGS_CALL_SEARCH_TOOL)
    agent.add_tool(**MACRO_RESEARCH_SEARCH_TOOL)

    agent.add_tool(
        name="calculator",
        description="Evaluate mathematical expressions. Supports basic operations (+, -, *, /), "
                    "parentheses, and functions (sqrt, sin, cos, tan, log, ln, pi, e).",
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate"
                }
            },
            "required": ["expression"]
        },
        function=_calculator_wrapper,
    )

    agent.add_tool(
        name="think",
        description=THINK_DESCRIPTION,
        parameters=THINK_PARAMETERS,
        function=_think_wrapper,
    )
