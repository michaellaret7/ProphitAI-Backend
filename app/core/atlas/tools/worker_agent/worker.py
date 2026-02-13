"""Worker tool - delegates a focused task to a WorkerAgent."""

from typing import Any, List, Dict

from app.core.atlas.agents.worker_agent import WorkerAgent
from app.core.atlas.models.notebook import Notebook
from app.core.atlas.tools.responses import success_response, error_response


def deploy_worker_agent(
    notebook: Notebook,
    chat_callback: Any,
    task: str,
    tools: List[Dict[str, Any]],
) -> str:
    """Deploy a worker agent to execute a focused task with selected tools.

    Args:
        notebook: Shared Notebook instance (pre-bound via partial).
        chat_callback: Orchestrator's callback for streaming events (pre-bound via partial).
        task: Focused task description for the worker agent to execute.
        tools: List of resolved tool definition dicts to register with the worker.

    Returns:
        str: YAML-formatted result with:
            - 'success' (bool): Whether operation succeeded
            - 'data' (dict): Worker result (answer, tool_calls_made, tokens_used, iterations, stop_reason)
            - 'error' (str): Error message when unsuccessful
    """
    from app.services.shared.chat_executor import WorkerCallbackWrapper

    try:
        tool_names = [t["name"] for t in tools]
        print(f"\n[WorkerDeploy] Spawning worker with tools: {tool_names}")
        print(f"[WorkerDeploy] Task: {task[:100]}{'...' if len(task) > 100 else ''}\n")

        # Wrap the orchestrator's callback so events are tagged with task context
        worker_callback = WorkerCallbackWrapper(chat_callback, task_id=task[:80])

        worker_agent = WorkerAgent(
            task=task,
            tools=tools,
            notebook=notebook,
            chat_callback=worker_callback,
            provider='grok',
            model='grok-4-1-fast-reasoning',
            max_iterations=30,
            temperature=0.7,
        )

        result = worker_agent.run()
        return success_response(result.model_dump())
    except Exception as e:
        return error_response(e)

