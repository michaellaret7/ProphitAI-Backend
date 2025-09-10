from enum import Enum
from typing import Dict

from pydantic import BaseModel, Field, RootModel, field_validator


class PositionType(str, Enum):
    """Allowed position directions for a portfolio holding."""
    long = "long"
    short = "short"


class PortfolioPosition(BaseModel):
    """Normalized position schema: allocation (0–1) and position (long/short)."""
    allocation: float = Field(..., ge=0.0, le=1.0, description="Allocation as decimal between 0 and 1")
    position: PositionType

    @field_validator("position", mode="before")
    @classmethod
    def normalize_position(cls, v):
        if isinstance(v, str):
            return v.lower()
        return v


class PortfolioInput(RootModel[Dict[str, PortfolioPosition]]):
    """Root model mapping ticker -> PortfolioPosition.

    Example:
        {
            "AAPL": {"allocation": 0.05, "position": "long"},
            "WBA": {"allocation": 0.03, "position": "short"}
        }
    """

    pass

