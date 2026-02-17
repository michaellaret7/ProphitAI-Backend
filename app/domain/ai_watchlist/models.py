from pydantic import BaseModel, Field
from typing import List

class WatchlistItem(BaseModel):
    """A single ticker recommendation in the watchlist."""
    ticker: str = Field(..., description="Stock or ETF ticker symbol")
    name: str = Field(..., description="Full name of the security")
    investment_thesis: str = Field(..., description="Extremely detailed investment thesis for the ticker")

class WatchlistResponse(BaseModel):
    """Complete AI watchlist response containing recommended tickers."""
    investment_thesis: str = Field(..., description="Extremely detailed overall investment thesis for the watchlist theme")
    watchlist: List[WatchlistItem] = Field(..., description="List of recommended tickers")
