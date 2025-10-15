import asyncio
import json
import logging
from typing import Any

from app.redis.client import cache
from app.services.shared.websocket_manager import attach_agent_stream, ws_manager

RESULT_CACHE_TTL = 86400  # 24 hours
RESULT_CACHE_KEY_TEMPLATE = "agents:optimizer:{run_id}:result"

logger = logging.getLogger(__name__)

async def start_agent_run(run_id: str, agent: Any) -> None:
    """Start a synchronous agent run in a worker thread and stream evidence.

    Args:
        run_id: Correlation id for websocket subscribers
        agent: Constructed agent instance (e.g., OptimizerAgent())
    """
    loop = asyncio.get_running_loop()
    detach = attach_agent_stream(agent, run_id, loop, ws_manager)
    cache_key = RESULT_CACHE_KEY_TEMPLATE.format(run_id=run_id)
    try:
        # Run the blocking agent in a thread without managing our own executor
        result = await asyncio.to_thread(agent.run)
        serializable_result = json.loads(json.dumps(result, default=str))

        await ws_manager.send(run_id, {"type": "completed", "payload": serializable_result})
        await cache.set(cache_key, serializable_result, ttl=RESULT_CACHE_TTL)
    except Exception as exc:
        logger.exception("Optimizer agent run %s failed", run_id)
        await ws_manager.send(
            run_id,
            {
                "type": "error",
                "error": str(exc),
            },
        )
        raise
    finally:
        detach()
