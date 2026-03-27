"""Volatility / low-risk factor calculations (price-based).

Reuses calc_beta and calc_idiosyncratic_vol from risk/benchmark.py,
calc_close_to_close_volatility from technicals/volatility.py,
and calc_max_drawdown from risk/drawdown.py.
"""

import numpy as np
import pandas as pd

from prophitai_calculations.factors.config import VOL_1Y_WINDOW, VOL_3M_WINDOW
from prophitai_calculations.risk.benchmark import (
    calc_beta as _calc_beta,
    calc_idiosyncratic_vol as _calc_idiosyncratic_vol,
)
from prophitai_calculations.risk.drawdown import calc_max_drawdown as _calc_max_drawdown
from prophitai_calculations.technicals.volatility import calc_close_to_close_volatility
from prophitai_calculations.models.factors import VolatilityFactors


# ================================
# --> Helper funcs
# ================================

def _last_vol(close: pd.Series, window: int) -> float | None:
    """Extract the most recent scalar annualized volatility from the rolling Series."""
    vol_series = calc_close_to_close_volatility(close, window=window, annualize=True)
    if vol_series.empty:
        return None
    val = float(vol_series.iloc[-1])
    return None if np.isnan(val) else val


# ================================
# --> Orchestrator
# ================================

def calc_volatility_factors(
    prices: pd.Series,
    daily_returns: pd.Series,
    bench_returns: pd.Series | None = None,
) -> VolatilityFactors:
    """Calculate all volatility factor exposures for a single ticker."""
    beta = None
    ivol = None

    if bench_returns is not None:
        beta = _calc_beta(daily_returns, bench_returns)
        ivol = _calc_idiosyncratic_vol(daily_returns, bench_returns, lookback=VOL_1Y_WINDOW)

    # Reason: risk/drawdown returns negative values; factor model expects positive
    mdd = _calc_max_drawdown(daily_returns, lookback=VOL_1Y_WINDOW)

    return VolatilityFactors(
        realized_vol_1y=_last_vol(prices, VOL_1Y_WINDOW),
        realized_vol_3m=_last_vol(prices, VOL_3M_WINDOW),
        beta=beta,
        idiosyncratic_vol=ivol,
        max_drawdown_1y=abs(mdd),
    )
