from pydantic import BaseModel, Field, field_validator
from typing import Optional
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
