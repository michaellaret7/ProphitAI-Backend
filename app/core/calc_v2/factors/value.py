"""Value factor calculations (fundamentals-based).

All functions take scalar values and return float | None.
"""

import numpy as np

from app.core.calc_v2.factors.prep import FundamentalData
from app.core.calc_v2.models.factors import ValueFactors
from app.core.calculations.core.helpers import safe_divide


# ================================
# --> Individual factor funcs
# ================================

def calc_earnings_yield(eps_ttm: float, price: float) -> float | None:
    """Earnings yield: EPS / Price (inverse P/E)."""
    result = safe_divide(eps_ttm, price)
    return None if np.isnan(result) else result


def calc_book_to_price(equity: float, shares: float, price: float) -> float | None:
    """Book-to-price: (Equity / Shares) / Price (Fama-French HML)."""
    bvps = safe_divide(equity, shares)
    if np.isnan(bvps):
        return None
    result = safe_divide(bvps, price)
    return None if np.isnan(result) else result


def calc_fcf_yield(fcf_ttm: float, market_cap: float) -> float | None:
    """Free cash flow yield: FCF / Market Cap."""
    result = safe_divide(fcf_ttm, market_cap)
    return None if np.isnan(result) else result


def calc_ebitda_to_ev(ebitda_ttm: float, ev: float) -> float | None:
    """EBITDA / Enterprise Value (MSCI Barra style)."""
    result = safe_divide(ebitda_ttm, ev)
    return None if np.isnan(result) else result


def calc_dividend_yield(dividends_ttm: float, market_cap: float) -> float | None:
    """Dividend yield: |Dividends Paid| / Market Cap.

    dividends_paid is typically negative in cash flow statements.
    """
    if np.isnan(dividends_ttm) or np.isnan(market_cap) or market_cap <= 0:
        return None
    result = safe_divide(abs(dividends_ttm), market_cap)
    return None if np.isnan(result) else result


# ================================
# --> Orchestrator
# ================================

def calc_value_factors(data: FundamentalData) -> ValueFactors:
    """Calculate all value factor exposures from fundamental data."""
    return ValueFactors(
        earnings_yield=calc_earnings_yield(data.eps_diluted, data.price),
        book_to_price=calc_book_to_price(data.total_equity, data.shares_outstanding, data.price),
        fcf_yield=calc_fcf_yield(data.free_cf, data.market_cap),
        ebitda_to_ev=calc_ebitda_to_ev(data.ebitda, data.enterprise_value),
        dividend_yield=calc_dividend_yield(data.dividends_paid, data.market_cap),
    )
