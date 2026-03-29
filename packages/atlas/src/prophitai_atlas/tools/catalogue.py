"""ToolCatalogue — builds registry dicts and prompt text from @agent_tool functions.

Takes a flat list of @agent_tool-decorated callables, groups them by category,
and exposes the data structures that register_tools and deploy_worker_agent need.
"""

from typing import Any, Callable, Dict, List


class ToolCatalogue:
    """Organizes @agent_tool-decorated functions into a queryable catalogue.

    Attributes:
        tool_registry: Category name → list of @agent_tool-decorated callables.
        all_tools: Flat dict of tool_name → tool dict (.tool attribute).
    """

    def __init__(self, tools: List[Callable]) -> None:
        self.tool_registry: Dict[str, List[Callable]] = {}
        self.all_tools: Dict[str, Dict[str, Any]] = {}

        for func in tools:
            if not hasattr(func, "tool"):
                raise ValueError(
                    f"'{getattr(func, '__name__', func)}' is not decorated with @agent_tool"
                )
            category = getattr(func, "category", None) or "uncategorized"
            self.tool_registry.setdefault(category, []).append(func)
            self.all_tools[func.tool["name"]] = func.tool

    def build_catalogue_description(self) -> str:
        """Generate prompt text listing every category and its tools.

        Output format (one block per category):
            **category_name**
              - tool_name: First sentence of the tool description.
              - tool_name: First sentence of the tool description.
        """
        sections: List[str] = []

        for category in sorted(self.tool_registry.keys()):
            lines = [f"**{category}**"]
            for func in self.tool_registry[category]:
                tool_name = func.tool["name"]
                description = _first_sentence(func.tool.get("description", ""))
                lines.append(f"  - `{tool_name}`: {description}")
            sections.append("\n".join(lines))

        return "\n\n".join(sections)


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
