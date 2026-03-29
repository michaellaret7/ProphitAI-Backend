"""Unified response model returned by all Agent.run() methods."""

from typing import List, Optional

from pydantic import BaseModel, Field

from prophitai_atlas.models.new_plan import Plan


class AgentResponse(BaseModel):
    """Response from Agent.run()"""

    answer: str
    tool_calls_made: List[str] = Field(default_factory=list)
    tokens_used: int = 0
    iterations: int = 0
    stop_reason: str = "answer_ready"
    plan: Optional[Plan] = None
    parsed_output: Optional[BaseModel] = None
