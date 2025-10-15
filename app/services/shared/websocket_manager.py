from typing import Dict, Set, Callable, Optional
from fastapi import WebSocket
import asyncio
import json
from app.core.agentic_framework.base_agent.events.manager import AgentEvent

class WebSocketConnectionManager:
    def __init__(self) -> None:
        self.run_id_to_sockets: Dict[str, Set[WebSocket]] = {}
        self.lock = asyncio.Lock()

    async def connect(self, run_id: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self.lock:
            self.run_id_to_sockets.setdefault(run_id, set()).add(ws)

    async def disconnect(self, run_id: str, ws: WebSocket) -> None:
        async with self.lock:
            sockets = self.run_id_to_sockets.get(run_id)
            if not sockets:
                return
            sockets.discard(ws)
            if not sockets:
                self.run_id_to_sockets.pop(run_id, None)

    async def send(self, run_id: str, message: dict) -> None:
        payload = json.dumps(message, ensure_ascii=False)
        async with self.lock:
            sockets = list(self.run_id_to_sockets.get(run_id, set()))
        if not sockets:
            return
        await asyncio.gather(*(s.send_text(payload) for s in sockets), return_exceptions=True)

ws_manager = WebSocketConnectionManager()

def attach_agent_stream(
    agent,
    run_id: str,
    loop: Optional[asyncio.AbstractEventLoop] = None,
    manager: WebSocketConnectionManager = ws_manager,
) -> Callable[[], None]:
    """Attach evidence/status streaming to an agent.

    Forwards only specific tool-call arguments (add_task_evidence, update_task_status)
    as a single JSON string to all websocket subscribers for the given run_id.
    """
    if loop is None:
        loop = asyncio.get_event_loop()

    def _send(msg: dict) -> None:
        asyncio.run_coroutine_threadsafe(manager.send(run_id, msg), loop)

    def _build_task_state() -> dict:
        """Serialize the current structured plan into a simple dict.

        The client will decide which parts to render (e.g., completed subtasks only).
        """
        try:
            task_manager = getattr(agent, "task_manager", None)
            plan = getattr(task_manager, "structured_plan", None) if task_manager else None
            if not plan or not getattr(plan, "tasks", None):
                return {"tasks": []}

            tasks = []
            for t in plan.tasks:
                tasks.append({
                    "id": t.id,
                    "description": t.description,
                    "status": getattr(t.status, "value", str(t.status)),
                    "subtasks": [
                        {
                            "id": st.id,
                            "description": st.description,
                            "completed": bool(st.completed),
                        }
                        for st in (t.subtasks or [])
                    ],
                })
            return {"tasks": tasks}
        except Exception:
            # On any serialization issue, return empty state to avoid breaking agent loop
            return {"tasks": []}

    def on_tool_executed(data):
        try:
            tool_name = (data or {}).get("tool_name")
            args = (data or {}).get("args") or {}

            # Send all tool calls to the websocket (just the tool name)
            _send({
                "type": "tool_call",
                "tool_name": tool_name,
            })

            # Also handle specific tools for evidence and task state
            if tool_name == "add_task_evidence":
                # Keep existing evidence stream intact
                _send({
                    "type": "evidence",
                    "arguments": json.dumps(args, ensure_ascii=False, separators=(",", ":")),
                })
            elif tool_name == "update_task_status":
                # Broadcast full hierarchical task state instead of raw status
                state = _build_task_state()
                _send({
                    "type": "task_state",
                    "arguments": json.dumps(state, ensure_ascii=False, separators=(",", ":")),
                })
        except Exception:
            # Never break the agent loop due to stream issues
            pass

    agent.event_manager.on(AgentEvent.TOOL_EXECUTED, on_tool_executed)

    def on_iteration_complete(_):
        try:
            state = _build_task_state()
            _send({
                "type": "task_state",
                "arguments": json.dumps(state, ensure_ascii=False, separators=(",", ":")),
            })
        except Exception:
            pass

    def on_task_event(_):
        try:
            state = _build_task_state()
            _send({
                "type": "task_state",
                "arguments": json.dumps(state, ensure_ascii=False, separators=(",", ":")),
            })
        except Exception:
            pass

    agent.event_manager.on(AgentEvent.ITERATION_COMPLETE, on_iteration_complete)
    agent.event_manager.on(AgentEvent.TASK_STARTED, on_task_event)
    agent.event_manager.on(AgentEvent.TASK_COMPLETED, on_task_event)

    def detach():
        agent.event_manager.off(AgentEvent.TOOL_EXECUTED, on_tool_executed)
        agent.event_manager.off(AgentEvent.ITERATION_COMPLETE, on_iteration_complete)
        agent.event_manager.off(AgentEvent.TASK_STARTED, on_task_event)
        agent.event_manager.off(AgentEvent.TASK_COMPLETED, on_task_event)

    return detach