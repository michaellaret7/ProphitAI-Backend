"""Worker tool setup — deploy schema and worker dispatch."""

from typing import Any, List, Optional

from prophitai_atlas.models.notebook import Notebook


# ==============================================================================
# TOOL SCHEMA CONSTANTS
# ==============================================================================

DEPLOY_WORKER_DESCRIPTION = """
  Deploy a focused worker agent to autonomously execute a sub-task.
  The worker runs its own tool-calling loop and returns a structured result.
  The worker has access to all available tools via deferred registration.

  The `task` string MUST contain ALL 5 labeled sections:
    ROLE — The worker's persona and expertise. Be specific.
    TASK — What to accomplish. Include concrete inputs (tickers, dates, metrics).
    SUCCESS CRITERIA — Measurable conditions the worker checks to know it's done.
    RULES — Constraints, scope limits, and guardrails.
    OUTPUT FORMAT — Exact structure of the final response.

  Pass prior results via `context` to avoid re-fetching.
  Always pass `plan_task_id`.

  Args:
      task: The worker's full prompt with all 5 sections: ROLE, TASK,
          SUCCESS CRITERIA, RULES, OUTPUT FORMAT.
      plan_task_id: The plan task ID this worker is deployed for (e.g., '1', '2').
      context: Optional data from prior steps to prepend as background.

  Returns:
      YAML-formatted result:
      - success (bool): Whether the worker completed successfully
      - data: answer, tool_calls_made, tokens_used, iterations, stop_reason

  Examples:
      deploy_worker_agent(
          task="ROLE: Senior equity analyst...\\nTASK: Research AAPL earnings...\\n...",
          plan_task_id="1",
          context="Prior worker identified AAPL as top pick, score 92/100."
      )
"""

DEPLOY_WORKER_PARAMETERS = {
    "type": "object",
    "properties": {
        "task": {
            "type": "string",
            "description": "The worker's full prompt with all 5 sections: ROLE, TASK, SUCCESS CRITERIA, RULES, OUTPUT FORMAT."
        },
        "plan_task_id": {
            "type": "string",
            "description": "The plan task ID this worker is being deployed for (e.g., '1', '2')."
        },
        "context": {
            "type": "string",
            "description": "Optional data from prior steps to prepend as background context."
        }
    },
    "required": ["task", "plan_task_id"],
    "additionalProperties": False
}


def _resolve_and_deploy(
    notebook: Notebook,
    chat_callback: Any,
    user_id: Optional[str],
    task: str,
    plan_task_id: str = "",
    context: str = "",
) -> str:
    """Deploy a worker agent for a sub-task.

    Workers are self-sufficient — they always load ALL_TOOL_FUNCTIONS from the
    registry directly, independent of the parent agent's tool scope.

    Args:
        notebook: Shared Notebook instance (pre-bound via lambda).
        chat_callback: Orchestrator's callback for streaming events (pre-bound via lambda).
        user_id: Clerk user ID for user-scoped tools (pre-bound via lambda).
        task: Task description from the orchestrator LLM.
        plan_task_id: The plan task ID this worker is deployed for.
        context: Optional data from prior steps to prepend to the task.
    """
    from prophitai_atlas.tools.base.worker_agent.worker import deploy_worker_agent

    # Reason: Prepend context with a label so the worker LLM can distinguish
    # background data from the structured 5-section task prompt.
    full_task = f"CONTEXT:\n{context}\n\n{task}" if context else task

    return deploy_worker_agent(
        notebook=notebook,
        chat_callback=chat_callback,
        user_id=user_id,
        task=full_task,
        plan_task_id=plan_task_id,
    )


# Reason: `function` is intentionally omitted — it must be bound via
# lambda at registration time in Agent.__init__.
DEPLOY_WORKER_TOOL = {
    "name": "deploy_worker_agent",
    "description": DEPLOY_WORKER_DESCRIPTION,
    "parameters": DEPLOY_WORKER_PARAMETERS,
}
