"""Dynamic tool registration tool for agents.

Allows the LLM to load tool categories or individual tools on demand,
rather than having all tools registered at init.

This is a framework tool — it reads from the agent's deferred tools data
which is populated by the caller (e.g., packages/tools or projects/api).
"""

from typing import Any, Dict, List, Optional, Callable

from prophitai_atlas.tools.responses import success_response, error_response


# ==============================================================================
# --> Static tool schema
# ==============================================================================

REGISTER_TOOLS_TOOL = {
    "name": "register_tools",
    "description": (
        "Register tools for this conversation. Call this before using "
        "tools that aren't in your pre-registered set. You start with a small set "
        "of pre-registered tools. Use this tool to load additional categories or "
        "individual tools on demand. At least one of `categories` or `tools` must "
        "be provided."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "categories": {
                "type": "array",
                "description": "Register all tools in these categories at once.",
                "items": {"type": "string"},
            },
            "tools": {
                "type": "array",
                "description": "Register individual tools by name.",
                "items": {"type": "string"},
            },
        },
        "additionalProperties": False,
    },
}


def register_tools_fn(
    tool_registry: Dict[str, List[Callable]],
    all_tools: Dict[str, Dict[str, Any]],
    _agent: Any,
    categories: Optional[List[str]] = None,
    tools: Optional[List[str]] = None,
) -> str:
    """Register additional tools for this conversation.

    Args:
        tool_registry: Category -> list of @agent_tool-decorated functions (pre-bound).
        all_tools: Flat dict of tool_name -> tool dict (pre-bound).
        _agent: The agent instance (pre-bound).
        categories: Register all tools in these categories at once.
        tools: Register individual tools by name.
    """
    if not categories and not tools:
        return error_response(
            "At least one of 'categories' or 'tools' must be provided. "
            f"Available categories: {sorted(tool_registry.keys())}"
        )

    newly_registered: List[str] = []
    already_loaded: List[str] = []
    invalid: List[str] = []

    # Reason: Collect all tool functions to register from requested categories
    if categories:
        for cat in categories:
            if cat not in tool_registry:
                invalid.append(f"category:{cat}")
                continue
            for func in tool_registry[cat]:
                tool_name = func.tool["name"]
                if tool_name in _agent.tool_functions:
                    already_loaded.append(tool_name)
                else:
                    _agent.add_tool(**func.tool)
                    newly_registered.append(tool_name)

    # Reason: Register individual tools by name
    if tools:
        for tool_name in tools:
            if tool_name not in all_tools:
                invalid.append(f"tool:{tool_name}")
                continue
            if tool_name in _agent.tool_functions:
                already_loaded.append(tool_name)
            else:
                _agent.add_tool(**all_tools[tool_name])
                newly_registered.append(tool_name)

    result = {}
    if newly_registered:
        result["newly_registered"] = newly_registered
    if already_loaded:
        result["already_loaded"] = already_loaded
    if invalid:
        result["invalid"] = invalid
        result["valid_categories"] = sorted(tool_registry.keys())
        result["valid_tools"] = sorted(all_tools.keys())

    return success_response(result)
