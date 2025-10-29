from app.core.agentic_framework.tool_lib.base_tools.search_engine_tool import AgentSearchEngine
from app.core.agentic_framework.tool_lib.base_tools import calculator
from app.core.agentic_framework.tool_lib.base_tools.task_management import (
    update_tasks,
    UPDATE_TASKS_DESCRIPTION,
    UPDATE_TASKS_PARAMETERS
)
from app.core.agentic_framework.tool_lib.base_tools.notes import (
    write_note as notes_write,
    WRITE_NOTE_DESCRIPTION,
    WRITE_NOTE_PARAMETERS,
)
from typing import Any

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

    # update_tasks (task management)
    agent.add_tool(
        name="update_tasks",
        description=UPDATE_TASKS_DESCRIPTION,
        parameters=UPDATE_TASKS_PARAMETERS,
        function=lambda main_task, subtasks=None, status="in_progress", work_summary=None, **kwargs: update_tasks(
            plan=agent.plan,
            main_task=main_task,
            subtasks=subtasks,
            status=status,
            work_summary=work_summary,
            output_dir=getattr(agent, "output_dir", None)
        ),
    )

    # write_note (notes)
    agent.add_tool(
        name="write_note",
        description=WRITE_NOTE_DESCRIPTION,
        parameters=WRITE_NOTE_PARAMETERS,
        function=lambda title, content, **kwargs: notes_write(
            title=title,
            content=content,
            output_dir=str(getattr(agent, "output_dir", ""))
        ),
    )
