"""Worker tool - delegates a focused task to a WorkerAgent."""

import uuid
from typing import Any, List, Dict

from prophitai_atlas.agents.worker_agent import WorkerAgent
from prophitai_atlas.models.callbacks import WorkerCallbackWrapper
from prophitai_atlas.models.notebook import Notebook
from prophitai_atlas.tools.responses import success_response, error_response


def deploy_worker_agent(
    notebook: Notebook,
    chat_callback: Any,
    task: str,
    tools: List[Dict[str, Any]],
    plan_task_id: str = "",
) -> str:
    """Deploy a worker agent to execute a focused task with selected tools.

    Args:
        notebook: Shared Notebook instance (pre-bound via partial).
        chat_callback: Orchestrator's callback for streaming events (pre-bound via partial).
        task: Focused task description for the worker agent to execute.
        tools: List of resolved tool definition dicts to register with the worker.
        plan_task_id: The plan task ID this worker is deployed for.
    Returns:
        str: YAML-formatted result with:
            - 'success' (bool): Whether operation succeeded
            - 'data' (dict): Worker result (answer, tool_calls_made, tokens_used, iterations, stop_reason)
            - 'error' (str): Error message when unsuccessful
    """
    from prophitai_atlas.models.callbacks import WorkerCallbackWrapper

    try:
        tool_names = [t["name"] for t in tools]
        print(f"\n[WorkerDeploy] Spawning worker for plan task {plan_task_id} with tools: {tool_names}")
        print(f"[WorkerDeploy] Task: {task[:100]}{'...' if len(task) > 100 else ''}\n")

        # Wrap the orchestrator's callback so events are tagged with worker identity
        worker_id = f"worker-{uuid.uuid4().hex[:8]}"
        worker_callback = WorkerCallbackWrapper(
            chat_callback, task_id=task[:80], worker_id=worker_id, plan_task_id=plan_task_id,
        )

        worker_agent = WorkerAgent(
            task=task,
            tools=tools,
            notebook=notebook,
            provider="together",
            model="glm-5",
            chat_callback=worker_callback,
            max_iterations=30,
        )

        result = worker_agent.run()
        return success_response(result.model_dump())
    except Exception as e:
        return error_response(e)
