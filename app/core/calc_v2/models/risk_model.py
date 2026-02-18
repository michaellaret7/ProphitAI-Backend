"""Pydantic model for risk metric output."""

from typing import Annotated
from pydantic import AfterValidator, BaseModel

Float4 = Annotated[float, AfterValidator(lambda v: round(v, 4))]

class RiskMetrics(BaseModel):
    """Container for portfolio risk metrics."""
    # Tier 1: Essential
    annualized_volatility: Float4              # Annualized standard deviation
    max_drawdown: Float4                       # Maximum peak-to-trough decline
    var_95: Float4                             # Value at Risk (95% confidence)
    var_99: Float4                             # Value at Risk (99% confidence)
    cvar_95: Float4                            # Conditional VaR / Expected Shortfall (95%)
    cvar_99: Float4                            # Conditional VaR / Expected Shortfall (99%)

    # Tier 2: Downside-Focused
    downside_deviation: Float4                 # Semi-deviation (negative returns only)
    ulcer_index: Float4                        # Depth and duration of drawdowns
    max_drawdown_duration: Float4              # Maximum duration of a drawdown

    # Tier 3: Distribution Shape (Tail Risk)
    skewness: Float4                           # Asymmetry of returns (-ve = left tail risk)
    kurtosis: Float4                           # Excess kurtosis (>0 = fat tails, more extreme events)

    # Tier 4: Market-Relative (None if no benchmark provided)
    beta: Float4 | None = None                 # Systematic risk vs benchmark
    tracking_error: Float4 | None = None       # Volatility of returns vs benchmark
    upside_capture: Float4 | None = None       # % of benchmark gains captured
    downside_capture: Float4 | None = None     # % of benchmark losses captured
