from typing import Any

def register_base_tools(agent: Any) -> None:
    """
    Register the base tools on the provided agent.

    Notes:
    - Imports are local to avoid circular dependencies.
    - Lambdas capture `agent` and access attributes at call-time.
    """
    # Local imports to avoid circular dependencies at module import time
    from backend.src.agentic_framework.base_agent.base_tools.search_engine_tool import AgentSearchEngine
    from backend.src.agentic_framework.base_agent.base_tools.calculator import calculator

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
        function=lambda query: AgentSearchEngine().perplexity_free_search(query),
    )

    # calculator
    agent.add_tool(
        name="calculator",
        description=(
            "Perform mathematical calculations. Provide the expression string and the tool returns the result."
        ),
        parameters={
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Expression to evaluate."}
            },
            "required": ["expression"],
        },
        function=lambda expression: calculator(expression),
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
        function=lambda: agent.planning_tool.create_plan_from_agent(),
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
        function=lambda: agent.execution_engine.advance_task_progression(),
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
        function=lambda: agent.execution_engine.get_current_task_context(),
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
        function=lambda: agent.execution_engine.get_execution_summary(),
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
        function=lambda: agent.task_manager.get_task_progress_summary(),
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
        function=lambda task_id: agent.task_manager.get_task_evidence_summary(task_id),
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
        function=lambda task_id, evidence, subtask_id=None: agent.task_manager.add_task_evidence(task_id, evidence, subtask_id),
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
        function=lambda: agent.task_manager.get_execution_analytics(),
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
        function=lambda: agent.execution_engine.get_intelligent_completion_analysis(),
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
        function=lambda: agent._check_plan_completion_status(),
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
        function=lambda task_id, description, predicted_tools=None, insert_after=None: 
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
        function=lambda task_id, reason="Manual removal": 
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
        function=lambda error_message, recovery_strategy="retry": 
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
        function=lambda: agent.execution_engine.create_plan_analytics_report(),
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
        function=lambda max_parallel=2: agent.execution_engine.simulate_parallel_execution(max_parallel),
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
        function=lambda: agent.task_manager.get_plan_health_status(),
    )

    # Episodic memory tools (optional)
    if getattr(agent, "use_episodic_memory", False) and getattr(agent, "episodic", None) is not None:
        agent.add_tool(
            name="episodic_remember",
            description=(
                "Append an episodic memory entry. Use for key milestones or facts you may want to recall later."
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
            function=lambda title, event, context=None, outcome=None, tags=None, meta=None: \
                agent.episodic.append(title=title, event=event, context=context, outcome=outcome, tags=tags, meta=meta),
        )

        agent.add_tool(
            name="episodic_recall",
            description=(
                "Recall episodic memories by keyword, tags, or since a timestamp. Returns most recent first."
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
            function=lambda query=None, tags=None, since=None, limit=20: \
                agent.episodic.recall(query=query, tags=tags, since=since, limit=limit),
        )


def register_task_management_tools(agent: Any) -> None:
    """
    Register task management tools on the provided agent.

    Notes:
    - Imports are not required; lambdas use `agent` methods.
    - Kept separate from base tools for clarity.
    """
    # Update task status with evidence
    agent.add_tool(
        name="update_task_status",
        description="Update the status of a task with evidence of completion or progress",
        parameters={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Task identifier (e.g., 'task_1' or just '1' for step 1)"
                },
                "status": {
                    "type": "string",
                    "enum": ["started", "in_progress", "completed", "failed", "blocked"],
                    "description": "New task status"
                },
                "evidence": {
                    "type": "object",
                    "description": "Evidence supporting the status change",
                    "properties": {
                        "outputs": {"type": "object", "description": "Task outputs/results"},
                        "observations": {"type": "array", "items": {"type": "string"}},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1}
                    }
                },
                "reason": {
                    "type": "string",
                    "description": "Explanation for the status change"
                }
            },
            "required": ["task_id", "status"]
        },
        function=lambda **kwargs: agent.task_manager.update_task_status(**kwargs)
    )

    # Mark task complete (simplified version)
    agent.add_tool(
        name="mark_task_complete",
        description="Mark a task as complete with optional outputs",
        parameters={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Task identifier (e.g., 'task_1' or just '1' for step 1)"
                },
                "outputs": {
                    "type": "object",
                    "description": "Task outputs/results"
                },
                "summary": {
                    "type": "string",
                    "description": "Brief summary of what was accomplished"
                }
            },
            "required": ["task_id"]
        },
        function=lambda task_id, outputs=None, summary=None: agent.task_manager.update_task_status(
            task_id=task_id,
            status="completed",
            evidence={"outputs": outputs or {}, "summary": summary} if (outputs or summary) else None,
            reason=summary
        )
    )
