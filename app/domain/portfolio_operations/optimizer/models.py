from pydantic import BaseModel, Field
from typing_extensions import Literal
from typing import List

class PortfolioPosition(BaseModel):
    """Single position in the optimized portfolio."""
    ticker: str = Field(description="Stock ticker symbol")
    allocation: float = Field(description="Allocation as decimal between 0 and 1")
    position: Literal["long", "short"] = Field(description="Position type")
    thesis: str = Field(description="Investment thesis for this position")


class PortfolioChange(BaseModel):
    """A single change made during optimization."""
    ticker: str = Field(description="Stock ticker symbol")
    change_type: Literal["added", "removed", "adjusted"] = Field(description="Type of change")
    reason: str = Field(description="Reason for the change")


class OptimizedPortfolio(BaseModel):
    """Complete output from the portfolio optimizer agent."""
    # Portfolio positions as a list
    portfolio: List[PortfolioPosition] = Field(
        description="List of optimized portfolio positions"
    )
    # Changes as a list
    changes: List[PortfolioChange] = Field(
        description="List of changes made during optimization. Use empty list [] if none."
    )
    # Improvements - flat fields
    sharpe_ratio: str = Field(description="Sharpe ratio change (e.g., 'Old: 1.82 -> New: 2.14'). Use 'N/A' if not calculated.")
    annualized_volatility: str = Field(description="Volatility change. Use 'N/A' if not calculated.")
    beta: str = Field(description="Beta change. Use 'N/A' if not calculated.")
    correlation: str = Field(description="Correlation change. Use 'N/A' if not calculated.")
    improvement_notes: str = Field(description="Additional notes on improvements. Use empty string if none.")

