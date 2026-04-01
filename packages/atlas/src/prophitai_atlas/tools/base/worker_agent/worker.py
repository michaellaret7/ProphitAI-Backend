"""Worker tool - delegates a focused task to a WorkerAgent."""

import uuid
from typing import Any, List, Optional

from prophitai_atlas.agents.worker_agent import WorkerAgent
from prophitai_atlas.models.callbacks import WorkerCallbackWrapper
from prophitai_atlas.models.defaults import WORKER_PROVIDER, WORKER_MODEL
from prophitai_atlas.models.notebook import Notebook
from prophitai_atlas.tools.responses import success_response, error_response


def deploy_worker_agent(
    notebook: Notebook,
    chat_callback: Any,
    task: str,
    plan_task_id: str = "",
    user_id: Optional[str] = None,
) -> str:
    """
    Deploy a worker agent to execute a focused task.

    Workers are self-sufficient — they always receive ALL_TOOL_FUNCTIONS from
    the registry, independent of the parent agent's tool scope.

    Args:
        notebook: Shared Notebook instance (pre-bound via partial).
        chat_callback: Orchestrator's callback for streaming events (pre-bound via partial).
        task: Focused task description for the worker agent to execute.
        plan_task_id: The plan task ID this worker is deployed for.
        user_id: Clerk user ID for user-scoped tools.
    Returns:
        str: YAML-formatted result with:
            - 'success' (bool): Whether operation succeeded
            - 'data' (dict): Worker result (answer, tool_calls_made, tokens_used, iterations, stop_reason)
            - 'error' (str): Error message when unsuccessful
    """
    # Reason: Lazy import to avoid circular dependency (atlas -> tools -> atlas).
    # This is the integration point where the worker gets ALL available domain tools.
    from prophitai_tools.registry import ALL_TOOL_FUNCTIONS

    try:
        print(f"\n[WorkerDeploy] Spawning worker for plan task {plan_task_id} with {len(ALL_TOOL_FUNCTIONS)} tools available")
        print(f"[WorkerDeploy] Task: {task[:100]}{'...' if len(task) > 100 else ''}\n")

        # Wrap the orchestrator's callback so events are tagged with worker identity
        worker_id = f"worker-{uuid.uuid4().hex[:8]}"
        worker_callback = WorkerCallbackWrapper(
            chat_callback, task_id=task[:80], worker_id=worker_id, plan_task_id=plan_task_id,
        )

        worker_agent = WorkerAgent(
            task=task,
            deferred_tools=ALL_TOOL_FUNCTIONS,
            notebook=notebook,
            provider=WORKER_PROVIDER,
            model=WORKER_MODEL,
            chat_callback=worker_callback,
            max_iterations=30,
            user_id=user_id,
        )

        result = worker_agent.run()
        return success_response(result.model_dump())
    except Exception as e:
        return error_response(e)
