"""Pydantic models for correlation matrix output."""

from typing import Annotated
from pydantic import AfterValidator, BaseModel

Float4 = Annotated[float, AfterValidator(lambda v: round(v, 4))]

class CorrelationMetrics(BaseModel):
    """Derived metrics from a correlation matrix."""
    avg_pairwise_correlation: Float4
    diversification_ratio: Float4
