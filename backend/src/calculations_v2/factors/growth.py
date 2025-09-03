from __future__ import annotations

from typing import Optional, Iterable, List, Dict
from datetime import date

from backend.src.calculations_v2.core.data_service import DataService
from backend.src.calculations_v2.core.models import FundamentalData
import numpy as np
from scipy import stats
import pandas as pd


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

        # Defensive sort by date descending where possible
        ists = self._sort_rows_desc_by_date(self.fund.income_statements)
        bss = self._sort_rows_desc_by_date(self.fund.balance_sheets)
        cfs = self._sort_rows_desc_by_date(self.fund.cash_flow_statements)
        frs = self._sort_rows_desc_by_date(self.fund.financial_ratios)
        ests = self._sort_rows_desc_by_date(self.fund.analyst_estimates)

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
        return float(self._pct_change(self.curr_eps, self.prev_eps, scale=1.0))

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
        return float(self._pct_change(self.curr_rev, self.prev_rev, scale=1.0))

    def sales_trend_growth_factor(self) -> float:
        # Prefer TTM Sales CAGR; if unavailable, use robust log1p slope on revenue series
        series = self.rev_series
        if len(series) < 5:
            return np.nan
        # TTM now and TTM 4 quarters earlier (requires at least 8 quarters to be strict; relax to 5+ for minimal signal)
        ttm_now = self.ttm(series, window=4)
        ttm_prev = self.ttm(series[4:], window=4) if len(series) >= 8 else np.nan
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
        ists = self._sort_rows_desc_by_date(self.fund.income_statements)
        if len(ists) < 5:
            return np.nan
        curr = getattr(ists[0], 'eps', None)
        lag4 = getattr(ists[4], 'eps', None)
        return float(self.yoy_growth(curr, lag4))

    def sales_ttm_yoy(self) -> float:
        ists = self._sort_rows_desc_by_date(self.fund.income_statements)
        if len(ists) < 8:
            return np.nan
        # Prefer per-share if shares available
        shares_series = [getattr(x, 'weightedAverageShsOut', None) for x in ists]
        if all(s is not None and float(s) > 0 for s in shares_series[:8]):
            sales_series = [
                self._safe_divide(getattr(x, 'revenue', None), getattr(x, 'weightedAverageShsOut', None))
                for x in ists
            ]
        else:
            sales_series = [getattr(x, 'revenue', None) for x in ists]
        ttm_now = self.ttm(sales_series, window=4)
        ttm_prev = self.ttm(sales_series[4:], window=4)
        return float(self.yoy_growth(ttm_now, ttm_prev))

    def ocf_ttm_yoy(self) -> float:
        cfs = self._sort_rows_desc_by_date(self.fund.cash_flow_statements)
        if len(cfs) < 8:
            return np.nan
        # Prefer per-share using income statement shares where possible
        ists = self._sort_rows_desc_by_date(self.fund.income_statements)
        shares_series = [getattr(x, 'weightedAverageShsOut', None) for x in ists[:len(cfs)]] if ists else []
        if shares_series and all(s is not None and float(s) > 0 for s in shares_series[:8]):
            ocf_series = [
                self._safe_divide(getattr(c, 'netCashProvidedByOperatingActivities', None), getattr(i, 'weightedAverageShsOut', None))
                for c, i in zip(cfs, ists)
            ]
        else:
            ocf_series = [getattr(x, 'netCashProvidedByOperatingActivities', None) for x in cfs]
        ttm_now = self.ttm(ocf_series, window=4)
        ttm_prev = self.ttm(ocf_series[4:], window=4)
        return float(self.yoy_growth(ttm_now, ttm_prev))

    def fcf_ttm_yoy(self) -> float:
        cfs = self._sort_rows_desc_by_date(self.fund.cash_flow_statements)
        if len(cfs) < 8:
            return np.nan
        fcf_series = [getattr(x, 'freeCashFlow', None) for x in cfs]
        ttm_now = self.ttm(fcf_series, window=4)
        ttm_prev = self.ttm(fcf_series[4:], window=4)
        return float(self.yoy_growth(ttm_now, ttm_prev))

    # ------------------------- Forward estimates ------------------------- #
    def forward_eps_growth(self) -> float:
        """FY1 EPS growth: (FY1 - CY) / |CY| where CY is trailing actual TTM EPS.

        Uses analyst_estimates.epsAvg aggregated over next 4 quarters as FY1 proxy.
        """
        # CY: trailing TTM EPS from actuals
        ists = self._sort_rows_desc_by_date(self.fund.income_statements)
        if len(ists) < 4:
            return np.nan
        eps_series = [getattr(x, 'eps', None) for x in ists]
        cy_ttm = self.ttm(eps_series, window=4)
        if np.isnan(cy_ttm):
            return np.nan
        # FY1: next 4 quarters EPSAvg from estimates, most recent-first
        ests = self._sort_rows_desc_by_date(self.fund.analyst_estimates)
        if not ests or len(ests) < 1:
            return np.nan
        try:
            next4 = [getattr(e, 'epsAvg', None) for e in ests[:4]]
            if any(v is None for v in next4) or len(next4) < 4:
                return np.nan
            fy1 = float(np.nansum([float(v) for v in next4]))
        except Exception:
            return np.nan
        base = self._safe_divide(fy1 - float(cy_ttm), abs(float(cy_ttm)))
        return float(base) if not np.isnan(base) else np.nan

    def forward_eps_cagr_2y(self) -> float:
        """2-year forward EPS CAGR using estimates: CAGR(FY2, CY, 2)."""
        # CY: trailing TTM EPS from actuals
        ists = self._sort_rows_desc_by_date(self.fund.income_statements)
        if len(ists) < 4:
            return np.nan
        eps_series = [getattr(x, 'eps', None) for x in ists]
        cy_ttm = self.ttm(eps_series, window=4)
        if np.isnan(cy_ttm):
            return np.nan
        # FY2: next 8 quarters EPSAvg
        ests = self._sort_rows_desc_by_date(self.fund.analyst_estimates)
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
        return float(self._pct_change(self.curr_fcf, self.prev_fcf, scale=1.0))

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
        return float(self._pct_change(self.curr_roe, self.prev_roe, scale=1.0))

    def roic_growth_rate(self) -> float:
        if self.curr_roic is None or self.prev_roic is None:
            return np.nan
        # Decimal unit
        return float(self._pct_change(self.curr_roic, self.prev_roic, scale=1.0))

    def book_value_growth_rate(self) -> float:
        if self.curr_bvps is None or self.prev_bvps is None:
            return np.nan
        # Decimal unit
        return float(self._pct_change(self.curr_bvps, self.prev_bvps, scale=1.0))

    def ocf_growth_rate(self) -> float:
        if self.curr_ocf is None or self.prev_ocf is None:
            return np.nan
        # Decimal unit
        return float(self._pct_change(self.curr_ocf, self.prev_ocf, scale=1.0))

    # ------------------------- Helpers (in-file) ------------------------- #
    @staticmethod
    def _sort_rows_desc_by_date(rows: Optional[Iterable]) -> list:
        if not rows:
            return []
        try:
            return sorted(list(rows), key=lambda r: getattr(r, 'date', None) or date.min, reverse=True)
        except Exception:
            # Fallback: return as list without sorting
            return list(rows)

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
    def _safe_divide(numerator: Optional[float], denominator: Optional[float], default: float = np.nan) -> float:
        try:
            if numerator is None or denominator is None:
                return default
            if float(denominator) == 0.0:
                return default
            return float(numerator) / float(denominator)
        except Exception:
            return default

    @classmethod
    def _pct_change(cls, current: Optional[float], previous: Optional[float], scale: float = 1.0) -> float:
        if current is None or previous is None:
            return np.nan
        try:
            base = cls._safe_divide(float(current) - float(previous), abs(float(previous)))
            if np.isnan(base):
                return np.nan
            return float(base * scale)
        except Exception:
            return np.nan

    @staticmethod
    def yoy_growth(current: Optional[float], lagged: Optional[float]) -> float:
        """Year-over-year growth (decimal)."""
        if current is None or lagged is None:
            return np.nan
        try:
            base = GrowthFactors._safe_divide(float(current), float(lagged))
            if np.isnan(base):
                return np.nan
            return float(base - 1.0)
        except Exception:
            return np.nan

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
    def cagr(v_end: Optional[float], v_start: Optional[float], years: Optional[float]) -> float:
        if v_end is None or v_start is None or years is None:
            return np.nan
        try:
            if float(v_start) <= 0.0 or float(v_end) <= 0.0 or float(years) <= 0.0:
                return np.nan
            return float((float(v_end) / float(v_start)) ** (1.0 / float(years)) - 1.0)
        except Exception:
            return np.nan

    # ------------------------- Cross-section helpers ------------------------- #
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
    def sector_zscore(cls, df: pd.DataFrame, col: str, sector_col: str = "sector") -> pd.Series:
        if df is None or df.empty or col not in df.columns:
            return pd.Series(dtype=float)
        if sector_col not in df.columns:
            # Global z-score if no sector
            return cls.zscore_series(df[col])
        return df.groupby(sector_col)[col].transform(cls.zscore_series)

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
        sector_col: str = "sector",
        winsor_limits: tuple[float, float] = (0.025, 0.025),
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
        for c in cols:
            if c not in df.columns:
                df[c] = np.nan
        lw, uw = winsor_limits
        # Winsorize then sector z-score
        for c in cols:
            df[f"{c}_w"] = cls.winsorize_series(df[c], lower=lw, upper=uw)
            df[f"{c}_z"] = cls.sector_zscore(df, f"{c}_w", sector_col=sector_col)
        # Default weights
        if not weights:
            weights = {"fwd_eps_g_z": 0.35, "fwd_2y_cagr_z": 0.25, "sales_yoy_z": 0.20, "ocf_yoy_z": 0.20}
        # Compute weighted sum
        df[output_col] = 0.0
        for key, w in weights.items():
            if key not in df.columns:
                # Map base name to z variant if needed
                base = key.replace("_z", "")
                key = f"{base}_z"
            if key in df.columns:
                df[output_col] = df[output_col].fillna(0.0) + w * df[key].fillna(0.0)
        return df

    @classmethod
    def orthogonalize_growth(
        cls,
        df: pd.DataFrame,
        exposure_col: str = "growth_exposure_raw",
        size_col: Optional[str] = None,
        value_col: Optional[str] = None,
        output_col: str = "growth_exposure",
    ) -> pd.DataFrame:
        """Orthogonalize growth exposure against Size/Value via OLS residuals.

        If size_col/value_col are None or missing, returns z-scored exposure.
        """
        if df is None or df.empty or exposure_col not in df.columns:
            return df
        # Z-score exposure globally first
        exp_z = cls.zscore_series(df[exposure_col].astype(float))
        if not size_col or not value_col or size_col not in df.columns or value_col not in df.columns:
            df[output_col] = exp_z
            return df
        # Prepare design matrix with intercept
        X0 = pd.DataFrame({
            "const": 1.0,
            "size_z": cls.zscore_series(df[size_col].astype(float)),
            "value_z": cls.zscore_series(df[value_col].astype(float)),
        })
        # Align and drop NaNs
        m = pd.concat([exp_z.rename("y"), X0], axis=1).dropna()
        if m.empty:
            df[output_col] = exp_z
            return df
        Y = m["y"].values
        X = m[["const", "size_z", "value_z"]].values
        try:
            beta, *_ = np.linalg.lstsq(X, Y, rcond=None)
            fitted = X @ beta
            resid = Y - fitted
            # Place residuals back aligned to df index
            df[output_col] = np.nan
            df.loc[m.index, output_col] = resid
        except Exception:
            df[output_col] = exp_z
        return df


