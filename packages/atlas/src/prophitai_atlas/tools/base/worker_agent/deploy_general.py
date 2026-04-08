"""deploy_general_worker — Deploy an ad-hoc worker with explicitly named tools."""

import uuid
from typing import Any, List, Optional

from prophitai_atlas.models.callbacks import WorkerCallbackWrapper
from prophitai_atlas.models.defaults import WORKER_PROVIDER, WORKER_MODEL
from prophitai_atlas.models.notebook import Notebook
from prophitai_atlas.tools.responses import success_response, error_response

# Reason: General workers handle open-ended tasks that may require more
# exploration than scoped workers (whose specs default to 30).
GENERAL_WORKER_MAX_ITERATIONS = 100


# ==============================================================================
# --> Tool Schema
# ==============================================================================

DEPLOY_GENERAL_WORKER_DESCRIPTION = """
  Deploy an ad-hoc worker agent with an explicit set of tools.

  Use this when no predefined worker_type fits the task. You specify exactly
  which tools the worker receives by name. The worker runs its own tool-calling
  loop and returns a structured result.

  ## When to use deploy_general_worker vs deploy_worker

  - deploy_scoped_worker: A predefined specialist exists for your task. Prefer this.
  - deploy_general_worker: No specialist fits. You need a custom tool combination.

  ## When NOT to Deploy (do it yourself instead)

  - The task is 1-3 tool calls — just call the tools directly.
  - You need the raw output for your next reasoning step.
  - The task is context gathering, synthesis, or decision-making.

  ## Task Format

  The `task` string MUST contain ALL 5 labeled sections:
    ROLE — The worker's persona and expertise. Be specific.
    TASK — What to accomplish. Include concrete inputs (tickers, dates, metrics).
    SUCCESS CRITERIA — Measurable conditions the worker checks to know it's done.
    RULES — Constraints, scope limits, and guardrails.
    OUTPUT FORMAT — Exact structure of the final response.

  Args:
      task: The worker's full prompt with all 5 sections: ROLE, TASK,
          SUCCESS CRITERIA, RULES, OUTPUT FORMAT.
      tools: Array of tool name strings the worker should have access to
          (e.g., ["ticker_performance", "ticker_risk", "get_ticker_info"]).
      plan_task_id: The plan task ID this worker is deployed for (if during plan execution).
      context: Optional data from prior steps to prepend as background.

  Returns:
      YAML-formatted result:
      - success (bool): Whether the worker completed successfully
      - data: answer, tool_calls_made, tokens_used, iterations, stop_reason
"""

DEPLOY_GENERAL_WORKER_PARAMETERS = {
    "type": "object",
    "properties": {
        "task": {
            "type": "string",
            "description": (
                "The worker's full prompt with all 5 sections: ROLE, TASK, "
                "SUCCESS CRITERIA, RULES, OUTPUT FORMAT."
            ),
        },
        "tools": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Tool names the worker should have access to "
                "(e.g., ['ticker_performance', 'get_ticker_info'])."
            ),
        },
        "plan_task_id": {
            "type": "string",
            "description": "The plan task ID this worker is being deployed for (e.g., '1', '2').",
        },
        "context": {
            "type": "string",
            "description": "Optional data from prior steps to prepend as background context.",
        },
    },
    "required": ["task", "tools"],
    "additionalProperties": False,
}


# ==============================================================================
# --> Deploy Function
# ==============================================================================

def deploy_general_worker(
    notebook: Notebook,
    chat_callback: Any,
    user_id: Optional[str],
    task: str,
    tools: List[str],
    plan_task_id: str = "",
    context: str = "",
) -> str:
    """Deploy an ad-hoc worker with explicitly named tools.

    Resolves tool name strings to callables and runs the worker
    with the default worker system prompt.

    Args:
        notebook: Shared Notebook instance (pre-bound via lambda).
        chat_callback: Orchestrator's callback for streaming events (pre-bound via lambda).
        user_id: Clerk user ID for user-scoped tools (pre-bound via lambda).
        task: Task description from the orchestrator LLM.
        tools: List of tool name strings to resolve and give to the worker.
        plan_task_id: The plan task ID this worker is deployed for.
        context: Optional data from prior steps to prepend to the task.

    Returns:
        YAML-formatted success/error response.
    """
    # Reason: Lazy imports to avoid circular dependency (atlas -> tools -> atlas).
    from prophitai_tools.registry import ALL_TOOL_FUNCTIONS
    from prophitai_atlas.tools.base.worker_agent.resolve import resolve_tools_by_name
    from prophitai_atlas.agents.worker_agent import WorkerAgent

    if not tools:
        return error_response("tools array is empty. Provide at least one tool name.")

    try:
        resolved_tools = resolve_tools_by_name(ALL_TOOL_FUNCTIONS, tools)
    except ValueError as e:
        return error_response(str(e))

    full_task = f"CONTEXT:\n{context}\n\n{task}" if context else task

    try:
        print(f"\n[DeployGeneralWorker] Spawning worker with {len(resolved_tools)} tools: {tools}")
        print(f"[DeployGeneralWorker] Task: {full_task[:100]}{'...' if len(full_task) > 100 else ''}\n")

        worker_id = f"worker-{uuid.uuid4().hex[:8]}"

        worker_callback = WorkerCallbackWrapper(
            chat_callback,
            task_id=full_task[:80],
            worker_id=worker_id,
            plan_task_id=plan_task_id,
        )

        worker_agent = WorkerAgent(
            task=full_task,
            tools=resolved_tools,
            notebook=notebook,
            provider=WORKER_PROVIDER,
            model=WORKER_MODEL,
            chat_callback=worker_callback,
            max_iterations=GENERAL_WORKER_MAX_ITERATIONS,
            user_id=user_id,
        )

        result = worker_agent.run()

        return success_response(result.model_dump())

    except Exception as e:
        return error_response(e)


# Reason: `function` is intentionally omitted — it must be bound via
# lambda at registration time in the parent agent's __init__.
DEPLOY_GENERAL_WORKER_TOOL = {
    "name": "deploy_general_worker",
    "description": DEPLOY_GENERAL_WORKER_DESCRIPTION,
    "parameters": DEPLOY_GENERAL_WORKER_PARAMETERS,
}
