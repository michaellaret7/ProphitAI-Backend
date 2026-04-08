"""Deferred tools utilities — builds description text and registry dicts from @agent_tool functions.

Takes a flat list of @agent_tool-decorated callables, groups them by category,
and returns the data structures that register_tools needs.
"""

from typing import Any, Callable, Dict, List, NamedTuple


class DeferredToolsData(NamedTuple):
    """Data bundle for deferred tool registration.

    Attributes:
        description: Formatted text block listing all tools grouped by category.
        tool_registry: Category name -> list of @agent_tool-decorated callables.
        all_tools: Flat dict of tool_name -> tool dict (.tool attribute).
    """

    description: str
    tool_registry: Dict[str, List[Callable]]
    all_tools: Dict[str, Dict[str, Any]]


def build_deferred_tools_data(tools: List[Callable]) -> DeferredToolsData:
    """Build description text and registry dicts from a list of @agent_tool-decorated callables.

    Groups tools by their `.category` attribute, extracts first-sentence descriptions,
    and returns everything needed for deferred tool registration.

    Args:
        tools: List of @agent_tool-decorated callables.

    Returns:
        DeferredToolsData with description, tool_registry, and all_tools.
    """
    tool_registry: Dict[str, List[Callable]] = {}
    all_tools: Dict[str, Dict[str, Any]] = {}

    for func in tools:
        if not hasattr(func, "tool"):
            raise ValueError(
                f"'{getattr(func, '__name__', func)}' is not decorated with @agent_tool"
            )
        category = getattr(func, "category", None) or "uncategorized"
        tool_registry.setdefault(category, []).append(func)
        all_tools[func.tool["name"]] = func.tool

    # Reason: Build a description block listing all tools grouped by category
    sections: List[str] = []
    for category in sorted(tool_registry.keys()):
        lines = [f"**{category}**"]
        for func in tool_registry[category]:
            tool_name = func.tool["name"]
            description = _first_sentence(func.tool.get("description", ""))
            lines.append(f"  - `{tool_name}`: {description}")
        sections.append("\n".join(lines))

    catalogue_text = "\n\n".join(sections)

    description = (
        "<deferred_tools>\n"
        "## Available Tools (call `register_tools` to load before use)\n\n"
        f"{catalogue_text}\n"
        "</deferred_tools>"
    )

    return DeferredToolsData(
        description=description,
        tool_registry=tool_registry,
        all_tools=all_tools,
    )


# ================================
# --> Helper funcs
# ================================

def _first_sentence(text: str) -> str:
    """Extract the first sentence from a description string."""
    text = text.strip()
    # Reason: split on period followed by whitespace or end-of-string
    for i, char in enumerate(text):
        if char == "." and (i + 1 >= len(text) or text[i + 1] in (" ", "\n")):
            return text[: i + 1]
    return text
