from pydantic import BaseModel, Field, field_validator
from typing import List


class StockPriceRequest(BaseModel):
    """Request model for fetching stock price data"""
    tickers: List[str] = Field(..., min_length=1, description="List of stock ticker symbols")
    days: int = Field(..., gt=0, description="Number of days of historical data to retrieve")

    @field_validator('tickers')
    @classmethod
    def validate_tickers(cls, v):
        """Ensure all tickers are uppercase and non-empty"""
        if not v:
            raise ValueError("At least one ticker must be provided")
        return [ticker.upper().strip() for ticker in v if ticker.strip()]


class PriceDataPoint(BaseModel):
    """Single price data point"""
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    close: float = Field(..., description="Closing price")


class TickerPriceData(BaseModel):
    """Price data for a single ticker"""
    ticker: str = Field(..., description="Stock ticker symbol")
    data: List[PriceDataPoint] = Field(..., description="List of price data points")


class BatchQuoteRequest(BaseModel):
    """Request model for fetching quotes for multiple tickers."""

    tickers: List[str] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="List of stock ticker symbols (max 20)"
    )

    @field_validator('tickers')
    @classmethod
    def validate_tickers(cls, v):
        """Ensure all tickers are uppercase, non-empty, and deduplicated."""
        if not v:
            raise ValueError("At least one ticker must be provided")

        # Clean, uppercase, and deduplicate while preserving order
        cleaned_tickers = list(dict.fromkeys(
            [ticker.upper().strip() for ticker in v if ticker and ticker.strip()]
        ))

        if not cleaned_tickers:
            raise ValueError("At least one valid ticker must be provided")

        if len(cleaned_tickers) > 20:
            raise ValueError("Maximum 20 tickers allowed per batch request")

        return cleaned_tickers
