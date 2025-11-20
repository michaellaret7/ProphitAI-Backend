"""
Pydantic models for company-specific data endpoints.

Handles request validation for peers, ESG, revenue segmentation,
and institutional ownership endpoints.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional


class PeersRequest(BaseModel):
    """Request model for fetching stock peers data"""
    ticker: str = Field(..., description="Stock ticker symbol")

    @field_validator('ticker')
    @classmethod
    def validate_ticker(cls, v):
        """Ensure ticker is uppercase and non-empty"""
        if not v or not v.strip():
            raise ValueError("Ticker must be provided and non-empty")
        return v.upper().strip()


class ESGRequest(BaseModel):
    """Request model for fetching ESG disclosures data"""
    ticker: str = Field(..., description="Stock ticker symbol")

    @field_validator('ticker')
    @classmethod
    def validate_ticker(cls, v):
        """Ensure ticker is uppercase and non-empty"""
        if not v or not v.strip():
            raise ValueError("Ticker must be provided and non-empty")
        return v.upper().strip()


class RevenueSegmentationRequest(BaseModel):
    """Request model for fetching revenue segmentation data (product or geographic)"""
    ticker: str = Field(..., description="Stock ticker symbol")

    @field_validator('ticker')
    @classmethod
    def validate_ticker(cls, v):
        """Ensure ticker is uppercase and non-empty"""
        if not v or not v.strip():
            raise ValueError("Ticker must be provided and non-empty")
        return v.upper().strip()


class InstitutionalOwnershipRequest(BaseModel):
    """Request model for fetching institutional ownership data"""
    ticker: str = Field(..., description="Stock ticker symbol")
    year: int = Field(..., description="Year (e.g., 2025)", ge=2000, le=2100)
    quarter: int = Field(..., description="Quarter (1-4)", ge=1, le=4)

    @field_validator('ticker')
    @classmethod
    def validate_ticker(cls, v):
        """Ensure ticker is uppercase and non-empty"""
        if not v or not v.strip():
            raise ValueError("Ticker must be provided and non-empty")
        return v.upper().strip()


class CompanyNotesRequest(BaseModel):
    """Request model for fetching company notes and bonds data"""
    ticker: str = Field(..., description="Stock ticker symbol")

    @field_validator('ticker')
    @classmethod
    def validate_ticker(cls, v):
        """Ensure ticker is uppercase and non-empty"""
        if not v or not v.strip():
            raise ValueError("Ticker must be provided and non-empty")
        return v.upper().strip()


class EarningsTranscriptRequest(BaseModel):
    """Request model for fetching earnings calls transcripts"""
    ticker: str = Field(..., description="Stock ticker symbol")
    year: int = Field(..., description="Year (e.g., 2025)", ge=2000, le=2100)
    quarter: int = Field(..., description="Quarter (1-4)", ge=1, le=4)
    quarters_back: int = Field(1, description="Number of quarters to fetch (default: 1, max: 20)", ge=1, le=20)

    @field_validator('ticker')
    @classmethod
    def validate_ticker(cls, v):
        """Ensure ticker is uppercase and non-empty"""
        if not v or not v.strip():
            raise ValueError("Ticker must be provided and non-empty")
        return v.upper().strip()