if __name__ == "__main__":
    # Lightweight smoke test for attributes and composite
    import sys
    try:
        test_tickers = ["AAPL", "MSFT", "AMZN", "GOOGL", "NVDA"]
        ds = DataService()
        rows: List[Dict[str, float]] = []
        for t in test_tickers:
            try:
                gf = GrowthFactors(t, ds)
                attrs = gf.compute_attributes()
                extra = {
                    "eps_gr": gf.eps_growth_rate(),
                    "eps_cagr": gf.eps_cagr(),
                    "eps_yoy": gf.eps_yoy(),
                    "rev_gr": gf.revenue_growth_rate(),
                    "sales_ttm_yoy": gf.sales_ttm_yoy(),
                    "sales_trend": gf.sales_trend_growth_factor(),
                    "ocf_gr": gf.ocf_growth_rate(),
                    "ocf_ttm_yoy": gf.ocf_ttm_yoy(),
                    "fcf_gr": gf.fcf_growth_rate(),
                    "fcf_ttm_yoy": gf.fcf_ttm_yoy(),
                    "peg": gf.peg_ratio(),
                    "roe_gr": gf.roe_growth_rate(),
                    "roic_gr": gf.roic_growth_rate(),
                    "bvps_gr": gf.book_value_growth_rate(),
                    "freq": gf.frequency,
                    "ppy": gf.periods_per_year,
                    "years_span": gf.years,
                }
                rows.append({"ticker": t, **attrs, **extra})
            except Exception as e:
                print(f"[warn] Failed computing attributes for {t}: {e}")
        frame = pd.DataFrame(rows)
        # Compose exposure (global z-score if sector not provided)
        frame = GrowthFactors.compose_growth_exposure(frame)
        frame = GrowthFactors.orthogonalize_growth(frame, exposure_col="growth_exposure_raw")
        cols = [
            "ticker",
            "fwd_eps_g",
            "fwd_2y_cagr",
            "eps_gr",
            "eps_cagr",
            "eps_yoy",
            "rev_gr",
            "sales_yoy",
            "sales_ttm_yoy",
            "sales_trend",
            "ocf_yoy",
            "ocf_ttm_yoy",
            "ocf_gr",
            "fcf_ttm_yoy",
            "fcf_gr",
            "peg",
            "roe_gr",
            "roic_gr",
            "bvps_gr",
            "growth_exposure_raw",
            "growth_exposure",
            "freq",
            "ppy",
            "years_span",
        ]
        print(frame[cols].to_string(index=False))
    except Exception as e:
        print(f"[error] Smoke test failed: {e}")
        sys.exit(1)


