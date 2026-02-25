"""Portfolio factor exposure tool.

Provides a tool for computing portfolio-level factor exposures (momentum,
value, quality, growth, volatility, size) via cross-sectional z-scoring
against a 55-ticker universe.
"""

from typing import Annotated

from app.core.atlas.tools.decorator import agent_tool, Param
from app.core.atlas.tools.responses import success_response, error_response
from app.core.atlas.tools.portfolio.utils import build_portfolio_obj


# ================================
# --> Helper funcs
# ================================

def _label_exposure(score: float | None) -> str:
    """Map a composite z-score to a human-readable tilt label.

    Args:
        score: Portfolio-weighted composite z-score for a factor category.

    Returns:
        Tilt label: "neutral", "mild/moderate/strong overweight/underweight", or "n/a".
    """
    if score is None:
        return "n/a"
    magnitude = abs(score)
    direction = "overweight" if score > 0 else "underweight"
    if magnitude < 0.25:
        return "neutral"
    if magnitude < 0.75:
        return f"mild {direction}"
    if magnitude < 1.25:
        return f"moderate {direction}"
    return f"strong {direction}"


def _build_tilt_summary(composite_scores: dict[str, float | None]) -> dict[str, str]:
    """Apply _label_exposure to all composite factor scores.

    Args:
        composite_scores: Dict of factor category name → composite z-score.

    Returns:
        Dict of factor category name → human-readable tilt label.
    """
    return {factor: _label_exposure(score) for factor, score in composite_scores.items()}


# ================================
# --> Tools
# ================================

@agent_tool(name="portfolio_factor_exposure")
def portfolio_factor_exposure(
    tickers: list[str],
    weights: list[float],
    years_back: Annotated[int, Param(min_val=1, max_val=5)] = 2,
) -> str:
    """Compute portfolio-level factor exposures via cross-sectional z-scoring.

Calculates how a portfolio tilts across six factor categories (momentum, value,
quality, growth, volatility, size) relative to a 55-ticker broad-market universe.
Composite scores are portfolio-weighted averages of per-metric z-scores.

**WHEN TO USE:**
- Understanding portfolio factor tilts (e.g. "is this portfolio momentum-heavy?")
- Comparing factor profiles across portfolio candidates
- Identifying unintended factor bets (e.g. hidden volatility overweight)
- Factor-based portfolio construction and rebalancing decisions

**IMPORTANT:**
- Weights are decimal percentages (0.30 = 30%). Negative = short position.
- Composite scores are z-scores: 0 = market-average, +1 = 1 std dev above universe mean.
- Momentum and volatility are always computed (price-based). Value, quality, growth, size
  require fundamental data and may be None for tickers without fundamentals.
- This tool takes ~15-25 seconds due to universe factor computation. Use judiciously.

    Args:
        tickers: List of ticker symbols in the portfolio (e.g., ['AAPL', 'MSFT', 'GOOGL'])
        weights: Decimal portfolio weights per ticker, same order as tickers.
            0.30 = 30% allocation. Negative = short. (e.g., [0.40, 0.35, 0.25])
        years_back: Number of years of historical data (default 2). Use 2+ for reliable
            factor signals — momentum needs 12+ months, YoY growth needs 8 quarters.

    Returns:
        YAML-formatted factor exposure results:
        - composite_scores: Per-category portfolio-weighted z-scores (momentum, value, etc.)
        - tilt_summary: Human-readable labels (neutral, mild/moderate/strong overweight/underweight)
        - detail: Per-metric z-scores for all 16 individual factor metrics

    Interpretation Guide:
        composite_scores: Portfolio-weighted mean z-score per factor category.
            0 = market-neutral. Positive = overweight vs universe. Negative = underweight.
        tilt_summary labels:
            neutral (|z| < 0.25): No meaningful tilt vs the universe.
            mild overweight/underweight (0.25-0.75): Small but noticeable tilt.
            moderate overweight/underweight (0.75-1.25): Meaningful factor bet.
            strong overweight/underweight (>1.25): Concentrated factor exposure.
        detail metrics:
            r12_1, r6_1, risk_adj_momentum: Price momentum sub-factors.
            earnings_yield, book_to_price, fcf_yield, ebitda_to_ev: Value sub-factors.
            gross_profitability, roe, accrual_ratio, altman_z_score: Quality sub-factors.
            revenue_growth_yoy, forward_eps_growth: Growth sub-factors.
            realized_vol_1y, beta: Volatility sub-factors.
            log_market_cap: Size sub-factor.

    Examples:
        portfolio_factor_exposure(
            tickers=["AAPL", "MSFT", "GOOGL"],
            weights=[0.40, 0.35, 0.25]
        )

        portfolio_factor_exposure(
            tickers=["AAPL", "TSLA", "JPM", "XOM", "PG"],
            weights=[0.25, 0.20, 0.20, 0.20, 0.15],
            years_back=3
        )

    Raises:
        ValueError: If tickers and weights have different lengths or no price data found
    """
    try:
        if len(tickers) != len(weights):
            return error_response(
                f"tickers ({len(tickers)}) and weights ({len(weights)}) must have the same length"
            )

        portfolio = build_portfolio_obj(tickers, weights, years_back, with_factors=True)

        if portfolio.factor_exposure is None:
            return error_response(
                "Factor exposure computation failed — check that ticker data and "
                "benchmark data are available for the requested period"
            )

        exposure = portfolio.factor_exposure
        composite_scores = {
            "momentum": exposure.momentum,
            "volatility": exposure.volatility,
            "value": exposure.value,
            "quality": exposure.quality,
            "growth": exposure.growth,
            "size": exposure.size,
        }

        return success_response({
            "tickers": portfolio.tickers,
            "weights": [round(w, 4) for w in portfolio.weights.tolist()],
            "years_back": years_back,
            "composite_scores": composite_scores,
            "tilt_summary": _build_tilt_summary(composite_scores),
            "detail": exposure.detail.model_dump(),
        })

    except Exception as e:
        return error_response(f"Failed to compute portfolio factor exposure: {str(e)}")


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print(portfolio_factor_exposure(
        tickers=["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
        weights=[0.30, 0.25, 0.20, 0.15, 0.10],
        years_back=2,
    ))
