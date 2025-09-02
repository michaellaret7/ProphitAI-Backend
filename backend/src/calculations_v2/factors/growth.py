from __future__ import annotations

from typing import Optional

from backend.src.calculations_v2.core.data_service import DataService
from backend.src.calculations_v2.core.models import FundamentalData
import numpy as np
from scipy import stats


class GrowthFactors:
    """Growth factor calculations backed by DataService fundamentals.

    Computes: EPS growth rate, EPS CAGR, revenue growth, sales trend growth factor,
    FCF growth, PEG, ROE growth, ROIC growth, book value per share growth,
    operating cash flow growth.
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

        # Most recent and previous values (null-safe)
        self.curr_eps = ists[0].eps if ists else None
        self.prev_eps = ists[1].eps if len(ists) > 1 else None
        self.beg_eps = ists[-1].eps if ists else None
        self.years = len(ists) / 4 if ists else 0

        self.curr_rev = ists[0].revenue if ists else None
        self.prev_rev = ists[1].revenue if len(ists) > 1 else None

        self.rev_series = [float(x.revenue) for x in ists if getattr(x, 'revenue', None) is not None] if ists else []

        self.curr_fcf = cfs[0].freeCashFlow if cfs else None
        self.prev_fcf = cfs[1].freeCashFlow if len(cfs) > 1 else None

        self.pe_ratio = frs[0].priceEarningsRatio if frs else None

        self.curr_roe = frs[0].returnOnEquity if frs else None
        self.prev_roe = frs[1].returnOnEquity if len(frs) > 1 else None

        self.curr_roic = frs[0].returnOnCapitalEmployed if frs else None
        self.prev_roic = frs[1].returnOnCapitalEmployed if len(frs) > 1 else None

        # Book value per share from equity / shares
        try:
            if bss and ists and ists[0].weightedAverageShsOut:
                curr_bvps = float(bss[0].totalStockholdersEquity) / float(ists[0].weightedAverageShsOut)
            else:
                curr_bvps = None
        except Exception:
            curr_bvps = None

        try:
            if len(bss) > 1 and len(ists) > 1 and ists[1].weightedAverageShsOut:
                prev_bvps = float(bss[1].totalStockholdersEquity) / float(ists[1].weightedAverageShsOut)
            else:
                prev_bvps = None
        except Exception:
            prev_bvps = None

        self.curr_bvps = curr_bvps
        self.prev_bvps = prev_bvps

        self.curr_ocf = cfs[0].netCashProvidedByOperatingActivities if cfs else None
        self.prev_ocf = cfs[1].netCashProvidedByOperatingActivities if len(cfs) > 1 else None

    # ------------------------- Metrics ------------------------- #
    def eps_growth_rate(self) -> float:
        if self.curr_eps is None or self.prev_eps is None or self.prev_eps == 0:
            return np.nan if self.curr_eps == 0 else np.inf
        return float((self.curr_eps - self.prev_eps) / abs(self.prev_eps) * 100)

    def eps_cagr(self) -> float:
        if self.curr_eps is None or self.beg_eps is None or self.beg_eps <= 0 or self.curr_eps <= 0 or self.years <= 0:
            return np.nan
        return float((self.curr_eps / self.beg_eps) ** (1 / self.years) - 1)

    def revenue_growth_rate(self) -> float:
        if self.curr_rev is None or self.prev_rev is None or self.prev_rev == 0:
            return np.nan if self.curr_rev == 0 else np.inf
        return float((self.curr_rev - self.prev_rev) / abs(self.prev_rev) * 100)

    def sales_trend_growth_factor(self) -> float:
        if len(self.rev_series) < 2:
            return np.nan
        x = np.arange(len(self.rev_series))
        slope, *_ = stats.linregress(x, self.rev_series)
        avg_abs_sales = np.mean(np.abs(self.rev_series))
        if avg_abs_sales == 0:
            return np.nan
        return float(slope / avg_abs_sales)

    def fcf_growth_rate(self) -> float:
        if self.curr_fcf is None or self.prev_fcf is None or self.prev_fcf == 0:
            return np.nan if self.curr_fcf == 0 else np.inf
        return float((self.curr_fcf - self.prev_fcf) / abs(self.prev_fcf) * 100)

    def peg_ratio(self) -> float:
        if self.pe_ratio is None:
            return np.nan
        eps_growth = self.eps_growth_rate()
        if eps_growth == 0 or np.isnan(eps_growth):
            return np.nan
        return float(self.pe_ratio / eps_growth)

    def roe_growth_rate(self) -> float:
        if self.curr_roe is None or self.prev_roe is None or self.prev_roe == 0:
            return np.nan if self.curr_roe == 0 else np.inf
        return float((self.curr_roe - self.prev_roe) / abs(self.prev_roe) * 100)

    def roic_growth_rate(self) -> float:
        if self.curr_roic is None or self.prev_roic is None or self.prev_roic == 0:
            return np.nan if self.curr_roic == 0 else np.inf
        return float((self.curr_roic - self.prev_roic) / abs(self.prev_roic) * 100)

    def book_value_growth_rate(self) -> float:
        if self.curr_bvps is None or self.prev_bvps is None or self.prev_bvps == 0:
            return np.nan if self.curr_bvps == 0 else np.inf
        return float((self.curr_bvps - self.prev_bvps) / abs(self.prev_bvps) * 100)

    def ocf_growth_rate(self) -> float:
        if self.curr_ocf is None or self.prev_ocf is None or self.prev_ocf == 0:
            return np.nan if self.curr_ocf == 0 else np.inf
        return float((self.curr_ocf - self.prev_ocf) / abs(self.prev_ocf) * 100)


