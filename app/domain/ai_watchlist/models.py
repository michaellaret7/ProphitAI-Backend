from pydantic import BaseModel, Field
from typing import List

class WatchlistItem(BaseModel):
    """A single ticker recommendation in the watchlist."""
    ticker: str = Field(..., description="Stock or ETF ticker symbol")
    name: str = Field(..., description="Full name of the security")
    theme_fit: str = Field(..., description="Explanation of how this ticker aligns with the investment theme")
    rationale: str = Field(..., description="Explanation of why this ticker will have strong future returns and performance potential")
    key_metrics: str = Field(..., description="Financial performance and risk metrics summary")


class WatchlistResponse(BaseModel):
    """Complete AI watchlist response containing recommended tickers."""
    investment_thesis: str = Field(..., description="Overall investment thesis for the watchlist theme")
    watchlist: List[WatchlistItem] = Field(..., description="List of recommended tickers")