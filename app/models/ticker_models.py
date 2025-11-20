"""
Pydantic models for ticker-specific data endpoints.

Handles request validation for ticker information and financial metrics.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List


class TTMRatiosTickerCompsRequest(BaseModel):
    """Request model for fetching TTM ratios for multiple tickers (comparables)"""
    tickers: List[str] = Field(..., min_length=1, max_length=50, description="List of stock ticker symbols (max 50)")

    @field_validator('tickers')
    @classmethod
    def validate_tickers(cls, v):
        """Ensure all tickers are uppercase, non-empty, and deduplicated"""
        if not v:
            raise ValueError("At least one ticker must be provided")

        # Remove empty strings, strip whitespace, convert to uppercase, and deduplicate
        cleaned_tickers = list(dict.fromkeys([ticker.upper().strip() for ticker in v if ticker and ticker.strip()]))

        if not cleaned_tickers:
            raise ValueError("At least one valid ticker must be provided")

        if len(cleaned_tickers) > 50:
            raise ValueError("Maximum 50 tickers allowed")

        return cleaned_tickers
