"""Pydantic model for group-level metrics (sector/industry/sub-industry)."""

from typing import Annotated
from pydantic import AfterValidator, BaseModel

Float4 = Annotated[float, AfterValidator(lambda v: round(v, 4))]


class GroupMetrics(BaseModel):
    """Risk and concentration metrics for a single classification group."""
    var_99: Float4
    concentration: Float4
    tickers: list[str]
