"""Request/response schemas for agent execution endpoints."""

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from prophitai_api.agents.sessions import ExecutionStatus


class AgentType(str, Enum):
    """Available agent types for execution."""

    WATCHLIST = "watchlist"
    PORTFOLIO_BUILDER = "portfolio_builder"


class ExecuteAgentRequest(BaseModel):
    """Request body for starting agent execution."""

    agent_type: AgentType = Field(..., description="The type of agent to execute")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Agent-specific parameters (varies by agent type)",
    )


class ExecuteAgentResponse(BaseModel):
    """Response from starting agent execution."""

    execution_id: str = Field(..., description="Unique identifier for this execution")
    message: str = Field(default="Agent execution started")


class ExecutionResultResponse(BaseModel):
    """Response from polling execution result."""

    status: ExecutionStatus = Field(..., description="Current execution status")
    result: Optional[Dict[str, Any]] = Field(None, description="Final result (when complete)")
    error: Optional[str] = Field(None, description="Error message (when status is error)")
    iterations: int = Field(0, description="Number of iterations used")
    tokens: int = Field(0, description="Total tokens consumed")
