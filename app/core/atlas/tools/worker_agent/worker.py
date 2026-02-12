"""Worker tool - delegates a focused task to a WorkerAgent."""

from typing import List, Dict, Any

from app.core.atlas.agents.worker_agent import WorkerAgent
from app.core.atlas.models.notebook import Notebook
from app.core.atlas.tools.responses import success_response, error_response

# TODO: Once this is working, test a complexity arg and a speed arg to dynamically select the model and provider.
# This could be super helpful for cost, speed, and answer depth of the worker agent but needs testing and validation.


def deploy_worker_agent(
    notebook: Notebook,
    task: str,
    tools: List[Dict[str, Any]],
) -> str:
    """Deploy a worker agent to execute a focused task with selected tools.

    Args:
        notebook: Shared Notebook instance (pre-bound via partial).
        task: Focused task description for the worker agent to execute.
        tools: List of resolved tool definition dicts to register with the worker.

    Returns:
        str: YAML-formatted result with:
            - 'success' (bool): Whether operation succeeded
            - 'data' (dict): Worker result (answer, tool_calls_made, tokens_used, iterations, stop_reason)
            - 'error' (str): Error message when unsuccessful
    """
    try:
        tool_names = [t["name"] for t in tools]
        print(f"\n[WorkerDeploy] Spawning worker with tools: {tool_names}")
        print(f"[WorkerDeploy] Task: {task[:100]}{'...' if len(task) > 100 else ''}\n")

        worker_agent = WorkerAgent(
            task=task,
            tools=tools,
            notebook=notebook,
            provider='gemini',
            model='gemini-3-flash-preview',
            max_iterations=30,
            temperature=0.7,
        )

        result = worker_agent.run()
        return success_response(result.model_dump())
    except Exception as e:
        return error_response(e)

