import asyncio
from uuid import uuid4, UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from app.domain.portfolio_operations.optimizer.agent import OptimizerAgent
from app.redis.client import cache
from app.services.shared import RESULT_CACHE_KEY_TEMPLATE, start_agent_run

router = APIRouter()

class OptimizerRunRequest(BaseModel):
    portfolio_id: str

    @field_validator('portfolio_id')
    @classmethod
    def validate_portfolio_id(cls, v: str) -> str:
        """Validate that portfolio_id is a valid UUID format"""
        try:
            UUID(v)
            return v
        except (ValueError, AttributeError):
            raise ValueError(
                f"portfolio_id must be a valid UUID format, got: '{v}'. "
                f"Example: 'b07e9c3b-01a1-4431-9b5f-2048c1bc7e11'"
            )

@router.post("/agents/optimizer/runs")
async def create_optimizer_run(body: OptimizerRunRequest):
    """
    Create and start an optimizer agent run for a specific portfolio.

    Args:
        body: Request body containing portfolio_id (must be valid UUID)

    Returns:
        run_id: UUID of the agent run for polling results

    Raises:
        HTTPException 422: If portfolio_id is not a valid UUID format
        HTTPException 500: If agent initialization fails
    """
    run_id = str(uuid4())

    try:
        agent = OptimizerAgent(portfolio_id=body.portfolio_id)
        asyncio.create_task(start_agent_run(run_id, agent))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start optimizer: {str(e)}")

    return {"run_id": run_id}


@router.get("/agents/optimizer/runs/{run_id}/result")
async def get_optimizer_run_result(run_id: str):
    """Fetch the cached optimizer run result if available."""
    cache_key = RESULT_CACHE_KEY_TEMPLATE.format(run_id=run_id)
    cached_result = await cache.get(cache_key)
    if cached_result is None:
        raise HTTPException(status_code=404, detail="Result not available yet")

    return {"payload": cached_result}