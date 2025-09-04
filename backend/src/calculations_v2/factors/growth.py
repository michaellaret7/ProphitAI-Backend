from __future__ import annotations

from typing import Optional, Iterable, List, Dict
from datetime import date

from backend.src.calculations_v2.core.data_service import DataService
from backend.src.calculations_v2.core.models import FundamentalData
from backend.src.calculations_v2.core.helpers import (
    winsorize_series,
    zscore_series,
    sector_zscore,
    ttm,
    safe_divide,
    sort_rows_desc_by_date,
    pct_change,
    yoy_growth,
    residualize,
    compose_exposure,
)
import numpy as np
from scipy import stats
import pandas as pd
from backend.src.calculations_v2.core.config import DEFAULT_SECTOR_COL, DEFAULT_WINSOR_LIMITS


class GrowthFactors:
    """Growth factor calculations backed by DataService fundamentals.

    Computes: EPS growth rate, EPS CAGR, revenue growth, sales trend growth factor,
    FCF growth, PEG, ROE growth, ROIC growth, book value per share growth,
    operating cash flow growth.
    """

    def __init__(self, ticker: str, data_service: DataService | None = None, fundamental_data: FundamentalData | None = None):
        self.ticker = ticker.upper()
        self.ds = data_service or DataService()
        # Use provided fundamental data or fetch it
        if fundamental_data is not None:
            self.fund: FundamentalData = fundamental_data
        else:
            self.fund: FundamentalData = self.ds.get_fundamentals(self.ticker)

        # Defensive sort by date descending where possible
        ists = sort_rows_desc_by_date(self.fund.income_statements)
        bss = sort_rows_desc_by_date(self.fund.balance_sheets)
        cfs = sort_rows_desc_by_date(self.fund.cash_flow_statements)
        frs = sort_rows_desc_by_date(self.fund.financial_ratios)
        ests = sort_rows_desc_by_date(self.fund.analyst_estimates)

        # Detect statement frequency and compute span in years using actual dates when available
        income_dates = self._extract_dates(ists)
        self.frequency, self.periods_per_year = self._detect_frequency(income_dates)
        self.years = self._compute_years_span(income_dates)

        # Most recent and previous values (null-safe)
        self.curr_eps = ists[0].eps if ists else None
        self.prev_eps = ists[1].eps if len(ists) > 1 else None
        self.beg_eps = ists[-1].eps if ists else None

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
        if self.curr_eps is None or self.prev_eps is None:
            return np.nan
        # Return decimal (e.g., 0.12 for 12%)
        return float(pct_change(self.curr_eps, self.prev_eps, scale=1.0))

    def eps_cagr(self) -> float:
        if self.curr_eps is None or self.beg_eps is None:
            return np.nan
        # Only meaningful for positive per-share earnings across the span
        if self.beg_eps is None or self.curr_eps is None or self.beg_eps <= 0 or self.curr_eps <= 0:
            return np.nan
        years = self.years if self.years and self.years > 0 else self._fallback_years_count(self.fund.income_statements)
        if years <= 0:
            return np.nan
        try:
            return float((float(self.curr_eps) / float(self.beg_eps)) ** (1.0 / float(years)) - 1.0)
        except Exception:
            return np.nan

    def revenue_growth_rate(self) -> float:
        if self.curr_rev is None or self.prev_rev is None:
            return np.nan
        # Decimal unit
        return float(pct_change(self.curr_rev, self.prev_rev, scale=1.0))

    def sales_trend_growth_factor(self) -> float:
        # Prefer TTM Sales CAGR; if unavailable, use robust log1p slope on revenue series
        series = self.rev_series
        if len(series) < 5:
            return np.nan
        # TTM now and TTM 4 quarters earlier (requires at least 8 quarters to be strict; relax to 5+ for minimal signal)
        ttm_now = ttm(series, window=4)
        ttm_prev = ttm(series[4:], window=4) if len(series) >= 8 else np.nan
        if not np.isnan(ttm_now) and not np.isnan(ttm_prev):
            return float(self.cagr(ttm_now, ttm_prev, 1.0))
        # Fallback: log1p-linear slope normalized by periods to approximate growth
        try:
            y = np.log1p(np.array(series, dtype=float))
            x = np.arange(len(y), dtype=float)
            slope, *_ = stats.linregress(x, y)
            # Convert per-period slope to approx growth rate (exp(slope)-1)
            return float(np.expm1(slope))
        except Exception:
            return np.nan

    # ------------------------- YoY/TTM variants ------------------------- #
    def eps_yoy(self) -> float:
        # Requires quarterly series; use lag 4
        ists = sort_rows_desc_by_date(self.fund.income_statements)
        if len(ists) < 5:
            return np.nan
        curr = getattr(ists[0], 'eps', None)
        lag4 = getattr(ists[4], 'eps', None)
        return float(yoy_growth(curr, lag4))

    def sales_ttm_yoy(self) -> float:
        ists = sort_rows_desc_by_date(self.fund.income_statements)
        if len(ists) < 8:
            return np.nan
        # Prefer per-share if shares available
        shares_series = [getattr(x, 'weightedAverageShsOut', None) for x in ists]
        if all(s is not None and float(s) > 0 for s in shares_series[:8]):
            sales_series = [
                safe_divide(getattr(x, 'revenue', None), getattr(x, 'weightedAverageShsOut', None))
                for x in ists
            ]
        else:
            sales_series = [getattr(x, 'revenue', None) for x in ists]
        ttm_now = ttm(sales_series, window=4)
        ttm_prev = ttm(sales_series[4:], window=4)
        return float(yoy_growth(ttm_now, ttm_prev))

    def ocf_ttm_yoy(self) -> float:
        cfs = sort_rows_desc_by_date(self.fund.cash_flow_statements)
        if len(cfs) < 8:
            return np.nan
        # Prefer per-share using income statement shares where possible
        ists = sort_rows_desc_by_date(self.fund.income_statements)
        shares_series = [getattr(x, 'weightedAverageShsOut', None) for x in ists[:len(cfs)]] if ists else []
        if shares_series and all(s is not None and float(s) > 0 for s in shares_series[:8]):
            ocf_series = [
                safe_divide(getattr(c, 'netCashProvidedByOperatingActivities', None), getattr(i, 'weightedAverageShsOut', None))
                for c, i in zip(cfs, ists)
            ]
        else:
            ocf_series = [getattr(x, 'netCashProvidedByOperatingActivities', None) for x in cfs]
        ttm_now = ttm(ocf_series, window=4)
        ttm_prev = ttm(ocf_series[4:], window=4)
        return float(yoy_growth(ttm_now, ttm_prev))

    def fcf_ttm_yoy(self) -> float:
        cfs = sort_rows_desc_by_date(self.fund.cash_flow_statements)
        if len(cfs) < 8:
            return np.nan
        fcf_series = [getattr(x, 'freeCashFlow', None) for x in cfs]
        ttm_now = ttm(fcf_series, window=4)
        ttm_prev = ttm(fcf_series[4:], window=4)
        return float(yoy_growth(ttm_now, ttm_prev))

    # ------------------------- Forward estimates ------------------------- #
    def forward_eps_growth(self) -> float:
        """FY1 EPS growth: (FY1 - CY) / |CY| where CY is trailing actual TTM EPS.

        Uses analyst_estimates.epsAvg aggregated over next 4 quarters as FY1 proxy.
        """
        # CY: trailing TTM EPS from actuals
        ists = sort_rows_desc_by_date(self.fund.income_statements)
        if len(ists) < 4:
            return np.nan
        eps_series = [getattr(x, 'eps', None) for x in ists]
        cy_ttm = ttm(eps_series, window=4)
        if np.isnan(cy_ttm):
            return np.nan
        # FY1: next 4 quarters EPSAvg from estimates, most recent-first
        ests = sort_rows_desc_by_date(self.fund.analyst_estimates)
        if not ests or len(ests) < 1:
            return np.nan
        try:
            next4 = [getattr(e, 'epsAvg', None) for e in ests[:4]]
            if any(v is None for v in next4) or len(next4) < 4:
                return np.nan
            fy1 = float(np.nansum([float(v) for v in next4]))
        except Exception:
            return np.nan
        base = safe_divide(fy1 - float(cy_ttm), abs(float(cy_ttm)))
        return float(base) if not np.isnan(base) else np.nan

    def forward_eps_cagr_2y(self) -> float:
        """2-year forward EPS CAGR using estimates: CAGR(FY2, CY, 2)."""
        # CY: trailing TTM EPS from actuals
        ists = sort_rows_desc_by_date(self.fund.income_statements)
        if len(ists) < 4:
            return np.nan
        eps_series = [getattr(x, 'eps', None) for x in ists]
        cy_ttm = ttm(eps_series, window=4)
        if np.isnan(cy_ttm):
            return np.nan
        # FY2: next 8 quarters EPSAvg
        ests = sort_rows_desc_by_date(self.fund.analyst_estimates)
        if not ests or len(ests) < 8:
            return np.nan
        try:
            next8 = [getattr(e, 'epsAvg', None) for e in ests[:8]]
            if any(v is None for v in next8):
                return np.nan
            fy2 = float(np.nansum([float(v) for v in next8]))
        except Exception:
            return np.nan
        return float(self.cagr(fy2, float(cy_ttm), 2.0))

    def fcf_growth_rate(self) -> float:
        if self.curr_fcf is None or self.prev_fcf is None:
            return np.nan
        # Decimal unit
        return float(pct_change(self.curr_fcf, self.prev_fcf, scale=1.0))

    def peg_ratio(self) -> float:
        if self.pe_ratio is None:
            return np.nan
        eps_growth_dec = self.eps_growth_rate()
        if eps_growth_dec is None or np.isnan(eps_growth_dec):
            return np.nan
        # PEG convention divides by growth in percent
        eps_growth_pct = float(eps_growth_dec * 100.0)
        if eps_growth_pct <= 0.0:
            return np.nan
        return float(self.pe_ratio / eps_growth_pct)

    def roe_growth_rate(self) -> float:
        if self.curr_roe is None or self.prev_roe is None:
            return np.nan
        # Decimal unit
        return float(pct_change(self.curr_roe, self.prev_roe, scale=1.0))

    def roic_growth_rate(self) -> float:
        if self.curr_roic is None or self.prev_roic is None:
            return np.nan
        # Decimal unit
        return float(pct_change(self.curr_roic, self.prev_roic, scale=1.0))

    def book_value_growth_rate(self) -> float:
        if self.curr_bvps is None or self.prev_bvps is None:
            return np.nan
        # Decimal unit
        return float(pct_change(self.curr_bvps, self.prev_bvps, scale=1.0))

    def ocf_growth_rate(self) -> float:
        if self.curr_ocf is None or self.prev_ocf is None:
            return np.nan
        # Decimal unit
        return float(pct_change(self.curr_ocf, self.prev_ocf, scale=1.0))

    # ------------------------- Helpers (in-file) ------------------------- #
    @staticmethod
    def _extract_dates(rows: Optional[Iterable]) -> List[date]:
        if not rows:
            return []
        result: List[date] = []
        for r in rows:
            try:
                d = getattr(r, 'date', None)
                if d is not None:
                    result.append(d)
            except Exception:
                continue
        return result

    @staticmethod
    def _days_between(d1: Optional[date], d2: Optional[date]) -> Optional[int]:
        if d1 is None or d2 is None:
            return None
        try:
            return abs((d1 - d2).days)
        except Exception:
            return None

    def _detect_frequency(self, dates: List[date]) -> tuple[str, int]:
        """Detects statement frequency from date gaps.

        Returns (frequency_str, periods_per_year).
        """
        if len(dates) < 2:
            return ("unknown", 4)
        gaps: List[int] = []
        for i in range(len(dates) - 1):
            delta = self._days_between(dates[i], dates[i + 1])
            if delta is not None:
                gaps.append(delta)
        if not gaps:
            return ("unknown", 4)
        avg_gap = float(np.median(gaps))
        # Heuristics: quarterly ~ 90 days, annual ~ 365
        if 60.0 <= avg_gap <= 150.0:
            return ("quarterly", 4)
        if avg_gap >= 300.0:
            return ("annual", 1)
        # Default to quarterly if unclear
        return ("quarterly", 4)

    def _compute_years_span(self, dates: List[date]) -> float:
        if len(dates) < 2:
            return 0.0
        try:
            total_days = float(self._days_between(dates[0], dates[-1]) or 0)
            if total_days <= 0:
                # Fallback to period-count based
                return float(max(len(dates) - 1, 0)) / float(self.periods_per_year or 4)
            return total_days / 365.25
        except Exception:
            return float(max(len(dates) - 1, 0)) / float(self.periods_per_year or 4)

    def _fallback_years_count(self, rows: Optional[Iterable]) -> float:
        dates = self._extract_dates(rows)
        if len(dates) < 2:
            return 0.0
        return float(max(len(dates) - 1, 0)) / float(self.periods_per_year or 4)

    @staticmethod
    def cagr(v_end: Optional[float], v_start: Optional[float], years: Optional[float]) -> float:
        if v_end is None or v_start is None or years is None:
            return np.nan
        try:
            if float(v_start) <= 0.0 or float(v_end) <= 0.0 or float(years) <= 0.0:
                return np.nan
            return float((float(v_end) / float(v_start)) ** (1.0 / float(years)) - 1.0)
        except Exception:
            return np.nan

    # ------------------------- Attributes & composite ------------------------- #
    def compute_attributes(self) -> Dict[str, float]:
        """Compute raw growth attributes (decimals) for this ticker."""
        attrs: Dict[str, float] = {
            "fwd_eps_g": self.forward_eps_growth(),
            "fwd_2y_cagr": self.forward_eps_cagr_2y(),
            "sales_yoy": self.sales_ttm_yoy(),
            "ocf_yoy": self.ocf_ttm_yoy(),
        }
        # Normalize invalids
        for k, v in list(attrs.items()):
            if v is None or np.isinf(v) or (isinstance(v, float) and np.isnan(v)):
                attrs[k] = np.nan
        return attrs

    @classmethod
    def compose_growth_exposure(
        cls,
        df: pd.DataFrame,
        sector_col: str = DEFAULT_SECTOR_COL,
        winsor_limits: tuple[float, float] = DEFAULT_WINSOR_LIMITS,
        weights: Optional[Dict[str, float]] = None,
        output_col: str = "growth_exposure_raw",
    ) -> pd.DataFrame:
        """Compose growth exposure from attributes in df.

        Expected columns: fwd_eps_g, fwd_2y_cagr, sales_yoy, ocf_yoy, sector.
        Returns df with winsorized, z-scored columns and a weighted exposure column.
        """
        if df is None or df.empty:
            return df
        cols = ["fwd_eps_g", "fwd_2y_cagr", "sales_yoy", "ocf_yoy"]
        if not weights:
            weights = {"fwd_eps_g": 0.35, "fwd_2y_cagr": 0.25, "sales_yoy": 0.20, "ocf_yoy": 0.20}
        return compose_exposure(
            df,
            cols=cols,
            weights=weights,
            sector_col=sector_col,
            winsor_limits=winsor_limits,
            output_col=output_col,
        )

    @classmethod
    def orthogonalize_growth(
        cls,
        df: pd.DataFrame,
        exposure_col: str = "growth_exposure_raw",
        size_col: Optional[str] = None,
        value_col: Optional[str] = None,
        output_col: str = "growth_exposure",
    ) -> pd.DataFrame:
        """Orthogonalize growth exposure against Size/Value using shared residualizer.

        If required regressors are missing, falls back to global z-score of exposure.
        """
        if df is None or df.empty or exposure_col not in df.columns:
            return df
        # Fallback if regressors missing
        if not size_col or not value_col or size_col not in df.columns or value_col not in df.columns:
            df[output_col] = zscore_series(df[exposure_col].astype(float))
            return df
        # Residualize y ~ [size_col, value_col]
        return residualize(df, y_col=exposure_col, x_cols=[size_col, value_col], out_col=output_col)

    def calc_all(self) -> Dict[str, float]:
        """Calculate all growth factors for the ticker.
        
        Returns:
            Dictionary containing all growth factor metrics (as decimals).
        """
        round_factor = 4
        results = {
            # Basic growth rates
            "eps_growth_rate": round(self.eps_growth_rate(), round_factor),
            "eps_cagr": round(self.eps_cagr(), round_factor),
            "revenue_growth_rate": round(self.revenue_growth_rate(), round_factor),
            "sales_trend_growth_factor": round(self.sales_trend_growth_factor(), round_factor),
            
            # YoY metrics
            "eps_yoy": round(self.eps_yoy(), round_factor),
            "sales_ttm_yoy": round(self.sales_ttm_yoy(), round_factor),
            "ocf_ttm_yoy": round(self.ocf_ttm_yoy(), round_factor),
            "fcf_ttm_yoy": round(self.fcf_ttm_yoy(), round_factor),
            
            # Forward estimates
            "forward_eps_growth": round(self.forward_eps_growth(), round_factor),
            "forward_eps_cagr_2y": round(self.forward_eps_cagr_2y(), round_factor),
            
            # Other growth metrics
            "fcf_growth_rate": round(self.fcf_growth_rate(), round_factor),
            "peg_ratio": round(self.peg_ratio(), round_factor),    
            "roe_growth_rate": round(self.roe_growth_rate(), round_factor),
            "roic_growth_rate": round(self.roic_growth_rate(), round_factor),
            "book_value_growth_rate": round(self.book_value_growth_rate(), round_factor),
            "ocf_growth_rate": round(self.ocf_growth_rate(), round_factor),
        }
        
        # Clean up NaN/Inf values
        for key, value in results.items():
            if value is None or np.isinf(value) or (isinstance(value, float) and np.isnan(value)):
                results[key] = np.nan
                
        return results
    
    @classmethod
    def calc_all_bulk(cls, tickers: List[str], data_service: DataService | None = None) -> pd.DataFrame:
        """Calculate all growth factors for multiple tickers using bulk data fetching.
        
        Args:
            tickers: List of ticker symbols
            data_service: Optional DataService instance (created if not provided)
        
        Returns:
            DataFrame with tickers as rows and growth metrics as columns
        """
        ds = data_service or DataService()
        
        # Bulk fetch fundamental data for all tickers
        fundamentals = ds.get_bulk_fundamentals(tickers)
        
        # Calculate growth factors for each ticker
        all_results = {}
        for ticker in tickers:
            ticker = ticker.upper()
            if ticker in fundamentals:
                try:
                    # Create GrowthFactors with pre-fetched data
                    gf = cls(ticker, data_service=ds, fundamental_data=fundamentals[ticker])
                    all_results[ticker] = gf.calc_all()
                except Exception as e:
                    print(f"Error calculating growth factors for {ticker}: {e}")
                    # Add NaN row for failed tickers
                    all_results[ticker] = {}
        
        # Convert to DataFrame
        df = pd.DataFrame(all_results).T
        return df
