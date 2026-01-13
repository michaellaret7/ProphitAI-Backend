from pydantic import BaseModel, Field
from typing import List, Literal


class SuggestedChange(BaseModel):
    """A single suggested change to the portfolio."""
    action: Literal["remove", "reduce", "add", "increase"] = Field(..., description="Type of action to take")
    ticker: str = Field(..., description="Ticker symbol affected")
    reason: str = Field(..., description="Why this change is recommended")
    current_allocation: float | None = Field(None, description="Current allocation (if exists)")
    suggested_allocation: float | None = Field(None, description="Suggested new allocation")


class PortfolioPosition(BaseModel):
    """A position in the portfolio."""
    ticker: str
    allocation: float = Field(..., description="Allocation as decimal (0.10 = 10%)")
    position: Literal["long", "short"] = "long"


class InsightsResponseModel(BaseModel):
    """Portfolio insights with suggested changes and updated portfolio."""
    insights: List[str] = Field(..., description="Key findings about the portfolio (correlations, weaknesses, etc.)")
    suggested_changes: List[SuggestedChange] = Field(..., description="Recommended changes to improve the portfolio")
    updated_portfolio: List[PortfolioPosition] = Field(..., description="The new portfolio with suggested changes applied")