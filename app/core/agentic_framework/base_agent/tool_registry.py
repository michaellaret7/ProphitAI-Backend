from typing import Any
from app.core.agentic_framework.tool_lib.base_tools.task_tools import (
    update_task_status,
    UPDATE_TASK_STATUS_DESCRIPTION,
    UPDATE_TASK_STATUS_PARAMETERS,
    mark_task_complete,
    MARK_TASK_COMPLETE_DESCRIPTION,
    MARK_TASK_COMPLETE_PARAMETERS
)

# Local imports to avoid circular dependencies at module import time
from app.core.agentic_framework.tool_lib.base_tools.search_engine_tool import AgentSearchEngine
from app.core.agentic_framework.tool_lib.base_tools import calculator

def register_base_tools(agent: Any) -> None:
    """
    Register the base tools on the provided agent.

    Notes:
    - Imports are local to avoid circular dependencies.
    - Lambdas capture `agent` and access attributes at call-time.
    """

    search_description = (
        "The free_search tool searches the web. Provide a detailed query that will be "
        "sent to an external search engine."
    )

    # free_search
    agent.add_tool(
        name="free_search",
        description=search_description,
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
            "Returns a TodoList with main tasks and subtasks for accomplishing the user's goal."
        ),
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        function=lambda **kwargs: agent.planning_tool.create_plan_from_agent(),
    )

    # Task progression tools
    agent.add_tool(
        name="advance_to_next_task",
        description=(
            "Advance to the next task or subtask in the structured plan. "
            "Use this when you have completed the current task and want to move to the next one."
        ),
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        function=lambda **kwargs: agent.execution_engine.advance_task_progression(),
    )

    agent.add_tool(
        name="get_current_task_info",
        description=(
            "Get information about the current task being worked on, including progress and context."
        ),
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        function=lambda **kwargs: agent.execution_engine.get_current_task_context(),
    )

    agent.add_tool(
        name="get_execution_summary",
        description=(
            "Get a comprehensive summary of the current execution state and progress through the plan."
        ),
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        function=lambda **kwargs: agent.execution_engine.get_execution_summary(),
    )

    # Real-time state management tools
    agent.add_tool(
        name="get_task_progress_summary",
        description=(
            "Get detailed progress summary including main task and subtask completion percentages."
        ),
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        function=lambda **kwargs: agent.task_manager.progress.get_summary(),
    )

    agent.add_tool(
        name="get_task_evidence",
        description=(
            "Get evidence summary for a specific task, including all collected evidence and observations."
        ),
        parameters={
            "type": "object",
            "properties": {
                "task_id": {"type": "integer", "description": "ID of the task to get evidence for"}
            },
            "required": ["task_id"],
        },
        function=lambda task_id, **kwargs: agent.task_manager.get_task_evidence_summary(task_id),
    )

    agent.add_tool(
        name="add_task_evidence",
        description=(
            "Add completion evidence to a task or subtask to help track progress."
        ),
        parameters={
            "type": "object",
            "properties": {
                "task_id": {"type": "integer", "description": "ID of the main task"},
                "evidence": {"type": "string", "description": "Evidence description"},
                "subtask_id": {"type": "string", "description": "Optional subtask ID if evidence is for a subtask"}
            },
            "required": ["task_id", "evidence"],
        },
        function=lambda task_id, evidence, subtask_id=None, **kwargs: agent.task_manager.add_task_evidence(task_id, evidence, subtask_id),
    )

    agent.add_tool(
        name="get_execution_analytics",
        description=(
            "Get analytics about execution patterns, task activity, and evidence collection."
        ),
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        function=lambda **kwargs: agent.task_manager.get_execution_analytics(),
    )

    agent.add_tool(
        name="get_completion_analysis",
        description=(
            "Get intelligent completion analysis with confidence scores and validation breakdown for current tasks."
        ),
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        function=lambda **kwargs: agent.execution_engine.get_intelligent_completion_analysis(),
    )

    agent.add_tool(
        name="check_plan_completion_status",
        description=(
            "Check overall plan completion status and determine if ready for final answer. "
            "Use this to understand your progress through the structured plan."
        ),
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        function=lambda **kwargs: _check_plan_completion_status_impl(agent),
    )

    # Advanced task management tools
    agent.add_tool(
        name="add_task_to_plan",
        description=(
            "Add a new main task to the structured plan at a specific position."
        ),
        parameters={
            "type": "object",
            "properties": {
                "task_id": {"type": "integer", "description": "ID for the new task"},
                "description": {"type": "string", "description": "Task description"},
                "predicted_tools": {"type": "array", "items": {"type": "string"}, "description": "Tools predicted for this task"},
                "insert_after": {"type": "integer", "description": "Task ID to insert after (optional)"}
            },
            "required": ["task_id", "description"],
        },
        function=lambda task_id, description, predicted_tools=None, insert_after=None, **kwargs:
            agent.task_manager.add_main_task_to_plan(task_id, description, predicted_tools, insert_after),
    )

    agent.add_tool(
        name="remove_task_from_plan",
        description=(
            "Remove a main task from the structured plan."
        ),
        parameters={
            "type": "object",
            "properties": {
                "task_id": {"type": "integer", "description": "ID of task to remove"},
                "reason": {"type": "string", "description": "Reason for removal"}
            },
            "required": ["task_id"],
        },
        function=lambda task_id, reason="Manual removal", **kwargs:
            agent.task_manager.remove_main_task_from_plan(task_id, reason),
    )

    agent.add_tool(
        name="handle_task_failure",
        description=(
            "Handle current task failure with intelligent recovery strategies. "
            "Use when a task cannot be completed and you need to recover."
        ),
        parameters={
            "type": "object",
            "properties": {
                "error_message": {"type": "string", "description": "Description of the failure"},
                "recovery_strategy": {"type": "string", "enum": ["retry", "skip", "alternative"], "description": "Recovery strategy to use"}
            },
            "required": ["error_message"],
        },
        function=lambda error_message, recovery_strategy="retry", **kwargs:
            agent.execution_engine.handle_task_failure(error_message, recovery_strategy),
    )

    agent.add_tool(
        name="get_plan_analytics_report",
        description=(
            "Get comprehensive analytics report for plan execution including health, complexity, and recommendations."
        ),
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        function=lambda **kwargs: agent.execution_engine.create_plan_analytics_report(),
    )

    agent.add_tool(
        name="check_parallel_execution_options",
        description=(
            "Check what tasks can be executed in parallel and get simulation of parallel execution benefits."
        ),
        parameters={
            "type": "object",
            "properties": {
                "max_parallel": {"type": "integer", "description": "Maximum number of parallel tasks (default: 2)"}
            },
            "required": [],
        },
        function=lambda max_parallel=2, **kwargs: agent.execution_engine.simulate_parallel_execution(max_parallel),
    )

    agent.add_tool(
        name="get_plan_health_status",
        description=(
            "Get overall health status of plan execution with failure/blocked task analysis."
        ),
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        function=lambda **kwargs: agent.task_manager.get_plan_health_status(),
    )

    # Episodic memory tools (optional)
    if getattr(agent, "use_episodic_memory", False) and getattr(agent, "episodic", None) is not None:
        def episodic_remember_impl(title, event, context=None, outcome=None, tags=None, meta=None, **kwargs):
            """Wrapper for episodic_remember that returns structured YAML response."""
            import yaml
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
                    "event": {"type": "string", "description": "Machine-oriented event key"},
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
            """Wrapper for episodic_recall that returns structured YAML response."""
            import yaml
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


