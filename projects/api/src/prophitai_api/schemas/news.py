import re
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime


class NewsRequest(BaseModel):
    """Request model for fetching news data"""
    ticker: str = Field(..., description="Stock ticker symbol")
    start_date: Optional[datetime] = Field(None, description="Start date for filtering news (ISO format)")
    end_date: Optional[datetime] = Field(None, description="End date for filtering news (ISO format)")
    limit: Optional[int] = Field(None, gt=0, le=1000, description="Maximum number of news items to return")
    ascending: bool = Field(True, description="Sort by date ascending (True) or descending (False)")

    @field_validator('ticker')
    @classmethod
    def validate_ticker(cls, v):
        """Ensure ticker is uppercase and non-empty"""
        if not v or not v.strip():
            raise ValueError("Ticker must be provided and non-empty")
        return v.upper().strip()

    @field_validator('end_date')
    @classmethod
    def validate_end_date(cls, v, info):
        """Ensure end_date is after start_date if both provided"""
        if v is not None and info.data.get('start_date') is not None:
            if v < info.data['start_date']:
                raise ValueError("end_date must be after start_date")
        return v


class BatchStockNewsRequest(BaseModel):
    """Request model for fetching stock news for multiple tickers."""

    tickers: List[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="List of stock ticker symbols (max 5)"
    )
    limit: int = Field(
        default=100,
        gt=0,
        le=500,
        description="Maximum number of news items to return (default: 100, max: 500)"
    )
    from_date: Optional[str] = Field(
        default=None,
        description="Start date (YYYY-MM-DD format)"
    )
    to_date: Optional[str] = Field(
        default=None,
        description="End date (YYYY-MM-DD format)"
    )

    @field_validator('tickers')
    @classmethod
    def validate_tickers(cls, v):
        """Ensure all tickers are uppercase, non-empty, and deduplicated."""
        if not v:
            raise ValueError("At least one ticker must be provided")

        cleaned_tickers = list(dict.fromkeys(
            [ticker.upper().strip() for ticker in v if ticker and ticker.strip()]
        ))

        if not cleaned_tickers:
            raise ValueError("At least one valid ticker must be provided")

        if len(cleaned_tickers) > 5:
            raise ValueError("Maximum 5 tickers allowed per batch request")

        return cleaned_tickers

    @field_validator('from_date', 'to_date')
    @classmethod
    def validate_date_format(cls, v):
        """Validate date format is YYYY-MM-DD."""
        if v is None:
            return v
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            raise ValueError("Date must be in YYYY-MM-DD format")
        return v
