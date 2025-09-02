from __future__ import annotations

from typing import Optional

import numpy as np

from backend.src.calculations_v2.core.data_service import DataService
from backend.src.calculations_v2.core.models import FundamentalData
from backend.src.utils.ticker_utils import get_most_recent_price


class QualityFactors:
    """Quality factor calculations using DataService fundamentals.

    Metrics: ROE, ROA, ROIC, gross profitability, gross/net/FCF margins, D/E,
    net debt/EBITDA, interest coverage, quick ratio, Altman Z, accruals, earnings
    stability, EPS revision 3m, dividend payout, asset turnover, cash conversion,
    cash flow to debt, conservative financing, ROCE.
    """

    def __init__(self, ticker: str, data_service: DataService | None = None):
        self.ticker = ticker.upper()
        self.ds = data_service or DataService()
        self.fund: FundamentalData = self.ds.get_fundamentals(self.ticker)

        ists = self.fund.income_statements
        bss = self.fund.balance_sheets
        cfs = self.fund.cash_flow_statements
        frs = self.fund.financial_ratios
        ests = self.fund.analyst_estimates

        # Basics
        self.net_income = float(ists[0].netIncome) if ists and ists[0].netIncome is not None else None
        self.revenue = float(ists[0].revenue) if ists and ists[0].revenue is not None else None
        self.gross_profit = float(ists[0].grossProfit) if ists and ists[0].grossProfit is not None else None
        self.ebit = float(ists[0].operatingIncome) if ists and ists[0].operatingIncome is not None else None
        self.ebitda = float(ists[0].ebitda) if ists and ists[0].ebitda is not None else None
        self.interest_expense = float(ists[0].interestExpense) if ists and ists[0].interestExpense is not None else None
        self.eps = float(ists[0].eps) if ists and ists[0].eps is not None else None

        # Balance sheet
        self.total_assets = float(bss[0].totalAssets) if bss and bss[0].totalAssets is not None else None
        self.total_equity = float(bss[0].totalStockholdersEquity) if bss and bss[0].totalStockholdersEquity is not None else None
        self.total_debt = float(bss[0].totalDebt) if bss and bss[0].totalDebt is not None else None
        self.current_assets = float(bss[0].totalCurrentAssets) if bss and bss[0].totalCurrentAssets is not None else None
        self.current_liabilities = float(bss[0].totalCurrentLiabilities) if bss and bss[0].totalCurrentLiabilities is not None else None
        self.inventory = float(bss[0].inventory) if bss and bss[0].inventory is not None else None
        self.cash_and_equivalents = float(bss[0].cashAndCashEquivalents) if bss and bss[0].cashAndCashEquivalents is not None else None
        self.retained_earnings = float(bss[0].retainedEarnings) if bss and bss[0].retainedEarnings is not None else None
        self.total_liabilities = float(bss[0].totalLiabilities) if bss and bss[0].totalLiabilities is not None else None

        # Cash flow
        self.free_cash_flow = float(cfs[0].freeCashFlow) if cfs and cfs[0].freeCashFlow is not None else None
        self.operating_cash_flow = (
            float(cfs[0].netCashProvidedByOperatingActivities) if cfs and cfs[0].netCashProvidedByOperatingActivities is not None else None
        )
        self.dividends = float(cfs[0].dividendsPaid) if cfs and cfs[0].dividendsPaid is not None else None

        # Ratios & series
        self.return_on_equity_ratio = float(frs[0].returnOnEquity) if frs and frs[0].returnOnEquity is not None else None
        self.return_on_capital_employed_ratio = (
            float(frs[0].returnOnCapitalEmployed) if frs and frs[0].returnOnCapitalEmployed is not None else None
        )

        # EPS timeseries for stability
        self.eps_quarterly_8 = [float(x.eps) for x in ists[:8] if getattr(x, 'eps', None) is not None] if ists else []

        # EPS estimates for revisions
        self.eps_estimate_now = float(ests[0].epsAvg) if ests and ests[0].epsAvg is not None else None
        self.eps_estimate_3m_ago = float(ests[1].epsAvg) if len(ests) > 1 and ests[1].epsAvg is not None else None

        # Shares and market cap
        self.shares_outstanding = (
            float(ists[0].weightedAverageShsOut) if ists and ists[0].weightedAverageShsOut is not None else None
        )
        price = get_most_recent_price(self.ticker)
        self.market_value_equity = (self.shares_outstanding * price) if self.shares_outstanding and price else None

        # Working capital & invested capital
        self.working_capital = (
            (self.current_assets - self.current_liabilities)
            if self.current_assets is not None and self.current_liabilities is not None
            else None
        )
        self.nopat = (self.ebit * (1 - 0.21)) if self.ebit is not None else None
        self.invested_capital = (
            (self.total_equity + self.total_debt - self.cash_and_equivalents)
            if self.total_equity is not None and self.total_debt is not None and self.cash_and_equivalents is not None
            else None
        )

    # ------------------ Profitability & Margins ------------------ #
    def return_on_equity(self) -> Optional[float]:
        if self.total_equity is None or self.net_income is None or self.total_equity <= 0:
            return None
        return self.net_income / self.total_equity

    def return_on_assets(self) -> Optional[float]:
        if self.total_assets is None or self.net_income is None or self.total_assets <= 0:
            return None
        return self.net_income / self.total_assets

    def roic(self) -> Optional[float]:
        if self.invested_capital is None or self.nopat is None or self.invested_capital <= 0:
            return None
        return self.nopat / self.invested_capital

    def gross_profitability(self) -> Optional[float]:
        if self.total_assets is None or self.gross_profit is None or self.total_assets <= 0:
            return None
        return self.gross_profit / self.total_assets

    def gross_margin(self) -> Optional[float]:
        if self.revenue is None or self.gross_profit is None or self.revenue == 0:
            return None
        return self.gross_profit / self.revenue

    def net_margin(self) -> Optional[float]:
        if self.revenue is None or self.net_income is None or self.revenue == 0:
            return None
        return self.net_income / self.revenue

    def fcf_margin(self) -> Optional[float]:
        if self.revenue is None or self.free_cash_flow is None or self.revenue == 0:
            return None
        return self.free_cash_flow / self.revenue

    # -------------------------- Leverage ------------------------- #
    def debt_to_equity(self) -> Optional[float]:
        if self.total_equity is None or self.total_debt is None or self.total_equity == 0:
            return None
        return self.total_debt / self.total_equity

    def net_debt_to_ebitda(self) -> Optional[float]:
        if self.ebitda is None or self.total_debt is None or self.cash_and_equivalents is None or self.ebitda <= 0:
            return None
        net_debt = self.total_debt - self.cash_and_equivalents
        return net_debt / self.ebitda

    def interest_coverage(self) -> Optional[float]:
        if self.ebit is None or self.interest_expense is None or self.interest_expense <= 0:
            return None
        return self.ebit / self.interest_expense

    def quick_ratio(self) -> Optional[float]:
        if (
            self.current_assets is None
            or self.inventory is None
            or self.current_liabilities is None
            or self.current_liabilities == 0
        ):
            return None
        return (self.current_assets - self.inventory) / self.current_liabilities

    # ------------------------ Altman Z-Score ---------------------- #
    def altman_z_score(self) -> Optional[float]:
        if (
            self.total_assets is None
            or self.total_liabilities is None
            or self.total_assets == 0
            or self.total_liabilities == 0
            or self.working_capital is None
            or self.retained_earnings is None
            or self.ebit is None
            or self.revenue is None
            or self.market_value_equity is None
        ):
            return None
        wc_ta = self.working_capital / self.total_assets
        re_ta = self.retained_earnings / self.total_assets
        ebit_ta = self.ebit / self.total_assets
        mve_tl = self.market_value_equity / self.total_liabilities
        sales_ta = self.revenue / self.total_assets
        z = 1.2 * wc_ta + 1.4 * re_ta + 3.3 * ebit_ta + 0.6 * mve_tl + 1.0 * sales_ta
        return z

    # ---------------------- Earnings Quality --------------------- #
    def accruals_ratio(self) -> Optional[float]:
        if self.total_assets is None or self.net_income is None or self.operating_cash_flow is None or self.total_assets == 0:
            return None
        return (self.net_income - self.operating_cash_flow) / self.total_assets

    def earnings_stability(self) -> Optional[float]:
        if len(self.eps_quarterly_8) < 4:
            return None
        eps_arr = np.array(self.eps_quarterly_8, dtype=float)
        mean_eps = eps_arr.mean()
        if mean_eps == 0 or np.isnan(mean_eps):
            return None
        return float(eps_arr.std(ddof=0) / abs(mean_eps))

    def eps_revision_3m(self) -> Optional[float]:
        if self.eps_estimate_now is None or self.eps_estimate_3m_ago is None or self.eps_estimate_3m_ago == 0:
            return None
        return (self.eps_estimate_now - self.eps_estimate_3m_ago) / self.eps_estimate_3m_ago

    def dividend_payout(self) -> Optional[float]:
        if self.net_income is None or self.dividends is None or self.net_income == 0:
            return None
        return self.dividends / self.net_income

    # ------------------------- Efficiency ------------------------ #
    def asset_turnover(self) -> Optional[float]:
        if self.total_assets is None or self.revenue is None or self.total_assets == 0:
            return None
        return self.revenue / self.total_assets

    def cash_conversion_ratio(self) -> Optional[float]:
        if self.net_income is None or self.operating_cash_flow is None or self.net_income == 0:
            return None
        return self.operating_cash_flow / self.net_income

    def cash_flow_to_debt_ratio(self) -> Optional[float]:
        if self.total_debt is None or self.operating_cash_flow is None or self.total_debt == 0:
            return None
        return self.operating_cash_flow / self.total_debt

    def conservative_financing(self) -> Optional[bool]:
        if self.total_debt is None or self.total_assets is None:
            return None
        return self.total_debt < self.total_assets

    def return_on_capital_employed(self) -> Optional[float]:
        if self.total_assets is None or self.current_liabilities is None or self.ebit is None:
            return None
        capital_employed = self.total_assets - self.current_liabilities
        if capital_employed == 0:
            return None
        return self.ebit / capital_employed


