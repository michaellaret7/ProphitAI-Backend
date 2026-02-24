"""Ticker factor exposure tool.

Provides a tool for analyzing single-ticker factor exposures using the Ticker
class and TickerFactors model from calc_v2. Supports momentum, volatility,
value, quality, growth, and size factors.
"""

from typing import Annotated, Literal

from app.core.atlas.tools.decorator import agent_tool, Param
from app.core.atlas.tools.responses import success_response, error_response
from app.core.atlas.tools_v2.ticker.utils import build_ticker_obj


# ================================
# --> Tools
# ================================

@agent_tool(name="ticker_factors")
def ticker_factors(
    ticker: str,
    category: Literal["momentum", "volatility", "value", "quality", "growth", "size", "all"] = "all",
    years_back: Annotated[int, Param(min_val=1, max_val=5)] = 2,
) -> str:
    """
    Compute quantitative factor exposures for a single ticker.

    Returns factor metrics organized by category. Momentum and volatility are
    always available (price-based). Value, quality, growth, and size require
    fundamentals data and will be null if unavailable.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'KO')
        category: Factor category to retrieve, or 'all' for every category
        years_back: Number of years of historical price data to analyze

    Returns:
        YAML-formatted factor exposures for the requested category.

    Interpretation Guide (all metrics are point-in-time exposures):
        MOMENTUM (price-based, always available):
            r12_1: 12-month return ex last month. Core academic momentum signal. Positive = uptrend.
            r6_1: 6-month return ex last month. Medium-term momentum.
            r3_1: 3-month return ex last month. Short-term momentum.
            risk_adj_momentum: Momentum divided by volatility. Quality-adjusted trend strength.
            pct_from_52w_high: Distance from 52-week peak. 0.0 = at high, -0.20 = 20% below.

        VOLATILITY (price-based, always available):
            realized_vol_1y: Annualized 1-year volatility. <15% low, 15-25% moderate, >40% high.
            realized_vol_3m: Annualized 3-month volatility. More responsive to recent regime shifts.
            beta: Sensitivity to SPY. <0.8 defensive, 1.0 market, >1.5 aggressive.
            idiosyncratic_vol: Stock-specific volatility unexplained by market. Higher = more stock-specific risk.
            max_drawdown_1y: Largest peak-to-trough decline over 1 year. -0.10 mild, -0.30+ severe.

        VALUE (requires fundamentals):
            earnings_yield: E/P ratio. Higher = cheaper. >8% deep value.
            book_to_price: B/P ratio. Higher = cheaper. >1.0 below book value.
            fcf_yield: FCF/Price. Higher = more free cash flow per dollar invested.
            ebitda_to_ev: EBITDA/EV. Higher = cheaper enterprise valuation.
            dividend_yield: Annual dividends / price.

        QUALITY (requires fundamentals):
            gross_profitability: Gross profit / total assets. Novy-Marx quality factor. Higher = better.
            roe: Return on equity. >15% strong, <5% weak.
            roa: Return on assets. >10% excellent, <3% weak.
            accrual_ratio: Earnings quality. Near 0 = cash-backed, high = accrual-driven (riskier).
            debt_to_equity: Leverage. <0.5 conservative, >2.0 highly leveraged.
            interest_coverage: EBIT / interest expense. >5 safe, <2 distressed.
            altman_z_score: Bankruptcy risk. >3.0 safe, 1.8-3.0 grey zone, <1.8 distress.

        GROWTH (requires fundamentals):
            revenue_growth_yoy: Year-over-year revenue growth. >15% high growth.
            earnings_growth_yoy: Year-over-year earnings growth.
            fcf_growth_yoy: Year-over-year free cash flow growth.
            forward_eps_growth: Analyst consensus forward EPS growth estimate.
            sustainable_growth_rate: ROE * retention ratio. Max growth without external financing.

        SIZE (requires fundamentals):
            market_cap: Market capitalization in dollars.
            log_market_cap: Natural log of market cap. Used for cross-sectional factor models.

    Examples:
        ticker_factors(ticker="AAPL", category="momentum")
        >>> {"success": True, "data": {"ticker": "AAPL", "category": "momentum", "factors": {...}}}

        ticker_factors(ticker="MSFT", category="all")
        >>> {"success": True, "data": {"ticker": "MSFT", "category": "all", "factors": {...}}}

    Raises:
        ValueError: If ticker has no available price data
    """
    try:
        ticker = ticker.upper().strip()
        ticker_obj = build_ticker_obj(ticker, years_back, fundamentals=True)
        all_factors = ticker_obj.factors

        if category == "all":
            factors_out = all_factors.model_dump()
        else:
            cat_data = getattr(all_factors, category)
            if cat_data is None:
                return error_response(
                    f"No {category} factors available for {ticker}. "
                    f"This category requires fundamentals data which may not be available."
                )
            factors_out = {category: cat_data.model_dump()}

        return success_response({
            "ticker": ticker,
            "category": category,
            "years_back": years_back,
            "factors": factors_out,
        })

    except Exception as e:
        return error_response(f"Failed to compute factor exposures for {ticker}: {str(e)}")


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print(ticker_factors(ticker="AAPL", category="all"))
