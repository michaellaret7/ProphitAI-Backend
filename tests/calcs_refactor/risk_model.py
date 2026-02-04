from pydantic import BaseModel


class RiskMetrics(BaseModel):
    """Container for portfolio risk metrics."""
    # Tier 1: Essential
    volatility: float              # Annualized standard deviation
    max_drawdown: float            # Maximum peak-to-trough decline
    var_95: float                  # Value at Risk (95% confidence)
    var_99: float                  # Value at Risk (99% confidence)
    cvar_95: float                 # Conditional VaR / Expected Shortfall (95%)
    cvar_99: float                 # Conditional VaR / Expected Shortfall (99%)

    # Tier 2: Downside-Focused
    downside_deviation: float      # Semi-deviation (negative returns only)
    ulcer_index: float             # Depth and duration of drawdowns
    avg_drawdown: float            # Average of all drawdowns
    avg_drawdown_duration: float   # Average days underwater

    # Tier 3: Distribution Shape (Tail Risk)
    skewness: float                # Asymmetry of returns (-ve = left tail risk)
    kurtosis: float                # Excess kurtosis (>0 = fat tails, more extreme events)

    # Tier 4: Market-Relative (None if no benchmark provided)
    beta: float | None = None      # Systematic risk vs benchmark
    tracking_error: float | None = None  # Volatility of returns vs benchmark
    upside_capture: float | None = None  # % of benchmark gains captured
    downside_capture: float | None = None  # % of benchmark losses captured