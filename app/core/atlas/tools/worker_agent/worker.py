"""Worker tool - delegates a focused task to a WorkerAgent."""

from typing import List, Dict, Any, Callable, Optional

from app.core.atlas.agents.worker_agent import WorkerAgent
from app.core.atlas.tools.responses import success_response, error_response

# TODO: Once this is working, test a complexity arg and a speed arg to dynamically select the model and provider.
# This could be super helpful for cost, speed, and answer depth of the worker agent but needs testing and validation.

def deploy_worker_agent(
    task: str,
    tools: List[Dict[str, Any]],
    *,
    worker_id: str = "worker",
    note_sink: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> str:
    """Deploy a worker agent to execute a focused task with selected tools.

    Args:
        task: Focused task description for the worker agent to execute.
        tools: List of resolved tool definition dicts to register with the worker.
        worker_id: Stable identifier assigned by the caller.
        note_sink: Optional callback for streaming worker notes to orchestrator state.

    Returns:
        str: YAML-formatted result with:
            - 'success' (bool): Whether operation succeeded
            - 'data' (dict): Worker result (answer, tool_calls_made, tokens_used, iterations, stop_reason)
            - 'error' (str): Error message when unsuccessful
    """
    try:
        worker_notes: List[Dict[str, Any]] = []

        def _write_note(note: Dict[str, Any]) -> None:
            worker_notes.append(note)
            if note_sink is not None:
                note_sink(note)

        tool_names = [t["name"] for t in tools]
        print(f"\n[WorkerDeploy] Spawning {worker_id} with tools: {tool_names}")
        print(f"[WorkerDeploy] Task: {task[:100]}{'...' if len(task) > 100 else ''}\n")

        worker_agent = WorkerAgent(
            task=task,
            provider='gemini',
            model='gemini-3-flash-preview',
            tools=tools,
            max_iterations=30,
            temperature=0.7,
            worker_id=worker_id,
            note_sink=_write_note,
        )

        worker_result = worker_agent.run()
        payload = worker_result.model_dump() if hasattr(worker_result, "model_dump") else worker_result
        payload.update({
            "worker_id": worker_id,
            "notes_written": len(worker_notes),
        })

        return success_response(payload)
    except Exception as e:
        return error_response(e)

