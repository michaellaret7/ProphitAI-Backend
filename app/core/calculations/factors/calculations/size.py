"""Size factor calculations (fundamentals-based)."""

import math
import numpy as np

from app.core.calculations.factors.prep import FundamentalData
from app.core.calculations.models.factors import SizeFactors


# ================================
# --> Individual factor funcs
# ================================

def calc_market_cap(shares: float, price: float) -> float | None:
    """Market capitalization: shares outstanding × price."""
    if np.isnan(shares) or np.isnan(price) or shares <= 0 or price <= 0:
        return None
    return shares * price


def calc_log_market_cap(market_cap: float) -> float | None:
    """Natural log of market cap (Fama-French SMB)."""
    if np.isnan(market_cap) or market_cap <= 0:
        return None
    return math.log(market_cap)


# ================================
# --> Orchestrator
# ================================

def calc_size_factors(data: FundamentalData) -> SizeFactors:
    """Calculate all size factor exposures from fundamental data."""
    mcap = data.market_cap if not np.isnan(data.market_cap) else None
    log_mcap = calc_log_market_cap(data.market_cap) if mcap is not None else None

    return SizeFactors(
        market_cap=mcap,
        log_market_cap=log_mcap,
    )
