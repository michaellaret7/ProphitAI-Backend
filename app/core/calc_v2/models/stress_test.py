"""Pydantic models for combined ETF beta-shock stress testing."""

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel

Float4 = Annotated[float, AfterValidator(lambda v: round(v, 4))]


class TickerStressResult(BaseModel):
    """Per-ticker stress result from combined ETF shocks.

    Each ticker's expected return is computed via multi-factor OLS:
        expected_return = Σ(βᵢ × shockᵢ)
    """

    ticker: str
    weight: Float4
    expected_return: Float4 | None = None
    weighted_pnl: Float4 | None = None
    pct_of_portfolio_impact: Float4 | None = None
    factor_betas: dict[str, Float4]
    factor_beta_std_errors: dict[str, Float4] | None = None


class EtfContribution(BaseModel):
    """How much of the portfolio stress comes from a single ETF shock.

    contribution = portfolio_sensitivity × shock
    """

    etf: str
    shock: Float4
    portfolio_sensitivity: Float4 | None = None
    contribution: Float4 | None = None
    pct_of_total: Float4 | None = None


class StressTestResult(BaseModel):
    """Top-level combined stress test result.

    Combines per-ticker OLS betas with user-supplied ETF shocks to estimate
    portfolio-level impact, residual risk, and attribution breakdowns.

    Two expected-return paths:
        - expected_return: top-down (portfolio OLS betas × shocks) — consistent with residual_std
        - expected_return_bottom_up: sum of weight × ticker-level OLS PnLs — for attribution
    """

    # Portfolio-level metrics (top-down from portfolio OLS)
    expected_return: Float4 | None = None
    expected_return_bottom_up: Float4 | None = None
    idiosyncratic_vol_annual: Float4 | None = None
    total_stressed_vol: Float4 | None = None
    stressed_var_95: Float4 | None = None
    r_squared: Float4 | None = None
    residual_std: Float4 | None = None
    horizon: Literal["daily"] = "daily"

    # Breakdowns
    ticker_results: list[TickerStressResult]
    etf_contributions: list[EtfContribution]

    # Summary
    top_detractors: list[str]
    top_hedges: list[str]
