from __future__ import annotations

from typing import Optional, Iterable, List, Dict
from datetime import date, timedelta

import numpy as np

from backend.src.calculations_v2.core.data_service import DataService
from backend.src.calculations_v2.core.models import FundamentalData
from backend.src.utils.ticker_utils import get_most_recent_price
import pandas as pd
import numpy as np


class QualityFactors:
    """Quality factor calculations using DataService fundamentals.

    Metrics: ROE, ROA, ROIC, gross profitability, gross/net/FCF margins, D/E,
    net debt/EBITDA, interest coverage, quick ratio, Altman Z, accruals, earnings
    stability, EPS revision 3m, dividend payout, asset turnover, cash conversion,
    cash flow to debt, conservative financing, ROCE.
    """

    def __init__(self, ticker: str, data_service: DataService | None = None, filing_lag_days: int | None = None):
        self.ticker = ticker.upper()
        self.ds = data_service or DataService()
        self.fund: FundamentalData = self.ds.get_fundamentals(self.ticker)

        # Defensive sort by period end date desc
        ists = self._sort_rows_desc_by_date(self.fund.income_statements)
        bss = self._sort_rows_desc_by_date(self.fund.balance_sheets)
        cfs = self._sort_rows_desc_by_date(self.fund.cash_flow_statements)
        frs = self._sort_rows_desc_by_date(self.fund.financial_ratios)
        ests = self._sort_rows_desc_by_date(self.fund.analyst_estimates)

        # Optional filing lag handling: if provided, drop the most recent statements not older than lag
        if filing_lag_days is not None and filing_lag_days > 0:
            lag = timedelta(days=int(filing_lag_days))
            cutoff_date = (ists[0].date - lag) if ists and getattr(ists[0], 'date', None) else None
            if cutoff_date is not None:
                ists = [x for x in ists if getattr(x, 'date', date.min) <= cutoff_date]
                bss = [x for x in bss if getattr(x, 'date', date.min) <= cutoff_date]
                cfs = [x for x in cfs if getattr(x, 'date', date.min) <= cutoff_date]
                frs = [x for x in frs if getattr(x, 'date', date.min) <= cutoff_date]
                ests = [x for x in ests if getattr(x, 'date', date.min) <= cutoff_date]

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

    # ------------------------- Sector adjustments ------------------------- #
    @staticmethod
    def adjust_for_sector(attrs: Dict[str, float], sector: Optional[str]) -> Dict[str, float]:
        if sector is None:
            return attrs
        sec = (sector or '').lower()
        out = dict(attrs)
        if 'financial' in sec or 'bank' in sec or 'insurance' in sec:
            # Downweight or drop EBITDA-dependent and gross profitability for banks/insurers
            out['gp_a'] = np.nan if 'gp_a' in out else np.nan
            # Keep nd_ebitda but allow cross-section z-scoring within sector to neutralize
        if 'utility' in sec:
            # Utilities often have regulated returns; leave metrics but expect sector z-score to normalize
            pass
        return out

    # ------------------------- Winsorize/Z-score helpers ------------------------- #
    @staticmethod
    def winsorize_series(series: pd.Series, lower: float = 0.025, upper: float = 0.025) -> pd.Series:
        if series is None or series.empty:
            return series
        s = series.copy()
        try:
            lo = s.quantile(lower)
            hi = s.quantile(1.0 - upper)
            return s.clip(lower=lo, upper=hi)
        except Exception:
            return s

    @staticmethod
    def zscore_series(series: pd.Series) -> pd.Series:
        if series is None or series.empty:
            return series
        s = series.copy()
        m = s.mean()
        sd = s.std(ddof=0)
        if sd is None or sd == 0 or np.isnan(sd):
            return pd.Series(0.0, index=s.index)
        return (s - m) / sd

    @classmethod
    def sector_zscore(cls, df: pd.DataFrame, col: str, sector_col: str = 'sector') -> pd.Series:
        if df is None or df.empty or col not in df.columns:
            return pd.Series(dtype=float)
        if sector_col not in df.columns:
            return cls.zscore_series(df[col])
        return df.groupby(sector_col)[col].transform(cls.zscore_series)

    # ------------------------- Composite & orthogonalization ------------------------- #
    @classmethod
    def compose_quality_exposure(
        cls,
        df: pd.DataFrame,
        sector_col: str = 'sector',
        winsor_limits: tuple[float, float] = (0.025, 0.025),
        output_col: str = 'quality_exposure_raw',
    ) -> pd.DataFrame:
        if df is None or df.empty:
            return df
        cols = ['roe','roic','gp_a','fcf_margin','accruals','de','nd_ebitda','int_cover','stab']
        for c in cols:
            if c not in df.columns:
                df[c] = np.nan
        lw, uw = winsor_limits
        for c in cols:
            df[f'{c}_w'] = cls.winsorize_series(df[c], lower=lw, upper=uw)
            df[f'{c}_z'] = cls.sector_zscore(df, f'{c}_w', sector_col=sector_col)
        df[output_col] = (
            0.40*(0.33*df['roe_z'] + 0.33*df['roic_z'] + 0.34*df['gp_a_z']) +
            0.25*(0.5*df['accruals_z'] + 0.5*df['fcf_margin_z']) +
            0.25*(0.4*df['de_z'] + 0.3*df['nd_ebitda_z'] + 0.3*df['int_cover_z']) +
            0.10*(df['stab_z'])
        )
        return df

    @classmethod
    def orthogonalize_quality(
        cls,
        df: pd.DataFrame,
        exposure_col: str = 'quality_exposure_raw',
        size_col: Optional[str] = None,
        value_col: Optional[str] = None,
        output_col: str = 'quality_exposure',
    ) -> pd.DataFrame:
        if df is None or df.empty or exposure_col not in df.columns:
            return df
        exp_z = cls.zscore_series(df[exposure_col].astype(float))
        if not size_col or not value_col or size_col not in df.columns or value_col not in df.columns:
            df[output_col] = exp_z
            return df
        X0 = pd.DataFrame({
            'const': 1.0,
            'size_z': cls.zscore_series(df[size_col].astype(float)),
            'value_z': cls.zscore_series(df[value_col].astype(float)),
        })
        m = pd.concat([exp_z.rename('y'), X0], axis=1).dropna()
        if m.empty:
            df[output_col] = exp_z
            return df
        Y = m['y'].values
        X = m[['const','size_z','value_z']].values
        try:
            beta, *_ = np.linalg.lstsq(X, Y, rcond=None)
            fitted = X @ beta
            resid = Y - fitted
            df[output_col] = np.nan
            df.loc[m.index, output_col] = resid
        except Exception:
            df[output_col] = exp_z
        return df
    
     # ------------------------- Helpers (in-file) ------------------------- #
    @staticmethod
    def _sort_rows_desc_by_date(rows: Optional[Iterable]) -> list:
        if not rows:
            return []
        try:
            return sorted(list(rows), key=lambda r: getattr(r, 'date', None) or date.min, reverse=True)
        except Exception:
            return list(rows)

    @staticmethod
    def ttm(series: List[Optional[float]], window: int = 4) -> float:
        if not series or len(series) < window:
            return np.nan
        try:
            values = [float(x) for x in series[:window] if x is not None]
            if len(values) < window:
                return np.nan
            return float(np.nansum(values))
        except Exception:
            return np.nan

    @staticmethod
    def avg(a: Optional[float], b: Optional[float]) -> float:
        try:
            if a is None or b is None:
                return np.nan
            return float((float(a) + float(b)) / 2.0)
        except Exception:
            return np.nan

    # ------------------------- Composite attributes ------------------------- #
    def compute_attributes(self) -> Dict[str, float]:
        """Compute robust TTM/averaged quality attributes with proper signs (decimals)."""
        ists = self._sort_rows_desc_by_date(self.fund.income_statements)
        bss = self._sort_rows_desc_by_date(self.fund.balance_sheets)
        cfs = self._sort_rows_desc_by_date(self.fund.cash_flow_statements)

        # TTM numerators (quarterly expected, most-recent-first)
        ni_ttm = self.ttm([getattr(q, 'netIncome', None) for q in ists])
        gp_ttm = self.ttm([getattr(q, 'grossProfit', None) for q in ists])
        sales_ttm = self.ttm([getattr(q, 'revenue', None) for q in ists])
        ebit_ttm = self.ttm([getattr(q, 'operatingIncome', None) for q in ists])
        ebitda_ttm = self.ttm([getattr(q, 'ebitda', None) for q in ists])
        cfo_ttm = self.ttm([getattr(c, 'netCashProvidedByOperatingActivities', None) for c in cfs])
        fcf_ttm = self.ttm([getattr(c, 'freeCashFlow', None) for c in cfs])
        # Averages: current vs 4Q ago
        assets0 = getattr(bss[0], 'totalAssets', None) if bss else None
        assets4 = getattr(bss[4], 'totalAssets', None) if len(bss) > 4 else None
        equity0 = getattr(bss[0], 'totalStockholdersEquity', None) if bss else None
        equity4 = getattr(bss[4], 'totalStockholdersEquity', None) if len(bss) > 4 else None
        debt0 = getattr(bss[0], 'totalDebt', None) if bss else None
        cash0 = getattr(bss[0], 'cashAndCashEquivalents', None) if bss else None
        avg_assets = self.avg(assets0, assets4)
        avg_equity = self.avg(equity0, equity4)
        invested_capital0 = (float(equity0 or 0) + float(debt0 or 0) - float(cash0 or 0)) if (equity0 is not None and debt0 is not None and cash0 is not None) else None
        invested_capital4 = (float(getattr(bss[4], 'totalStockholdersEquity', 0) or 0) + float(getattr(bss[4], 'totalDebt', 0) or 0) - float(getattr(bss[4], 'cashAndCashEquivalents', 0) or 0)) if len(bss) > 4 else None
        avg_invested_capital = self.avg(invested_capital0, invested_capital4)
        # NOPAT TTM (assume 21% tax on EBIT TTM)
        nopat_ttm = np.nan if np.isnan(ebit_ttm) else float(ebit_ttm) * (1.0 - 0.21)

        # Metrics (decimals); guard zeros and invalids
        def safe_div(n, d):
            try:
                if n is None or d is None:
                    return np.nan
                d = float(d)
                if d == 0 or np.isnan(d):
                    return np.nan
                return float(n) / d
            except Exception:
                return np.nan

        roe = safe_div(ni_ttm, avg_equity)
        roic = safe_div(nopat_ttm, avg_invested_capital)
        gp_a = safe_div(gp_ttm, avg_assets)
        fcf_margin = safe_div(fcf_ttm, sales_ttm)
        accruals = safe_div((ni_ttm - cfo_ttm) if (not np.isnan(ni_ttm) and not np.isnan(cfo_ttm)) else np.nan, avg_assets)
        cfo_assets = safe_div(cfo_ttm, avg_assets)
        cash_conv = safe_div(cfo_ttm, ni_ttm)
        # Leverage/safety
        de = safe_div(getattr(bss[0], 'totalDebt', None) if bss else None, getattr(bss[0], 'totalStockholdersEquity', None) if bss else None)
        nd_ebitda = safe_div((float(getattr(bss[0], 'totalDebt', 0) or 0) - float(getattr(bss[0], 'cashAndCashEquivalents', 0) or 0)) if bss else None, ebitda_ttm)
        int_cover = safe_div(ebit_ttm, self.ttm([getattr(q, 'interestExpense', None) for q in ists]))
        # Stability: negative stdev of EPS over 12 quarters if available, fallback to 8
        eps_series = [getattr(x, 'eps', None) for x in ists[:12]] if ists else []
        eps_vals = [float(x) for x in eps_series if x is not None]
        stab = np.nan
        if len(eps_vals) >= 4:
            sd = float(np.std(eps_vals, ddof=0))
            stab = -sd

        # Sign handling (higher = higher quality)
        # Bad metrics: accruals, de, nd_ebitda, instability (already negative)
        accruals = -accruals if not np.isnan(accruals) else accruals
        de = -de if not np.isnan(de) else de
        nd_ebitda = -nd_ebitda if not np.isnan(nd_ebitda) else nd_ebitda

        attrs: Dict[str, float] = {
            'roe': roe,
            'roic': roic,
            'gp_a': gp_a,
            'fcf_margin': fcf_margin,
            'accruals': accruals,
            'cfo_assets': cfo_assets,
            'cash_conv': cash_conv,
            'de': de,
            'nd_ebitda': nd_ebitda,
            'int_cover': int_cover,
            'stab': stab,
        }
        # Normalize invalids
        for k, v in list(attrs.items()):
            if v is None or (isinstance(v, float) and (np.isinf(v) or np.isnan(v))):
                attrs[k] = np.nan
        return attrs

