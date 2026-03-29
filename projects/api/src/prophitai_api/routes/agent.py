"""Agent execution router for starting agents and retrieving results.

Provides REST endpoints for:
- Starting agent execution (returns execution_id)
- Polling for execution results
- Clarifying user preferences before portfolio build
- Building portfolios from enriched briefs
"""

from fastapi import APIRouter, BackgroundTasks

from prophitai_api.agents import ClarifyRequest, ClarifyResult, BuildRequest
from prophitai_api.controllers.agent import (
    execute_agent_controller,
    get_execution_result_controller,
    clarify_preferences_controller,
    build_portfolio_controller,
)
from prophitai_api.schemas.agent import (
    ExecuteAgentRequest,
    ExecuteAgentResponse,
    ExecutionResultResponse,
)

router = APIRouter(prefix="/agents", tags=["Agent Execution"])


@router.post("/execute", response_model=ExecuteAgentResponse)
async def execute_agent(
    request: ExecuteAgentRequest,
    background_tasks: BackgroundTasks,
) -> ExecuteAgentResponse:
    """Start an agent execution. Returns execution_id for tracking."""
    result = await execute_agent_controller(
        agent_type=request.agent_type,
        parameters=request.parameters,
        background_tasks=background_tasks,
    )
    return ExecuteAgentResponse(**result)


@router.get("/{execution_id}/result", response_model=ExecutionResultResponse)
async def get_execution_result(execution_id: str) -> ExecutionResultResponse:
    """Poll for execution result."""
    result = await get_execution_result_controller(execution_id=execution_id)
    return ExecutionResultResponse(**result)


@router.post("/clarify", response_model=ClarifyResult)
async def clarify_preferences(request: ClarifyRequest) -> ClarifyResult:
    """Generate clarifying questions for a portfolio request."""
    result = await clarify_preferences_controller(
        user_preferences=request.user_preferences,
    )
    return ClarifyResult(**result)


@router.post("/build-portfolio", response_model=ExecuteAgentResponse)
async def build_portfolio(
    request: BuildRequest,
    background_tasks: BackgroundTasks,
) -> ExecuteAgentResponse:
    """Build a portfolio from the original query and clarification answers."""
    result = await build_portfolio_controller(
        user_preferences=request.user_preferences,
        answers=request.answers,
        background_tasks=background_tasks,
    )
    return ExecuteAgentResponse(**result)
