import asyncio
import re
from uuid import uuid4, UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from app.domain.portfolio_operations.optimizer.agent import OptimizerAgent
from app.redis.client import cache
from app.services.shared import RESULT_CACHE_KEY_TEMPLATE, start_agent_run

router = APIRouter()

class OptimizerRunRequest(BaseModel):
    portfolio_id: str
    risk_tolerance: str = None
    investment_goals: str = None
    time_horizon: str = None
    sectors_to_exclude: str = None
    sectors_to_include: str = None
    tickers_to_keep: str = None
    tickers_to_exclude: str = None

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

    @field_validator(
        'risk_tolerance',
        'investment_goals',
        'time_horizon',
        'sectors_to_exclude',
        'sectors_to_include',
        'tickers_to_keep',
        'tickers_to_exclude'
    )
    @classmethod
    def sanitize_template_placeholders(cls, v: str | None) -> str | None:
        """
        Convert empty strings, whitespace, and template placeholders to None.
        Template placeholders are strings like {{VARIABLE_NAME}}.
        """
        if v is None:
            return None

        # Strip whitespace
        v = v.strip()

        # Check if empty after stripping
        if not v:
            return None

        # Check if it's a template placeholder (e.g., {{SECTORS_TO_INCLUDE}})
        if re.match(r'^\{\{[A-Z_]+\}\}$', v):
            return None

        return v

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
        agent = OptimizerAgent(
            portfolio_id=body.portfolio_id,
            risk_tolerance=body.risk_tolerance,
            investment_goals=body.investment_goals,
            time_horizon=body.time_horizon,
            sectors_to_exclude=body.sectors_to_exclude,
            sectors_to_include=body.sectors_to_include,
            tickers_to_keep=body.tickers_to_keep,
            tickers_to_exclude=body.tickers_to_exclude
        )
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