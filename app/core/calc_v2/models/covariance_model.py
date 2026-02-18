"""Pydantic models for covariance matrix output."""

from typing import Annotated
from pydantic import AfterValidator, BaseModel

Float4 = Annotated[float, AfterValidator(lambda v: round(v, 4))]


class AssetRiskContribution(BaseModel):
    """Risk decomposition for a single asset."""
    ticker: str
    weight: Float4
    marginal_contribution: Float4
    component_contribution: Float4
    pct_contribution: Float4


class CovarianceMetrics(BaseModel):
    """Derived metrics from the covariance matrix with portfolio weights."""
    portfolio_variance_daily: Float4
    asset_risk_contributions: list[AssetRiskContribution]
