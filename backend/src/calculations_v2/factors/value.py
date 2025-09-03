from __future__ import annotations

from typing import Optional, Dict
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from backend.src.calculations_v2.core.data_service import DataService
from backend.src.calculations_v2.core.models import FundamentalData
from backend.src.utils.ticker_utils import get_most_recent_price
from backend.src.calculations_v2.factors.growth import GrowthFactors


class ValueFactors:
    """Value factor calculations using the unified DataService fundamentals.

    Mirrors legacy value factors: P/B, B/M, trailing/forward P/E, earnings yield,
    P/S, P/CF, FCF yield, EV/EBITDA, EV/EBIT, dividend yield, PEG.
    """

    def __init__(
        self,
        ticker: str,
        data_service: DataService | None = None,
        as_of_date: Optional[datetime] = None,
        filing_lag_days: int = 0,
    ):
        self.ticker = ticker.upper()
        self.ds = data_service or DataService()
        self.fund: FundamentalData = self.ds.get_fundamentals(self.ticker)

        # As-of alignment controls
        self.as_of_date: Optional[datetime] = as_of_date
        self.filing_lag_days: int = int(filing_lag_days) if filing_lag_days and filing_lag_days > 0 else 0
        self._effective_end_dt: datetime = as_of_date if as_of_date is not None else datetime.now(timezone.utc)
        self._cutoff_date = (self._effective_end_dt - timedelta(days=self.filing_lag_days)).date()

        # Price aligned to as_of_date if provided, else most recent
        try:
            if self.as_of_date is not None:
                start_dt = self._effective_end_dt - timedelta(days=30)
                price_data = self.ds.get_price_data(self.ticker, start_dt, self._effective_end_dt)
                if price_data and price_data.frame is not None and not price_data.frame.empty:
                    last_close = price_data.frame["close"].iloc[-1]
                    self.price = float(last_close) if last_close is not None else None
                else:
                    self.price = get_most_recent_price(self.ticker)
            else:
                self.price = get_most_recent_price(self.ticker)
        except Exception:
            self.price = get_most_recent_price(self.ticker)

        # Defensive sort by date desc using Growth helpers (DRY)
        ists = GrowthFactors._sort_rows_desc_by_date(self.fund.income_statements)
        bss = GrowthFactors._sort_rows_desc_by_date(self.fund.balance_sheets)
        cfs = GrowthFactors._sort_rows_desc_by_date(self.fund.cash_flow_statements)
        frs = GrowthFactors._sort_rows_desc_by_date(self.fund.financial_ratios)
        ests = GrowthFactors._sort_rows_desc_by_date(self.fund.analyst_estimates)

        # As-of cutoff filter to avoid look-ahead
        def _filter_rows_by_cutoff(rows):
            if not rows:
                return []
            out = []
            for r in rows:
                try:
                    d = getattr(r, 'date', None)
                    if d is None:
                        continue
                    dd = d.date() if hasattr(d, 'date') else d
                    if dd is not None and dd <= self._cutoff_date:
                        out.append(r)
                except Exception:
                    continue
            return out

        ists = _filter_rows_by_cutoff(ists)
        bss = _filter_rows_by_cutoff(bss)
        cfs = _filter_rows_by_cutoff(cfs)
        frs = _filter_rows_by_cutoff(frs)
        ests = _filter_rows_by_cutoff(ests)

        # Prefer diluted shares; fallback to basic
        self.shares_outstanding = None
        try:
            shs_dil = getattr(ists[0], 'weightedAverageShsOutDil', None) if ists else None
            shs_basic = getattr(ists[0], 'weightedAverageShsOut', None) if ists else None
            if shs_dil is not None and float(shs_dil) > 0:
                self.shares_outstanding = float(shs_dil)
            elif shs_basic is not None and float(shs_basic) > 0:
                self.shares_outstanding = float(shs_basic)
        except Exception:
            self.shares_outstanding = None

        # TTM aggregations from quarterly series
        def _ttm_from(rows, attr: str) -> Optional[float]:
            series = [getattr(x, attr, None) for x in rows] if rows else []
            val = GrowthFactors.ttm(series, window=4)
            return float(val) if val is not None and not np.isnan(val) else None

        self.eps_ttm = _ttm_from(ists, 'eps')
        # Forward EPS: sum next 4 quarters epsAvg from analyst estimates
        try:
            if ests and len(ests) >= 4:
                next4 = [getattr(e, 'epsAvg', None) for e in ests[:4]]
                if all(v is not None for v in next4):
                    self.eps_forward_next_fy = float(np.nansum([float(v) for v in next4]))
                else:
                    self.eps_forward_next_fy = None
            else:
                self.eps_forward_next_fy = None
        except Exception:
            self.eps_forward_next_fy = None

        self.revenue_ttm = _ttm_from(ists, 'revenue')
        self.operating_cash_flow_ttm = _ttm_from(cfs, 'netCashProvidedByOperatingActivities')
        self.free_cash_flow_ttm = _ttm_from(cfs, 'freeCashFlow')
        self.ebitda_ttm = _ttm_from(ists, 'ebitda')
        # EBIT proxy: operatingIncome TTM
        self.ebit_ttm = _ttm_from(ists, 'operatingIncome')

        # Balance sheet components for EV
        self.total_debt = float(getattr(bss[0], 'totalDebt', None)) if bss and getattr(bss[0], 'totalDebt', None) is not None else None
        self.cash_and_equivalents = float(getattr(bss[0], 'cashAndCashEquivalents', None)) if bss and getattr(bss[0], 'cashAndCashEquivalents', None) is not None else None
        self.preferred_equity = float(getattr(bss[0], 'preferredStock', None)) if bss and getattr(bss[0], 'preferredStock', None) is not None else 0.0
        self.minority_interest = float(getattr(bss[0], 'minorityInterest', None)) if bss and getattr(bss[0], 'minorityInterest', None) is not None else 0.0

        # Book value per share from equity / diluted shares
        try:
            equity = float(getattr(bss[0], 'totalStockholdersEquity', None)) if bss and getattr(bss[0], 'totalStockholdersEquity', None) is not None else None
            if equity is not None and self.shares_outstanding is not None and self.shares_outstanding > 0:
                self.book_value_per_share = equity / self.shares_outstanding
            else:
                self.book_value_per_share = None
        except Exception:
            self.book_value_per_share = None

        # Cache of last-12-month dividends per share (computed on demand)
        self._dps_ttm: Optional[float] = None

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
        # Backward-compat: approximate using DPS TTM when available
        dps = self._get_dps_ttm()
        if dps is None or self.price is None or self.price <= 0:
            return None
        dy = dps / self.price
        # Clip extreme specials
        if dy > 0.2:
            dy = 0.2
        return float(dy)

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

    # ------------------------- New: Attributes & Composition ------------------------- #
    def _get_market_cap(self) -> Optional[float]:
        if self.shares_outstanding is None or self.price is None:
            return None
        try:
            mc = float(self.shares_outstanding) * float(self.price)
            return mc if mc > 0 else None
        except Exception:
            return None

    def _get_ev(self) -> Optional[float]:
        mcap = self._get_market_cap()
        if mcap is None:
            return None
        try:
            td = self.total_debt if self.total_debt is not None else 0.0
            cash = self.cash_and_equivalents if self.cash_and_equivalents is not None else 0.0
            pref = self.preferred_equity if self.preferred_equity is not None else 0.0
            mi = self.minority_interest if self.minority_interest is not None else 0.0
            ev = float(mcap) + float(td) + float(pref) + float(mi) - float(cash)
            if ev is None or ev <= 0:
                return None
            return ev
        except Exception:
            return None

    def _get_dps_ttm(self) -> Optional[float]:
        if self._dps_ttm is not None:
            return self._dps_ttm
        try:
            end = self._effective_end_dt
            start = end - timedelta(days=365)
            divs = self.ds.get_dividends(self.ticker, start, end)
            if divs is None or divs.series is None or divs.series.empty:
                self._dps_ttm = None
            else:
                dps = float(np.nansum(divs.series.values.astype(float)))
                self._dps_ttm = dps if dps >= 0 else None
            return self._dps_ttm
        except Exception:
            self._dps_ttm = None
            return None

    def compute_attributes(self) -> Dict[str, float]:
        """Compute Value cheapness yields (higher = cheaper).

        Returns bp, ep, cfp, fcf_yield, sales_ev, ebitda_ev, ebit_ev, div_yld.
        """
        attrs: Dict[str, float] = {
            "bp": np.nan,
            "ep": np.nan,
            "cfp": np.nan,
            "fcf_yield": np.nan,
            "sales_ev": np.nan,
            "ebitda_ev": np.nan,
            "ebit_ev": np.nan,
            "div_yld": np.nan,
        }
        price = self.price if self.price is not None and self.price > 0 else None
        shares = self.shares_outstanding if self.shares_outstanding is not None and self.shares_outstanding > 0 else None
        mcap = self._get_market_cap()
        ev = self._get_ev()

        # bp: (Equity / Shares) / Price
        try:
            if price is not None and shares is not None:
                equity = getattr(GrowthFactors._sort_rows_desc_by_date(self.fund.balance_sheets)[0], 'totalStockholdersEquity', None)
                if equity is not None and float(equity) > 0:
                    bvps = float(equity) / float(shares)
                    if bvps > 0:
                        attrs["bp"] = float(bvps / float(price))
        except Exception:
            pass

        # ep: prefer forward (FY1) if positive, else TTM if positive
        try:
            if price is not None:
                if self.eps_forward_next_fy is not None and float(self.eps_forward_next_fy) > 0:
                    attrs["ep"] = float(self.eps_forward_next_fy) / float(price)
                elif self.eps_ttm is not None and float(self.eps_ttm) > 0:
                    attrs["ep"] = float(self.eps_ttm) / float(price)
        except Exception:
            pass

        # cfp and fcf_yield: totals over market cap
        try:
            if mcap is not None and float(mcap) > 0:
                if self.operating_cash_flow_ttm is not None:
                    attrs["cfp"] = float(self.operating_cash_flow_ttm) / float(mcap)
                if self.free_cash_flow_ttm is not None:
                    attrs["fcf_yield"] = float(self.free_cash_flow_ttm) / float(mcap)
        except Exception:
            pass

        # EV-based yields
        try:
            if ev is not None and float(ev) > 0:
                if self.ebitda_ttm is not None and float(self.ebitda_ttm) > 0:
                    attrs["ebitda_ev"] = float(self.ebitda_ttm) / float(ev)
                if self.ebit_ttm is not None and float(self.ebit_ttm) > 0:
                    attrs["ebit_ev"] = float(self.ebit_ttm) / float(ev)
                if self.revenue_ttm is not None and float(self.revenue_ttm) > 0:
                    attrs["sales_ev"] = float(self.revenue_ttm) / float(ev)
        except Exception:
            pass

        # Dividend yield from DPS TTM
        try:
            dps = self._get_dps_ttm()
            if dps is not None and price is not None:
                dy = float(dps) / float(price)
                attrs["div_yld"] = float(min(max(dy, 0.0), 0.2))
        except Exception:
            pass

        # Normalize None/inf to NaN
        for k, v in list(attrs.items()):
            if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
                attrs[k] = np.nan
        return attrs

    @classmethod
    def compose_value_exposure(
        cls,
        df: pd.DataFrame,
        sector_col: str = "sector",
        winsor_limits: tuple[float, float] = (0.025, 0.025),
        weights: Optional[Dict[str, float]] = None,
        output_col: str = "value_exposure_raw",
    ) -> pd.DataFrame:
        """Compose Value exposure with winsorization, sector z-score, and sector-aware weights.

        Expected columns: bp, ep, cfp, fcf_yield, sales_ev, ebitda_ev, ebit_ev, div_yld, sector.
        """
        if df is None or df.empty:
            return df
        base_cols = ["bp", "ep", "cfp", "fcf_yield", "sales_ev", "ebitda_ev", "ebit_ev", "div_yld"]
        for c in base_cols:
            if c not in df.columns:
                df[c] = np.nan
        lw, uw = winsor_limits
        # Winsorize then sector z-score (reuse Growth helpers)
        for c in base_cols:
            df[f"{c}_w"] = GrowthFactors.winsorize_series(df[c].astype(float), lower=lw, upper=uw)
            df[f"{c}_z"] = GrowthFactors.sector_zscore(df, f"{c}_w", sector_col=sector_col)

        # Default weights
        if not weights:
            weights = {
                "bp": 0.20,
                "ep": 0.20,
                "cfp": 0.15,
                "fcf_yield": 0.15,
                "sales_ev": 0.10,
                "ebitda_ev": 0.10,
                "ebit_ev": 0.05,
                "div_yld": 0.05,
            }

        ev_cols = {"sales_ev", "ebitda_ev", "ebit_ev"}

        def row_weighted_sum(row: pd.Series) -> float:
            # Drop EV-based attributes for Financials/Utilities and renormalize
            sector = str(row.get(sector_col, "")) if sector_col in row else ""
            drop_ev = sector.lower().startswith("financial") or sector.lower().startswith("utilit")
            num = 0.0
            denom = 0.0
            for key, w in weights.items():
                if drop_ev and key in ev_cols:
                    continue
                zcol = f"{key}_z"
                val = row.get(zcol, np.nan)
                if val is not None and not np.isnan(val):
                    num += float(w) * float(val)
                    denom += float(w)
            if denom == 0.0:
                return 0.0
            return float(num / denom)

        df[output_col] = df.apply(row_weighted_sum, axis=1)
        return df

    @classmethod
    def orthogonalize_value(
        cls,
        df: pd.DataFrame,
        exposure_col: str = "value_exposure_raw",
        size_col: Optional[str] = None,
        momentum_col: Optional[str] = None,
        output_col: str = "value_exposure",
    ) -> pd.DataFrame:
        """Orthogonalize Value exposure against Size/Momentum via OLS residuals.

        If required regressors are missing, returns z-scored exposure.
        """
        if df is None or df.empty or exposure_col not in df.columns:
            return df
        exp_z = GrowthFactors.zscore_series(df[exposure_col].astype(float))
        # Require both regressors for orthogonalization; otherwise fallback
        if not size_col or not momentum_col or size_col not in df.columns or momentum_col not in df.columns:
            df[output_col] = exp_z
            return df
        X0 = pd.DataFrame({
            "const": 1.0,
            "size_z": GrowthFactors.zscore_series(df[size_col].astype(float)),
            "mom_z": GrowthFactors.zscore_series(df[momentum_col].astype(float)),
        })
        m = pd.concat([exp_z.rename("y"), X0], axis=1).dropna()
        if m.empty:
            df[output_col] = exp_z
            return df
        Y = m["y"].values
        X = m[["const", "size_z", "mom_z"]].values
        try:
            beta, *_ = np.linalg.lstsq(X, Y, rcond=None)
            fitted = X @ beta
            resid = Y - fitted
            df[output_col] = np.nan
            df.loc[m.index, output_col] = resid
        except Exception:
            df[output_col] = exp_z
        return df

if __name__ == "__main__":
    # Lightweight smoke test for attributes, composition, and NaN handling
    import sys
    try:
        test_tickers = ["AAPL", "MSFT", "AMZN", "GOOGL", "NVDA"]
        ds = DataService()
        rows: list[dict[str, float]] = []
        for t in test_tickers:
            try:
                vf = ValueFactors(t, ds)
                attrs = vf.compute_attributes()
                rows.append({"ticker": t, **attrs})
            except Exception as e:
                print(f"[warn] Failed computing attributes for {t}: {e}")
        frame = pd.DataFrame(rows)
        # Compose exposure (global z-score if sector not provided)
        frame = ValueFactors.compose_value_exposure(frame)
        frame = ValueFactors.orthogonalize_value(frame, exposure_col="value_exposure_raw")
        cols = [
            "ticker",
            "bp",
            "ep",
            "cfp",
            "fcf_yield",
            "sales_ev",
            "ebitda_ev",
            "ebit_ev",
            "div_yld",
            "value_exposure_raw",
            "value_exposure",
        ]
        print(frame[cols].to_string(index=False))
    except Exception as e:
        print(f"[error] Smoke test failed: {e}")
        sys.exit(1)


