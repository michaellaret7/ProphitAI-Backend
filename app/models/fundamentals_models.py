from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class AnalystEstimatesRequest(BaseModel):
    """Request model for fetching analyst estimates data"""
    ticker: str = Field(..., description="Stock ticker symbol")
    periods_back: int = Field(4, gt=0, le=100, description="Number of periods to retrieve (quarters or years depending on period)")
    period: str = Field('quarter', description="Reporting period: 'quarter' or 'annual'")

    @field_validator('ticker')
    @classmethod
    def validate_ticker(cls, v):
        """Ensure ticker is uppercase and non-empty"""
        if not v or not v.strip():
            raise ValueError("Ticker must be provided and non-empty")
        return v.upper().strip()

    @field_validator('period')
    @classmethod
    def validate_period(cls, v):
        """Ensure period is either 'quarter' or 'annual'"""
        if v not in ['quarter', 'annual']:
            raise ValueError("Period must be either 'quarter' or 'annual'")
        return v.lower()


class AnalystDataRequest(BaseModel):
    """Request model for fetching analyst recommendations, grades, and ratings"""
    ticker: str = Field(..., description="Stock ticker symbol")
    start_date: Optional[datetime] = Field(None, description="Start date for filtering data (ISO format)")
    end_date: Optional[datetime] = Field(None, description="End date for filtering data (ISO format)")
    limit: Optional[int] = Field(None, gt=0, le=1000, description="Maximum number of items to return (not applicable to all endpoints)")
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


class PriceTargetRequest(BaseModel):
    """Request model for fetching price target summary (no date filtering)"""
    ticker: str = Field(..., description="Stock ticker symbol")

    @field_validator('ticker')
    @classmethod
    def validate_ticker(cls, v):
        """Ensure ticker is uppercase and non-empty"""
        if not v or not v.strip():
            raise ValueError("Ticker must be provided and non-empty")
        return v.upper().strip()
