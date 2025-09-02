from __future__ import annotations

from typing import Optional

from backend.src.calculations_v2.core.data_service import DataService
from backend.src.calculations_v2.core.models import FundamentalData
from backend.src.utils.ticker_utils import get_most_recent_price


class ValueFactors:
    """Value factor calculations using the unified DataService fundamentals.

    Mirrors legacy value factors: P/B, B/M, trailing/forward P/E, earnings yield,
    P/S, P/CF, FCF yield, EV/EBITDA, EV/EBIT, dividend yield, PEG.
    """

    def __init__(self, ticker: str, data_service: DataService | None = None):
        self.ticker = ticker.upper()
        self.ds = data_service or DataService()
        self.fund: FundamentalData = self.ds.get_fundamentals(self.ticker)

        # Current price
        self.price: Optional[float] = get_most_recent_price(self.ticker)

        # Convenience aliases
        ists = self.fund.income_statements
        bss = self.fund.balance_sheets
        cfs = self.fund.cash_flow_statements
        frs = self.fund.financial_ratios
        ests = self.fund.analyst_estimates

        # Safely extract latest values similar to legacy code
        self.eps_ttm = float(ists[0].eps) if ists and ists[0].eps is not None else None
        self.eps_forward_next_fy = float(ests[0].epsAvg) if ests and ests[0].epsAvg is not None else None
        self.shares_outstanding = (
            float(ists[0].weightedAverageShsOut) if ists and ists[0].weightedAverageShsOut is not None else None
        )
        self.revenue_ttm = float(ists[0].revenue) if ists and ists[0].revenue is not None else None

        self.operating_cash_flow_ttm = (
            float(cfs[0].netCashProvidedByOperatingActivities) if cfs and cfs[0].netCashProvidedByOperatingActivities is not None else None
        )
        self.free_cash_flow_ttm = float(cfs[0].freeCashFlow) if cfs and cfs[0].freeCashFlow is not None else None

        self.ebitda_ttm = float(ists[0].ebitda) if ists and ists[0].ebitda is not None else None
        self.ebit_ttm = float(ists[0].operatingIncome) if ists and ists[0].operatingIncome is not None else None

        self.total_debt = float(bss[0].totalDebt) if bss and bss[0].totalDebt is not None else None
        self.cash_and_equivalents = (
            float(bss[0].cashAndCashEquivalents) if bss and bss[0].cashAndCashEquivalents is not None else None
        )

        # Book value per share from equity / shares
        try:
            if bss and ists and ists[0].weightedAverageShsOut:
                self.book_value_per_share = float(bss[0].totalStockholdersEquity) / float(ists[0].weightedAverageShsOut)
            else:
                self.book_value_per_share = None
        except Exception:
            self.book_value_per_share = None

        # Dividends paid are negative in cash flow; we use absolute value later
        self.dividends = float(cfs[0].dividendsPaid) if cfs and cfs[0].dividendsPaid is not None else None

        # 5y EPS growth for PEG (reuse legacy logic when enough quarters exist)
        if ists and len(ists) >= 20 and ists[0].eps is not None and ists[19].eps is not None:
            try:
                curr = float(ists[0].eps)
                prev5y = float(ists[19].eps)
                if prev5y > 0 and curr > 0:
                    ratio = curr / prev5y
                    self.eps_growth_5yr = (ratio ** (1 / 5) - 1) * 100
                else:
                    self.eps_growth_5yr = None
            except Exception:
                self.eps_growth_5yr = None
        else:
            self.eps_growth_5yr = None

    # ------------------------- Value Ratios ------------------------- #
    def price_to_book(self) -> Optional[float]:
        if self.book_value_per_share is None or self.price is None or self.book_value_per_share <= 0:
            return None
        return self.price / self.book_value_per_share

    def book_to_market(self) -> Optional[float]:
        if self.price is None or self.book_value_per_share is None or self.price <= 0:
            return None
        return self.book_value_per_share / self.price

    def trailing_pe(self) -> Optional[float]:
        if self.eps_ttm is None or self.price is None or self.eps_ttm == 0:
            return None
        return self.price / self.eps_ttm

    def forward_pe(self) -> Optional[float]:
        if self.eps_forward_next_fy is None or self.price is None or self.eps_forward_next_fy == 0:
            return None
        return self.price / self.eps_forward_next_fy

    def earnings_yield(self) -> Optional[float]:
        if self.price is None or self.eps_forward_next_fy is None or self.price == 0:
            return None
        return self.eps_forward_next_fy / self.price

    def price_to_sales(self) -> Optional[float]:
        if self.revenue_ttm is None or self.shares_outstanding is None or self.shares_outstanding == 0 or self.price is None:
            return None
        revenue_per_share = self.revenue_ttm / self.shares_outstanding
        if revenue_per_share <= 0:
            return None
        return self.price / revenue_per_share

    def price_to_cashflow(self) -> Optional[float]:
        if (
            self.operating_cash_flow_ttm is None
            or self.shares_outstanding is None
            or self.shares_outstanding == 0
            or self.price is None
        ):
            return None
        ocf_per_share = self.operating_cash_flow_ttm / self.shares_outstanding
        if ocf_per_share <= 0:
            return None
        return self.price / ocf_per_share

    def free_cashflow_yield(self) -> Optional[float]:
        if self.shares_outstanding is None or self.price is None or self.free_cash_flow_ttm is None:
            return None
        market_cap = self.shares_outstanding * self.price
        if market_cap == 0:
            return None
        return self.free_cash_flow_ttm / market_cap

    def ev_to_ebitda(self) -> Optional[float]:
        if (
            self.shares_outstanding is None
            or self.price is None
            or self.total_debt is None
            or self.cash_and_equivalents is None
            or self.ebitda_ttm is None
        ):
            return None
        market_cap = self.shares_outstanding * self.price
        net_debt = self.total_debt - self.cash_and_equivalents
        enterprise_value = market_cap + net_debt
        if self.ebitda_ttm <= 0:
            return None
        return enterprise_value / self.ebitda_ttm

    def ev_to_ebit(self) -> Optional[float]:
        if (
            self.shares_outstanding is None
            or self.price is None
            or self.total_debt is None
            or self.cash_and_equivalents is None
            or self.ebit_ttm is None
        ):
            return None
        market_cap = self.shares_outstanding * self.price
        net_debt = self.total_debt - self.cash_and_equivalents
        enterprise_value = market_cap + net_debt
        if self.ebit_ttm <= 0:
            return None
        return enterprise_value / self.ebit_ttm

    def dividend_yield(self) -> Optional[float]:
        if (
            self.price is None
            or self.dividends is None
            or self.shares_outstanding is None
            or self.price == 0
            or self.shares_outstanding == 0
        ):
            return None
        dividends_per_share = abs(self.dividends) / self.shares_outstanding
        return dividends_per_share / self.price

    def peg_ratio(self) -> Optional[float]:
        if (
            self.price is None
            or self.eps_ttm is None
            or self.eps_growth_5yr is None
            or self.eps_ttm == 0
            or self.eps_growth_5yr <= 0
        ):
            return None
        pe = self.price / self.eps_ttm
        return pe / self.eps_growth_5yr

if __name__ == "__main__":
    # Simple test runner for all value factors
    import json

    ticker = "AAPL"
    vf = ValueFactors(ticker)

    results = {
        "ticker": ticker,
        "price_to_book": vf.price_to_book(),
        "book_to_market": vf.book_to_market(),
        "trailing_pe": vf.trailing_pe(),
        "forward_pe": vf.forward_pe(),
        "earnings_yield": vf.earnings_yield(),
        "price_to_sales": vf.price_to_sales(),
        "price_to_cashflow": vf.price_to_cashflow(),
        "free_cashflow_yield": vf.free_cashflow_yield(),
        "ev_to_ebitda": vf.ev_to_ebitda(),
        "ev_to_ebit": vf.ev_to_ebit(),
        "dividend_yield": vf.dividend_yield(),
        "peg_ratio": vf.peg_ratio(),
    }

    print(json.dumps(results, indent=2, default=lambda o: None))


