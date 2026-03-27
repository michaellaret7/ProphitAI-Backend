"""Worker tool setup — deploy schema, resolution, and worker dispatch."""

from copy import deepcopy
from typing import Any, Dict, List

from prophitai_atlas.models.notebook import Notebook
from prophitai_atlas.tools.responses import error_response


# ==============================================================================
# TOOL SCHEMA CONSTANTS
# ==============================================================================

DEPLOY_WORKER_DESCRIPTION = """
  Deploy a focused worker agent to autonomously execute a sub-task.
  The worker runs its own tool-calling loop and returns a structured result.

  The `task` string MUST contain ALL 5 labeled sections:
    ROLE — The worker's persona and expertise. Be specific.
    TASK — What to accomplish. Include concrete inputs (tickers, dates, metrics).
    SUCCESS CRITERIA — Measurable conditions the worker checks to know it's done.
    RULES — Constraints, scope limits, and guardrails.
    OUTPUT FORMAT — Exact structure of the final response.

  Pass prior results via `context` to avoid re-fetching.
  Only equip tools the worker actually needs — fewer is better.
  Always pass `plan_task_id`.

  Args:
      task: The worker's full prompt with all 5 sections: ROLE, TASK,
          SUCCESS CRITERIA, RULES, OUTPUT FORMAT.
      tools: List of tool names to equip the worker with.
      plan_task_id: The plan task ID this worker is deployed for (e.g., '1', '2').
      context: Optional data from prior steps to prepend as background.

  Returns:
      YAML-formatted result:
      - success (bool): Whether the worker completed successfully
      - data: answer, tool_calls_made, tokens_used, iterations, stop_reason

  Examples:
      deploy_worker_agent(
          task="ROLE: Senior equity analyst...\\nTASK: Research AAPL earnings...\\n...",
          tools=["earnings_call_search", "get_ticker_news"],
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
        "tools": {
            "type": "array",
            "items": {
                "type": "string",
            },
            "description": "List of tool names to equip the worker agent with.",
            "minItems": 1
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
    "required": ["task", "tools", "plan_task_id"],
    "additionalProperties": False
}

# Reason: WorkerAgent auto-registers these via AgentBase and its own __init__,
# so the orchestrator may redundantly request them. Skip silently.
_WORKER_DEFAULT_TOOLS = {"think", "calculator", "llm_web_search", "write_note"}


def _resolve_and_deploy(
    available_tools: Dict[str, Dict[str, Any]],
    notebook: Notebook,
    chat_callback: Any,
    task: str,
    tools: List[str],
    plan_task_id: str = "",
    context: str = "",
) -> str:
    """Resolve tool name strings to tool dicts, then deploy the worker agent.

    Args:
        available_tools: Flat dict of tool_name → tool dict (pre-bound via lambda).
        notebook: Shared Notebook instance (pre-bound via lambda).
        chat_callback: Orchestrator's callback for streaming events (pre-bound via lambda).
        task: Task description from the orchestrator LLM.
        tools: List of tool name strings from the orchestrator LLM.
        plan_task_id: The plan task ID this worker is deployed for.
        context: Optional data from prior steps to prepend to the task.
    """
    from prophitai_atlas.tools.base.worker_agent.worker import deploy_worker_agent

    tool_defs = []
    for name in tools:
        if name in _WORKER_DEFAULT_TOOLS:
            continue
        tool = available_tools.get(name)
        if tool is None:
            return error_response(
                f"Unknown tool '{name}'. Available: {sorted(available_tools.keys())}"
            )
        tool_defs.append(tool)

    # Reason: Prepend context with a label so the worker LLM can distinguish
    # background data from the structured 5-section task prompt.
    full_task = f"CONTEXT:\n{context}\n\n{task}" if context else task

    return deploy_worker_agent(
        notebook=notebook,
        chat_callback=chat_callback,
        task=full_task,
        tools=tool_defs,
        plan_task_id=plan_task_id,
    )


# Reason: `function` is intentionally omitted — it must be bound via
# lambda at registration time in Agent.__init__.
DEPLOY_WORKER_TOOL = {
    "name": "deploy_worker_agent",
    "description": DEPLOY_WORKER_DESCRIPTION,
    "parameters": DEPLOY_WORKER_PARAMETERS,
}


def build_deploy_worker_schema(available_tools: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Build deploy_worker_agent schema with tool name enum from catalogue.

    When a ToolCatalogue is available, this produces a schema whose ``tools``
    parameter has an enum of valid tool names so the LLM gets autocompletion
    and validation.
    """
    params = deepcopy(DEPLOY_WORKER_PARAMETERS)
    params["properties"]["tools"]["items"]["enum"] = sorted(available_tools.keys())
    return {
        "name": "deploy_worker_agent",
        "description": DEPLOY_WORKER_DESCRIPTION,
        "parameters": params,
    }
