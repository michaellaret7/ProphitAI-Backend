import asyncio
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.domain.portfolio_operations.optimizer.agent import OptimizerAgent
from app.redis.client import cache
from app.services.agent_runs import RESULT_CACHE_KEY_TEMPLATE, start_agent_run

router = APIRouter()

@router.post("/agents/optimizer/runs")
async def create_optimizer_run():
    """Create and start an optimizer agent run with built-in prompts."""
    run_id = str(uuid4())

    agent = OptimizerAgent()
    asyncio.create_task(start_agent_run(run_id, agent))

    return {"run_id": run_id}


@router.get("/agents/optimizer/runs/{run_id}/result")
async def get_optimizer_run_result(run_id: str):
    """Fetch the cached optimizer run result if available."""
    cache_key = RESULT_CACHE_KEY_TEMPLATE.format(run_id=run_id)
    cached_result = await cache.get(cache_key)
    if cached_result is None:
        raise HTTPException(status_code=404, detail="Result not available yet")

    return {"payload": cached_result}

id = "b07e9c3b-01a1-4431-9b5f-2048c1bc7e11"