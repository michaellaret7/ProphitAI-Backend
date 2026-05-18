"""Tool resolution — resolves tool name strings to @agent_tool-decorated callables."""

from typing import Callable, Dict, Iterable, List

# Reason: These tools are either built-in to WorkerAgent (write_note, web_search,
# web_extract) or orchestrator-only meta-tools (register_tools). LLMs hallucinate
# them into worker tool lists, so we silently drop them instead of erroring.
WORKER_BUILTIN_TOOLS = frozenset({"write_note", "web_search", "web_extract", "register_tools"})


def resolve_tools_by_name(
    tool_functions: List[Callable],
    tool_names: Iterable[str],
) -> List[Callable]:
    """Resolve tool name strings to their @agent_tool-decorated callable objects.

    Builds a name -> callable lookup from the full tool list, then resolves
    each requested name. Unknown tool names are silently dropped — LLMs
    sometimes hallucinate tool names that don't exist in the registry.
    Tools already built into WorkerAgent (write_note, web_search, web_extract)
    and orchestrator-only tools (register_tools) are also silently dropped.

    Args:
        tool_functions: Full list of @agent_tool-decorated callables (e.g., ALL_TOOL_FUNCTIONS).
        tool_names: Tool name strings to resolve (e.g., ["ticker_performance", "ticker_risk"]).

    Returns:
        List of matching @agent_tool-decorated callables.
    """
    # Reason: Build lookup once, O(1) per resolution
    name_to_func: Dict[str, Callable] = {}

    for func in tool_functions:
        tool_dict = getattr(func, "tool", None)

        if tool_dict is None:
            continue

        name_to_func[tool_dict["name"]] = func

    resolved: List[Callable] = []
    dropped: List[str] = []

    for name in tool_names:
        # Reason: Skip tools already built into WorkerAgent or orchestrator-only meta-tools
        if name in WORKER_BUILTIN_TOOLS:
            dropped.append(name)
            continue

        func = name_to_func.get(name)

        if func is None:
            dropped.append(name)
        else:
            resolved.append(func)

    if dropped:
        print(f"[resolve_tools] Dropped invalid/built-in tool names: {dropped}")

    return resolved