if __name__ == '__main__':
    # Smoke test: compute attributes for a small ticker set and compose a simple quality score
    from backend.src.calculations_v2.core.data_service import DataService
    from datetime import datetime, timedelta, timezone
    print('[quality] smoke test starting...')
    try:
        tickers = ['AAPL', 'MSFT', 'AMZN', 'GOOGL', 'NVDA', 'LMT', 'XOM', 'TSLA', 'WMT', 'JPM', 'V']
        ds = DataService()
        # Bulk prefetch fundamentals to leverage thread pooling and cache
        fetched = ds.get_bulk_fundamentals(tickers, max_workers=8)

        rows = []
        for t in fetched.keys():
            # Uses cached fundamentals loaded by get_bulk_fundamentals
            q = QualityFactors(t, ds)
            attrs = q.compute_attributes()
            rows.append({'ticker': t, **attrs})
        df = pd.DataFrame(rows)
        # Winsorize and z-score per sector if available; here we use global z
        df = QualityFactors.compose_quality_exposure(df)
        df = QualityFactors.orthogonalize_quality(df)
        cols = ['ticker','quality_exposure_raw','quality_exposure','roe','roic','gp_a','fcf_margin','accruals','de','nd_ebitda','int_cover','stab']
        print(df[cols].to_string(index=False))
    except Exception as e:
        print(f'[quality] smoke test failed: {e}')
   


