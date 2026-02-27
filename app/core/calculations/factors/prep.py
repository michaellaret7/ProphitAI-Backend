"""Fundamental data preparation for factor calculations.

Extracts all needed values from FundamentalsResult in one pass,
decoupling factor math from ORM attribute names.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.repositories.fundamentals.models import FundamentalsResult
from app.core.calculations.utils import sort_rows_desc_by_date, ttm


@dataclass
class FundamentalData:
    """Flattened snapshot of fundamental data needed by factor functions.

    All monetary values are raw (not per-share) unless noted.
    """
    # ================================
    # --> TTM income items
    # ================================
    revenue: float = np.nan
    gross_profit: float = np.nan
    ebitda: float = np.nan
    ebit: float = np.nan
    net_income: float = np.nan
    interest_expense: float = np.nan
    eps_diluted: float = np.nan

    # ================================
    # --> Balance sheet snapshot (most recent)
    # ================================
    total_assets: float = np.nan
    total_equity: float = np.nan
    total_debt: float = np.nan
    total_liabilities: float = np.nan
    total_current_assets: float = np.nan
    total_current_liabilities: float = np.nan
    retained_earnings: float = np.nan
    shares_outstanding: float = np.nan

    # ================================
    # --> TTM cash flow items
    # ================================
    operating_cf: float = np.nan
    free_cf: float = np.nan
    dividends_paid: float = np.nan

    # ================================
    # --> Prior-period TTM values (for YoY growth)
    # ================================
    prev_revenue: float = np.nan
    prev_eps_diluted: float = np.nan
    prev_free_cf: float = np.nan

    # ================================
    # --> Analyst estimates
    # ================================
    forward_eps: float = np.nan

    # ================================
    # --> Market data
    # ================================
    price: float = np.nan
    market_cap: float = np.nan
    enterprise_value: float = np.nan
    working_capital: float = np.nan

    # ================================
    # --> Financial ratios (most recent)
    # ================================
    payout_ratio: float = np.nan


# ================================
# --> Helper funcs
# ================================

def _safe_attr(obj: object, attr: str) -> float | None:
    """Extract a numeric attribute, returning None if missing or non-numeric."""
    val = getattr(obj, attr, None)
    if val is None:
        return None
    try:
        f = float(val)
        return f if np.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def _ttm_field(rows: list, attr: str, window: int = 4) -> float:
    """Compute TTM sum of a specific attribute across sorted rows."""
    values = [_safe_attr(r, attr) for r in rows]
    return ttm(values, window)


def extract_fundamental_data(fund: FundamentalsResult, price: float) -> FundamentalData:
    """Extract all needed values from FundamentalsResult into FundamentalData.

    Args:
        fund: FundamentalsResult containing lists of statement objects.
        price: Current stock price (typically last adj_close).

    Returns:
        FundamentalData with all fields populated (NaN where data missing).
    """
    data = FundamentalData(price=price)

    # Sort all statement lists by date descending (most recent first)
    inc = sort_rows_desc_by_date(fund.income_statements)
    bs = sort_rows_desc_by_date(fund.balance_sheets)
    cf = sort_rows_desc_by_date(fund.cash_flow_statements)
    ratios = sort_rows_desc_by_date(fund.financial_ratios)
    estimates = sort_rows_desc_by_date(fund.analyst_estimates)

    # ---- TTM income statement items ----
    if len(inc) >= 4:
        data.revenue = _ttm_field(inc, 'revenue')
        data.gross_profit = _ttm_field(inc, 'grossProfit')
        data.ebitda = _ttm_field(inc, 'ebitda')
        data.ebit = _ttm_field(inc, 'operatingIncome')
        data.net_income = _ttm_field(inc, 'netIncome')
        data.interest_expense = _ttm_field(inc, 'interestExpense')
        data.eps_diluted = _ttm_field(inc, 'epsdiluted')

    # ---- Balance sheet snapshot (most recent) ----
    if bs:
        latest_bs = bs[0]
        data.total_assets = _safe_attr(latest_bs, 'totalAssets') or np.nan
        data.total_equity = _safe_attr(latest_bs, 'totalStockholdersEquity') or np.nan
        data.total_debt = _safe_attr(latest_bs, 'totalDebt') or np.nan
        data.total_liabilities = _safe_attr(latest_bs, 'totalLiabilities') or np.nan
        data.total_current_assets = _safe_attr(latest_bs, 'totalCurrentAssets') or np.nan
        data.total_current_liabilities = _safe_attr(latest_bs, 'totalCurrentLiabilities') or np.nan
        data.retained_earnings = _safe_attr(latest_bs, 'retainedEarnings') or np.nan
        data.shares_outstanding = _safe_attr(latest_bs, 'weightedAverageShsOutDil') or np.nan

        # Reason: balance sheet may not have shares — fall back to income statement
        if np.isnan(data.shares_outstanding) and inc:
            data.shares_outstanding = _safe_attr(inc[0], 'weightedAverageShsOutDil') or np.nan

    # ---- TTM cash flow items ----
    if len(cf) >= 4:
        data.operating_cf = _ttm_field(cf, 'operatingCashFlow')
        data.free_cf = _ttm_field(cf, 'freeCashFlow')
        data.dividends_paid = _ttm_field(cf, 'dividendsPaid')

    # ---- Prior-period TTM values (quarters 5-8 for YoY growth) ----
    if len(inc) >= 8:
        data.prev_revenue = _ttm_field(inc[4:], 'revenue')
        data.prev_eps_diluted = _ttm_field(inc[4:], 'epsdiluted')
    if len(cf) >= 8:
        data.prev_free_cf = _ttm_field(cf[4:], 'freeCashFlow')

    # ---- Analyst estimates (next fiscal year forward EPS) ----
    if estimates:
        data.forward_eps = _safe_attr(estimates[0], 'epsAvg') or np.nan

    # ---- Financial ratios (most recent payout ratio) ----
    if ratios:
        data.payout_ratio = _safe_attr(ratios[0], 'payoutRatio') or np.nan

    # ---- Derived market values ----
    if not np.isnan(data.shares_outstanding) and not np.isnan(price):
        data.market_cap = data.shares_outstanding * price

    # Reason: EV = market_cap + total_debt - cash; use balance sheet cash
    if not np.isnan(data.market_cap) and bs:
        cash = _safe_attr(bs[0], 'cashAndCashEquivalents') or 0.0
        debt = data.total_debt if not np.isnan(data.total_debt) else 0.0
        data.enterprise_value = data.market_cap + debt - cash

    # Working capital = current assets - current liabilities
    if not np.isnan(data.total_current_assets) and not np.isnan(data.total_current_liabilities):
        data.working_capital = data.total_current_assets - data.total_current_liabilities

    return data
