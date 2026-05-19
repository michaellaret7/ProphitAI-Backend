"""deploy_scoped_worker — Deploy a pre-defined scoped worker from the WorkerSpec registry."""

import uuid
from typing import Any, Dict, Optional

from prophitai_atlas.models.callbacks import WorkerCallbackWrapper
from prophitai_atlas.models.worker_spec import WorkerSpec
from prophitai_atlas.models.defaults import WORKER_MODEL
from prophitai_atlas.models.notebook import Notebook
from prophitai_atlas.tools.responses import success_response, error_response


# ==============================================================================
# --> Tool Schema
# ==============================================================================

DEPLOY_SCOPED_WORKER_DESCRIPTION = """
  Deploy a pre-defined scoped worker agent to execute a sub-task.

  Each worker_type is a specialist with a curated tool set and system prompt
  optimized for its domain. The worker runs its own tool-calling loop in a
  separate context window and returns a structured result. Only the worker's
  final answer comes back — all intermediate tool calls stay in the worker's context.

  Workers serve two purposes:
  1. **Context compression** — multi-step research stays in the worker's context,
     keeping your context clean for coding and reasoning.
  2. **Specialization** — workers have domain-specific system prompts that make
     them better at their job (e.g., code reviewers know what to look for).

  Your system prompt specifies which steps REQUIRE worker deployment. Follow those
  instructions — when a step says "MANDATORY worker deployment", you must use this tool.

  ## Task Format

  The `task` string MUST contain ALL 5 labeled sections:
    ROLE — The worker's persona and expertise. Be specific.
    TASK — What to accomplish. Include concrete inputs (tickers, dates, metrics).
    SUCCESS CRITERIA — Measurable conditions the worker checks to know it's done.
    RULES — Constraints, scope limits, and guardrails.
    OUTPUT FORMAT — Exact structure of the final response.

  Pass prior results via `context` to avoid re-fetching.
  Always pass `plan_task_id`.

  Args:
      worker_type: The type of scoped worker to deploy. Each type has curated
          tools and a specialized system prompt.
      task: The worker's full prompt with all 5 sections: ROLE, TASK,
          SUCCESS CRITERIA, RULES, OUTPUT FORMAT.
      plan_task_id: The plan task ID this worker is deployed for (e.g., '1', '2').
      context: Optional data from prior steps to prepend as background.

  Returns:
      YAML-formatted result:
      - success (bool): Whether the worker completed successfully
      - data: answer, tool_calls_made, tokens_used, iterations, stop_reason
"""

DEPLOY_SCOPED_WORKER_PARAMETERS = {
    "type": "object",
    "properties": {
        "worker_type": {
            "type": "string",
            "description": (
                "The type of scoped worker to deploy. Each type has curated "
                "tools and a specialized system prompt."
            ),
        },
        "task": {
            "type": "string",
            "description": (
                "The worker's full prompt with all 5 sections: ROLE, TASK, "
                "SUCCESS CRITERIA, RULES, OUTPUT FORMAT."
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
    "required": ["worker_type", "task", "plan_task_id"],
    "additionalProperties": False,
}


# ==============================================================================
# --> Deploy Function
# ==============================================================================

def deploy_scoped_worker(
    notebook: Notebook,
    chat_callback: Any,
    user_id: Optional[str],
    registry: Dict[str, WorkerSpec],
    worker_type: str,
    task: str,
    plan_task_id: str = "",
    context: str = "",
) -> str:
    """Deploy a scoped worker from a workflow's worker registry.

    Looks up the spec by worker_type, resolves its tool names to callables,
    and runs the worker with the spec's custom system prompt.

    Args:
        notebook: Shared Notebook instance (pre-bound via lambda).
        chat_callback: Orchestrator's callback for streaming events (pre-bound via lambda).
        user_id: Clerk user ID for user-scoped tools (pre-bound via lambda).
        registry: Workflow-specific dict of worker_type -> WorkerSpec (pre-bound via lambda).
        worker_type: Registry key for the WorkerSpec to deploy.
        task: Task description from the orchestrator LLM.
        plan_task_id: The plan task ID this worker is deployed for.
        context: Optional data from prior steps to prepend to the task.

    Returns:
        YAML-formatted success/error response.
    """
    # Reason: Lazy imports to avoid circular dependency (atlas -> tools -> atlas).
    from prophitai_tools.registry import ALL_TOOL_FUNCTIONS
    from prophitai_atlas.tools.base.worker_agent.resolve import resolve_tools_by_name
    from prophitai_atlas.agents.worker_agent import WorkerAgent

    if worker_type not in registry:
        available = sorted(registry.keys()) if registry else ["(none registered)"]

        return error_response(
            f"Unknown worker_type '{worker_type}'. Available: {available}"
        )

    spec = registry[worker_type]

    tools = resolve_tools_by_name(ALL_TOOL_FUNCTIONS, spec.tools)

    full_task = f"CONTEXT:\n{context}\n\n{task}" if context else task

    try:
        print(f"\n[DeployWorker] Spawning '{worker_type}' for plan task {plan_task_id} with {len(tools)} tools")
        print(f"[DeployWorker] Task: {full_task[:100]}{'...' if len(full_task) > 100 else ''}\n")

        worker_id = f"worker-{uuid.uuid4().hex[:8]}"

        worker_callback = WorkerCallbackWrapper(
            chat_callback,
            task_id=full_task[:80],
            worker_id=worker_id,
            plan_task_id=plan_task_id,
        )

        worker_agent = WorkerAgent(
            task=full_task,
            tools=tools,
            notebook=notebook,
            system_prompt=spec.system_prompt,
            model=spec.model or WORKER_MODEL,
            chat_callback=worker_callback,
            max_iterations=spec.max_iterations,
            user_id=user_id,
        )

        result = worker_agent.run()

        return success_response(result.model_dump())

    except Exception as e:
        return error_response(e)


# Reason: `function` is intentionally omitted — it must be bound via
# lambda at registration time in the parent agent's __init__.
DEPLOY_SCOPED_WORKER_TOOL = {
    "name": "deploy_scoped_worker",
    "description": DEPLOY_SCOPED_WORKER_DESCRIPTION,
    "parameters": DEPLOY_SCOPED_WORKER_PARAMETERS,
}