def _check_plan_completion_status_impl(agent: Any) -> dict:
    """Helper function to check plan completion status (inlined from agent method).

    This function was extracted from agent._check_plan_completion_status() to remove
    the wrapper method. It directly calls execution_engine methods.

    Args:
        agent: The agent instance

    Returns:
        Dictionary with completion status and context
    """
    if not agent.execution_engine.plan_loaded:
        return {"plan_loaded": False, "can_finalize": True}

    task_context = agent.execution_engine.get_current_task_context()
    execution_summary = agent.execution_engine.get_execution_summary()

    # Check if all tasks are completed
    all_complete = (task_context.get("status") != "executing" or
                   execution_summary.get('completed_main_tasks', 0) == execution_summary.get('total_main_tasks', 0))

    return {
        "plan_loaded": True,
        "all_tasks_complete": all_complete,
        "can_finalize": all_complete,
        "progress_percentage": task_context.get('progress', {}).get('percentage', 0),
        "completed_tasks": execution_summary.get('completed_main_tasks', 0),
        "total_tasks": execution_summary.get('total_main_tasks', 0),
        "current_task": task_context.get('main_task', {}).get('id') if task_context.get("status") == "executing" else None
    }


def register_task_management_tools(agent: Any) -> None:
    """Register task management tools on the provided agent.

    Notes:
    - Imports from tool_lib.base_tools.task_tools
    - Lambdas wrap tool functions with agent parameter
    """

    # Update task status tool
    agent.add_tool(
        name="update_task_status",
        description=UPDATE_TASK_STATUS_DESCRIPTION,
        parameters=UPDATE_TASK_STATUS_PARAMETERS,
        function=lambda task_id, status, reason=None, evidence=None, **kwargs:
            update_task_status(agent, task_id, status, reason, evidence)
    )

    # Mark task complete tool
    agent.add_tool(
        name="mark_task_complete",
        description=MARK_TASK_COMPLETE_DESCRIPTION,
        parameters=MARK_TASK_COMPLETE_PARAMETERS,
        function=lambda task_id, outputs=None, summary=None, **kwargs:
            mark_task_complete(agent, task_id, summary, outputs)
    )
