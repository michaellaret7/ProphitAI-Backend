"""Quality factor calculations (fundamentals-based).

All functions take scalar values and return float | None.
"""

import numpy as np

from app.core.calc_v2.factors.prep import FundamentalData
from app.core.calc_v2.models.factors import QualityFactors
from app.core.calc_v2.utils import safe_divide


# ================================
# --> Individual factor funcs
# ================================

def calc_gross_profitability(gross_profit: float, total_assets: float) -> float | None:
    """Gross profitability: GP / Total Assets (Novy-Marx)."""
    result = safe_divide(gross_profit, total_assets)
    return None if np.isnan(result) else result


def calc_roe(net_income: float, equity: float) -> float | None:
    """Return on equity: NI / Equity (QMJ)."""
    result = safe_divide(net_income, equity)
    return None if np.isnan(result) else result


def calc_roa(net_income: float, total_assets: float) -> float | None:
    """Return on assets: NI / Total Assets (QMJ)."""
    result = safe_divide(net_income, total_assets)
    return None if np.isnan(result) else result


def calc_accrual_ratio(net_income: float, operating_cf: float, total_assets: float) -> float | None:
    """Accrual ratio: -(NI - OCF) / Total Assets (Sloan).

    Lower accruals = higher quality (cash earnings > accounting earnings).
    """
    if np.isnan(net_income) or np.isnan(operating_cf) or np.isnan(total_assets):
        return None
    if total_assets == 0:
        return None
    return -(net_income - operating_cf) / total_assets


def calc_debt_to_equity(total_debt: float, equity: float) -> float | None:
    """Debt-to-equity ratio: Total Debt / Equity."""
    result = safe_divide(total_debt, equity)
    return None if np.isnan(result) else result


def calc_interest_coverage(ebit: float, interest_expense: float) -> float | None:
    """Interest coverage: EBIT / Interest Expense."""
    if np.isnan(interest_expense) or interest_expense == 0:
        return None
    # Reason: interest_expense is sometimes stored as positive, sometimes negative
    denom = abs(interest_expense) if interest_expense < 0 else interest_expense
    result = safe_divide(ebit, denom)
    return None if np.isnan(result) else result


def calc_altman_z(
    working_capital: float,
    retained_earnings: float,
    ebit: float,
    market_cap: float,
    revenue: float,
    total_assets: float,
    total_liabilities: float,
) -> float | None:
    """Altman Z-Score: 1.2×WC/A + 1.4×RE/A + 3.3×EBIT/A + 0.6×MVE/TL + 1.0×S/A.

    Predicts bankruptcy risk. Z > 2.99 = safe, Z < 1.81 = distress.
    """
    if np.isnan(total_assets) or total_assets == 0:
        return None
    if np.isnan(total_liabilities) or total_liabilities == 0:
        return None

    vals = [working_capital, retained_earnings, ebit, market_cap, revenue]
    if any(np.isnan(v) for v in vals):
        return None

    z = (
        1.2 * (working_capital / total_assets)
        + 1.4 * (retained_earnings / total_assets)
        + 3.3 * (ebit / total_assets)
        + 0.6 * (market_cap / total_liabilities)
        + 1.0 * (revenue / total_assets)
    )
    return z


# ================================
# --> Orchestrator
# ================================

def calc_quality_factors(data: FundamentalData) -> QualityFactors:
    """Calculate all quality factor exposures from fundamental data."""
    return QualityFactors(
        gross_profitability=calc_gross_profitability(data.gross_profit, data.total_assets),
        roe=calc_roe(data.net_income, data.total_equity),
        roa=calc_roa(data.net_income, data.total_assets),
        accrual_ratio=calc_accrual_ratio(data.net_income, data.operating_cf, data.total_assets),
        debt_to_equity=calc_debt_to_equity(data.total_debt, data.total_equity),
        interest_coverage=calc_interest_coverage(data.ebit, data.interest_expense),
        altman_z_score=calc_altman_z(
            data.working_capital,
            data.retained_earnings,
            data.ebit,
            data.market_cap,
            data.revenue,
            data.total_assets,
            data.total_liabilities,
        ),
    )
