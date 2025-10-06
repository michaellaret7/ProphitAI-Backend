import asyncio
from uuid import uuid4
from fastapi import APIRouter

from app.services.agent_runs import start_agent_run
from app.domain.portfolio_operations.optimizer.agent import OptimizerAgent

router = APIRouter()

@router.post("/agents/optimizer/runs")
async def create_optimizer_run():
    """Create and start an optimizer agent run with built-in prompts."""
    run_id = str(uuid4())

    agent = OptimizerAgent()
    asyncio.create_task(start_agent_run(run_id, agent))

    return {"run_id": run_id}


