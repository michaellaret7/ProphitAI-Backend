"""Dynamic tool registration tool for the ChatAgent.

Allows the LLM to load tool categories or individual tools on demand,
rather than having all ~55 tools registered at init.
"""

from typing import Annotated, Any, List, Optional

from app.core.atlas.tools.decorator import Schema, agent_tool
from app.core.atlas.tools.responses import success_response, error_response
from app.core.atlas.tools.registry import (
    TOOL_REGISTRY,
    ALL_TOOLS,
)


# ================================
# --> Tool
# ================================

@agent_tool(name="register_tools")
def register_tools(
    categories: Annotated[
        Optional[list[str]],
        Schema({
            "type": "array",
            "description": "Register all tools in these categories at once.",
            "items": {"type": "string", "enum": sorted(TOOL_REGISTRY.keys())},
            "default": None,
        }),
    ] = None,
    tools: Annotated[
        Optional[list[str]],
        Schema({
            "type": "array",
            "description": "Register individual tools by name.",
            "items": {"type": "string", "enum": sorted(ALL_TOOLS.keys())},
            "default": None,
        }),
    ] = None,
    _agent: Optional[Any] = None,
) -> str:
    """Register additional tools for this conversation. Call this before using tools that aren't in your pre-registered set.

    You start with a small set of pre-registered tools. Use this tool to load
    additional categories or individual tools on demand. At least one of
    `categories` or `tools` must be provided.

    Args:
        categories: Register all tools in these categories at once.
        tools: Register individual tools by name.
    """
    if not categories and not tools:
        return error_response(
            "At least one of 'categories' or 'tools' must be provided. "
            f"Available categories: {sorted(TOOL_REGISTRY.keys())}"
        )

    if _agent is None:
        return error_response("Internal error: _agent not bound.")

    newly_registered: List[str] = []
    already_loaded: List[str] = []
    invalid: List[str] = []

    # Reason: Collect all tool functions to register from requested categories
    if categories:
        for cat in categories:
            if cat not in TOOL_REGISTRY:
                invalid.append(f"category:{cat}")
                continue
            for func in TOOL_REGISTRY[cat]:
                tool_name = func.tool["name"]
                if tool_name in _agent.tool_functions:
                    already_loaded.append(tool_name)
                else:
                    _agent.add_tool(**func.tool)
                    newly_registered.append(tool_name)

    # Reason: Register individual tools by name
    if tools:
        for tool_name in tools:
            if tool_name not in ALL_TOOLS:
                invalid.append(f"tool:{tool_name}")
                continue
            if tool_name in _agent.tool_functions:
                already_loaded.append(tool_name)
            else:
                _agent.add_tool(**ALL_TOOLS[tool_name])
                newly_registered.append(tool_name)

    result = {}
    if newly_registered:
        result["newly_registered"] = newly_registered
    if already_loaded:
        result["already_loaded"] = already_loaded
    if invalid:
        result["invalid"] = invalid
        result["valid_categories"] = sorted(TOOL_REGISTRY.keys())
        result["valid_tools"] = sorted(ALL_TOOLS.keys())

    return success_response(result)
