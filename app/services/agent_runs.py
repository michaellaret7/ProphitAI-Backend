import asyncio
from typing import Any
from app.services.websocket_manager_service import attach_agent_stream, ws_manager

async def start_agent_run(run_id: str, agent: Any) -> None:
    """Start a synchronous agent run in a worker thread and stream evidence.

    Args:
        run_id: Correlation id for websocket subscribers
        agent: Constructed agent instance (e.g., OptimizerAgent())
    """
    loop = asyncio.get_running_loop()
    detach = attach_agent_stream(agent, run_id, loop, ws_manager)
    try:
        # Run the blocking agent in a thread without managing our own executor
        await asyncio.to_thread(agent.run)
    finally:
        detach()


