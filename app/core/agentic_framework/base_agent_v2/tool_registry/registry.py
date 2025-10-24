"""Tool registration for Base Agent V2.

This module provides tool registration functions for agents.
Simplified from V1 to focus on essential tools without heavy task management overhead.
"""

from typing import Any
import yaml

# External tool imports
from app.core.agentic_framework.tool_lib.base_tools.search_engine_tool import AgentSearchEngine
from app.core.agentic_framework.tool_lib.base_tools import calculator


def register_base_tools(agent: Any) -> None:
    """
    Register core base tools available to all V2 agents.

    Includes:
    - free_search: Web search capability
    - calculator: Math calculations (last resort)
    - create_structured_plan: Planning tool
    - episodic_remember/recall: Memory tools

    Does NOT include old V1 task management tools - those are replaced by
    V2-specific task control tools (registered separately).
    """

    # free_search
    agent.add_tool(
        name="free_search",
        description=(
            "The free_search tool searches the web. Provide a detailed query that will be "
            "sent to an external search engine."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Detailed query for the search engine.",
                }
            },
            "required": ["query"],
        },
        function=lambda query, **kwargs: AgentSearchEngine().perplexity_free_search(query),
    )

    # calculator
    agent.add_tool(
        name="calculator",
        description=(
            "LAST RESORT TOOL - ONLY use when absolutely necessary for complex mathematical calculations "
            "that cannot be done with other tools. Most metrics are already calculated in factor tools. "
            "Provide the expression string and the tool returns the result."
        ),
        parameters={
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Expression to evaluate."}
            },
            "required": ["expression"],
        },
        function=lambda expression, **kwargs: calculator.calculator(expression),
    )

    # structured_planning
    agent.add_tool(
        name="create_structured_plan",
        description=(
            "Create a comprehensive structured plan using the agent's context. "
            "Returns a TodoList with main tasks and subtasks for accomplishing the user's goal. "
            "The plan will have comprehensive analytical structure (5-10 tasks, 10-20+ subtasks for complex work) "
            "with tasks as analytical objectives, not tool calls or meta-work."
        ),
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        function=lambda **kwargs: agent.planning_tool.create_plan_from_agent(),
    )

    # Episodic memory tools (if enabled)
    if getattr(agent, "use_episodic_memory", False) and getattr(agent, "episodic", None) is not None:

        def episodic_remember_impl(title, event, context=None, outcome=None, tags=None, meta=None, **kwargs):
            """Append an episodic memory entry."""
            try:
                entry = agent.episodic.append(
                    title=title,
                    event=event,
                    context=context,
                    outcome=outcome,
                    tags=tags,
                    meta=meta
                )
                result = {
                    "success": True,
                    "message": "Memory entry appended successfully",
                    "entry": {
                        "title": entry.get("title"),
                        "event": entry.get("event"),
                        "timestamp": entry.get("timestamp")
                    }
                }
                return yaml.dump(result, default_flow_style=False, sort_keys=False)
            except Exception as e:
                result = {
                    "success": False,
                    "error": str(e),
                    "message": "Failed to append memory entry"
                }
                return yaml.dump(result, default_flow_style=False, sort_keys=False)

        agent.add_tool(
            name="episodic_remember",
            description=(
                "Append an episodic memory entry. Use for key milestones or facts you may want to recall later. "
                "Returns YAML with success status."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Short human-readable label"},
                    "event": {"type": "string", "description": "Event description"},
                    "context": {"type": "object", "description": "Arbitrary context/details"},
                    "outcome": {"type": ["string", "object"], "description": "Outcome snapshot"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for retrieval"},
                    "meta": {"type": "object", "description": "Extra metadata"}
                },
                "required": ["title", "event"],
            },
            function=episodic_remember_impl,
        )

        def episodic_recall_impl(query=None, tags=None, since=None, limit=20, **kwargs):
            """Recall episodic memories."""
            try:
                entries = agent.episodic.recall(query=query, tags=tags, since=since, limit=limit)
                result = {
                    "success": True,
                    "message": f"Retrieved {len(entries)} memory entries",
                    "count": len(entries),
                    "entries": entries
                }
                return yaml.dump(result, default_flow_style=False, sort_keys=False)
            except Exception as e:
                result = {
                    "success": False,
                    "error": str(e),
                    "message": "Failed to recall memory entries"
                }
                return yaml.dump(result, default_flow_style=False, sort_keys=False)

        agent.add_tool(
            name="episodic_recall",
            description=(
                "Recall episodic memories by keyword, tags, or since a timestamp. Returns most recent first. "
                "Returns YAML with success status."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Keyword to search (optional)"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags filter (optional)"},
                    "since": {"type": "string", "description": "ISO timestamp to filter newer entries (optional)"},
                    "limit": {"type": "integer", "description": "Max entries to return (default 20)"}
                },
                "required": [],
            },
            function=episodic_recall_impl,
        )


def register_v2_task_control_tools(agent: Any) -> None:
    """
    Register V2-specific task control tools.

    These tools give the agent control over task progression:
    - get_current_task_info: See current task/subtask context
    - advance_to_next_subtask: Manually advance to next subtask
    - advance_to_next_main_task: Manually advance to next main task

    NOTE: These will be implemented in Phase 3.3 (Task Control Tools).
    This is a placeholder function to be filled in later.
    """
    # TODO: Implement in Phase 3.3
    # Will import from base_agent_v2.tasks.tools
    pass
