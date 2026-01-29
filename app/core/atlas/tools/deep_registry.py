"""Tool registration for agents."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.core.atlas.tools.base.search_engine import (
    AgentSearchEngine,
    LLM_WEB_SEARCH_DESCRIPTION,
    LLM_WEB_SEARCH_PARAMETERS,
)
from app.core.atlas.tools.deep import (
    update_tasks,
    UPDATE_TASKS_DESCRIPTION,
    UPDATE_TASKS_PARAMETERS,
    create_edit_plan_wrapper,
    EDIT_PLAN_DESCRIPTION,
    EDIT_PLAN_PARAMETERS,
    write_note as notes_write,
    WRITE_NOTE_DESCRIPTION,
    WRITE_NOTE_PARAMETERS,
    retrieve_notes as notes_retrieve,
    RETRIEVE_NOTES_DESCRIPTION,
    RETRIEVE_NOTES_PARAMETERS,
    finalize as finalize_tool,
    FINALIZE_DESCRIPTION,
    FINALIZE_PARAMETERS,
)

if TYPE_CHECKING:
    from app.core.atlas.agents import AgentBase
    from app.core.atlas.agents.chat_agent import ChatAgent


def register_base_deep_tools(agent: Any) -> None:
    """Register the base tools on the provided agent."""

    # llm_web_search (Perplexity-powered web search)
    agent.add_tool(
        name="llm_web_search",
        description=LLM_WEB_SEARCH_DESCRIPTION,
        parameters=LLM_WEB_SEARCH_PARAMETERS,
        function=lambda queries, recency_filter=None, reasoning_effort=None, mode="regular-search", **kwargs: AgentSearchEngine().llm_web_search(
            queries=queries,
            recency_filter=recency_filter,
            reasoning_effort=reasoning_effort,
            mode=mode,
        ),
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
            output_dir=getattr(agent, "output_dir", None),
            state_callback=getattr(agent, "state_callback", None)
        ),
    )

    # edit_plan (dynamic plan modification)
    agent.add_tool(
        name="edit_plan",
        description=EDIT_PLAN_DESCRIPTION,
        parameters=EDIT_PLAN_PARAMETERS,
        function=create_edit_plan_wrapper(agent),
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

    # retrieve_notes (read notes)
    agent.add_tool(
        name="retrieve_notes",
        description=RETRIEVE_NOTES_DESCRIPTION,
        parameters=RETRIEVE_NOTES_PARAMETERS,
        function=lambda title, **kwargs: notes_retrieve(
            title=title,
            output_dir=str(getattr(agent, "output_dir", ""))
        ),
    )

    # finalize (final answer)
    agent.add_tool(
        name="finalize",
        description=FINALIZE_DESCRIPTION,
        parameters=FINALIZE_PARAMETERS,
        function=lambda answer, meta=None, **kwargs: finalize_tool(
            answer=answer,
            plan=agent.plan,
            meta=meta
        ),
    )


