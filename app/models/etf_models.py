"""
Pydantic models for ETF-specific data endpoints.

Handles request validation for ETF information and batch operations.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List


class BatchETFInfoRequest(BaseModel):
    """Request model for fetching ETF info for multiple symbols."""

    symbols: List[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of ETF symbols (max 10)"
    )

    @field_validator('symbols')
    @classmethod
    def validate_symbols(cls, v):
        """Ensure all symbols are uppercase, non-empty, and deduplicated."""
        if not v:
            raise ValueError("At least one ETF symbol must be provided")

        # Reason: ETF symbols contain only letters and hyphens
        allowed_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ-")
        cleaned_symbols = []

        for symbol in v:
            if not symbol or not symbol.strip():
                continue
            s = symbol.upper().strip()
            if not all(c in allowed_chars for c in s):
                raise ValueError(f"Invalid symbol: {s}. Only letters and hyphens allowed.")
            cleaned_symbols.append(s)

        # Deduplicate while preserving order
        cleaned_symbols = list(dict.fromkeys(cleaned_symbols))

        if not cleaned_symbols:
            raise ValueError("At least one valid ETF symbol must be provided")

        if len(cleaned_symbols) > 10:
            raise ValueError("Maximum 10 ETF symbols allowed per batch request")

        return cleaned_symbols
