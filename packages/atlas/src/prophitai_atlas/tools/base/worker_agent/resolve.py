"""Tool resolution — resolves tool name strings to @agent_tool-decorated callables."""

from typing import Callable, Dict, Iterable, List


def resolve_tools_by_name(
    tool_functions: List[Callable],
    tool_names: Iterable[str],
) -> List[Callable]:
    """Resolve tool name strings to their @agent_tool-decorated callable objects.

    Builds a name -> callable lookup from the full tool list, then resolves
    each requested name. Order of the returned list matches the input order.

    Args:
        tool_functions: Full list of @agent_tool-decorated callables (e.g., ALL_TOOL_FUNCTIONS).
        tool_names: Tool name strings to resolve (e.g., ["ticker_performance", "ticker_risk"]).

    Returns:
        List of matching @agent_tool-decorated callables.

    Raises:
        ValueError: If any requested name is not found in tool_functions.
    """
    # Reason: Build lookup once, O(1) per resolution
    name_to_func: Dict[str, Callable] = {}

    for func in tool_functions:
        tool_dict = getattr(func, "tool", None)

        if tool_dict is None:
            continue

        name_to_func[tool_dict["name"]] = func

    resolved: List[Callable] = []
    missing: List[str] = []

    for name in tool_names:
        func = name_to_func.get(name)

        if func is None:
            missing.append(name)
        else:
            resolved.append(func)

    if missing:
        available = sorted(name_to_func.keys())

        raise ValueError(
            f"Unknown tool name(s): {missing}. "
            f"Available tools: {available}"
        )

    return resolved
