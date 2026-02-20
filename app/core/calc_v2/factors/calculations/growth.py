"""Growth factor calculations (fundamentals-based).

All functions take scalar values and return float | None.
"""

import numpy as np

from app.core.calc_v2.factors.prep import FundamentalData
from app.core.calc_v2.models.factors import GrowthFactors
from app.core.calc_v2.utils import safe_divide


# ================================
# --> Individual factor funcs
# ================================

def calc_revenue_growth_yoy(curr_revenue: float, prev_revenue: float) -> float | None:
    """Year-over-year revenue growth: (curr - prev) / |prev|."""
    if np.isnan(curr_revenue) or np.isnan(prev_revenue) or prev_revenue == 0:
        return None
    return (curr_revenue - prev_revenue) / abs(prev_revenue)


def calc_earnings_growth_yoy(curr_eps: float, prev_eps: float) -> float | None:
    """Year-over-year earnings growth: (curr - prev) / |prev|."""
    if np.isnan(curr_eps) or np.isnan(prev_eps) or prev_eps == 0:
        return None
    return (curr_eps - prev_eps) / abs(prev_eps)


def calc_fcf_growth_yoy(curr_fcf: float, prev_fcf: float) -> float | None:
    """Year-over-year free cash flow growth: (curr - prev) / |prev|."""
    if np.isnan(curr_fcf) or np.isnan(prev_fcf) or prev_fcf == 0:
        return None
    return (curr_fcf - prev_fcf) / abs(prev_fcf)


def calc_forward_eps_growth(forward_eps: float, ttm_eps: float) -> float | None:
    """Forward EPS growth: (FY1 estimate - TTM) / |TTM|."""
    if np.isnan(forward_eps) or np.isnan(ttm_eps) or ttm_eps == 0:
        return None
    return (forward_eps - ttm_eps) / abs(ttm_eps)


def calc_sustainable_growth_rate(roe: float | None, payout_ratio: float) -> float | None:
    """Sustainable growth rate: ROE × (1 - payout ratio).

    Represents maximum growth rate achievable without external financing.
    """
    if roe is None or np.isnan(payout_ratio):
        return None
    # Reason: payout_ratio > 1 means paying more than earnings (unsustainable but valid signal)
    return roe * (1.0 - payout_ratio)


# ================================
# --> Orchestrator
# ================================

def calc_growth_factors(data: FundamentalData) -> GrowthFactors:
    """Calculate all growth factor exposures from fundamental data."""
    roe = safe_divide(data.net_income, data.total_equity)
    roe_val = None if np.isnan(roe) else roe

    return GrowthFactors(
        revenue_growth_yoy=calc_revenue_growth_yoy(data.revenue, data.prev_revenue),
        earnings_growth_yoy=calc_earnings_growth_yoy(data.eps_diluted, data.prev_eps_diluted),
        fcf_growth_yoy=calc_fcf_growth_yoy(data.free_cf, data.prev_free_cf),
        forward_eps_growth=calc_forward_eps_growth(data.forward_eps, data.eps_diluted),
        sustainable_growth_rate=calc_sustainable_growth_rate(roe_val, data.payout_ratio),
    )
