"""Ticker-level factor orchestrator — computes all factor categories for a single ticker."""

import pandas as pd

from app.repositories.fundamentals.models import FundamentalsResult
from app.core.calc_v2.factors.prep import extract_fundamental_data
from app.core.calc_v2.factors.momentum import calc_momentum_factors
from app.core.calc_v2.factors.volatility import calc_volatility_factors
from app.core.calc_v2.factors.value import calc_value_factors
from app.core.calc_v2.factors.quality import calc_quality_factors
from app.core.calc_v2.factors.growth import calc_growth_factors
from app.core.calc_v2.factors.size import calc_size_factors
from app.core.calc_v2.models.factors import TickerFactors


def calc_all_factors(
    adj_close: pd.Series,
    daily_returns: pd.Series,
    benchmark_returns: pd.Series | None = None,
    fundamentals: FundamentalsResult | None = None,
    price: float | None = None,
) -> TickerFactors:
    """Calculate all factor exposures for a single ticker.

    Args:
        adj_close: Adjusted close price series.
        daily_returns: Daily return series (from adj_close).
        benchmark_returns: Benchmark daily returns (for beta/idiosyncratic vol).
        fundamentals: FundamentalsResult containing statement data (optional).
        price: Current stock price. Defaults to last adj_close if not provided.

    Returns:
        TickerFactors with momentum + volatility always populated,
        and value/quality/growth/size populated when fundamentals are provided.
    """
    # Always compute price-based factors
    momentum = calc_momentum_factors(adj_close, daily_returns)
    volatility = calc_volatility_factors(adj_close, daily_returns, benchmark_returns)

    # Compute fundamental-based factors if data provided
    value = quality = growth = size = None
    if fundamentals is not None:
        px = price if price is not None else float(adj_close.iloc[-1])
        data = extract_fundamental_data(fundamentals, px)
        value = calc_value_factors(data)
        quality = calc_quality_factors(data)
        growth = calc_growth_factors(data)
        size = calc_size_factors(data)

    return TickerFactors(
        momentum=momentum,
        volatility=volatility,
        value=value,
        quality=quality,
        growth=growth,
        size=size,
    )
