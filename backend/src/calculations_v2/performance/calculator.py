from __future__ import annotations

import numpy as np
import pandas as pd
from backend.src.calculations_v2.risk.calculator import RiskCalculator
from backend.src.calculations_v2.core.data_service import DataService
from datetime import datetime, timedelta, timezone
from backend.src.calculations_v2.returns.calculator import ReturnsCalculator
from backend.src.calculations_v2.core.config import DEFAULT_TRADING_DAYS, DEFAULT_RF_ANNUAL


class PerformanceCalculator:
    """Core performance ratios based on a daily returns series."""

    @staticmethod
    def sharpe_ratio(
        daily_returns: pd.Series,
        rf_annual: float = DEFAULT_RF_ANNUAL,
        periods_per_year: int = DEFAULT_TRADING_DAYS,
        rf_series: pd.Series | None = None,
    ) -> float:
        r = pd.Series(daily_returns).dropna().astype(float)
        if len(r) < 2:
            return np.nan
        if rf_series is not None:
            rf_aligned = pd.Series(rf_series).reindex(r.index).astype(float)
            excess = (r - rf_aligned).dropna()
            if len(excess) < 2:
                return np.nan
        else:
            rf_daily = (1.0 + float(rf_annual)) ** (1.0 / float(periods_per_year)) - 1.0
            excess = r - rf_daily
        sigma = excess.std(ddof=1)
        if not np.isfinite(sigma) or sigma == 0:
            return np.nan
        return float(excess.mean() / sigma * np.sqrt(periods_per_year))

    @staticmethod
    def sortino_ratio(
        daily_returns: pd.Series,
        mar_annual: float = DEFAULT_RF_ANNUAL,
        periods_per_year: int = DEFAULT_TRADING_DAYS,
        mar_daily: float | None = None,
    ) -> float:
        r = pd.Series(daily_returns).dropna().astype(float)
        if len(r) < 2:
            return np.nan
        md = float(mar_daily) if mar_daily is not None else (1.0 + float(mar_annual)) ** (1.0 / float(periods_per_year)) - 1.0
        excess = r - md
        shortfall = np.minimum(excess, 0.0)
        semidev_daily = float(np.sqrt(np.mean(np.square(shortfall))))
        if not np.isfinite(semidev_daily) or semidev_daily == 0.0:
            return np.inf if float(excess.mean()) > 0.0 else np.nan
        return float((excess.mean() * periods_per_year) / (semidev_daily * np.sqrt(periods_per_year)))

    @staticmethod
    def calmar_ratio(annual_return: float, max_drawdown: float) -> float:
        if not np.isfinite(annual_return) or not np.isfinite(max_drawdown):
            return np.nan
        md = abs(max_drawdown)
        if md == 0:
            return np.inf
        return float(annual_return / md)

    @staticmethod
    def calmar_from_returns(r: pd.Series, periods_per_year: int = DEFAULT_TRADING_DAYS, years: int = 3) -> float:
        series = pd.Series(r).dropna().astype(float)
        min_len = int(years * periods_per_year)
        if len(series) < min_len:
            return np.nan
        window = series.iloc[-min_len:]
        equity = (1.0 + window).cumprod()
        mdd = (equity / equity.cummax() - 1.0).min()
        if not np.isfinite(mdd):
            return np.nan
        cagr = float(equity.iloc[-1] ** (periods_per_year / len(window)) - 1.0)
        if mdd == 0:
            return np.inf
        return float(cagr / abs(mdd))

    # ------------------------------------------------------------------
    # Additional performance metrics (Phase 2)
    # ------------------------------------------------------------------

    @staticmethod
    def treynor_ratio(
        daily_returns: pd.Series,
        market_daily_returns: pd.Series,
        rf_annual: float = DEFAULT_RF_ANNUAL,
        periods_per_year: int = DEFAULT_TRADING_DAYS,
    ) -> float:
        """Treynor ratio computed on aligned excess returns with geometric RF.

        Returns NaN on insufficient data or invalid beta.
        """
        # 1) Align series and drop NaNs
        data = pd.concat(
            [pd.Series(daily_returns, name="asset"), pd.Series(market_daily_returns, name="market")],
            axis=1,
        ).dropna()
        if len(data) < 2:
            return np.nan
        # 2) Geometric RF conversions
        rf_daily = (1.0 + float(rf_annual)) ** (1.0 / float(periods_per_year)) - 1.0
        ann_rf = (1.0 + rf_daily) ** float(periods_per_year) - 1.0
        # 3) Beta on excess returns (with intercept implied)
        x = data["market"].astype(float) - rf_daily
        y = data["asset"].astype(float) - rf_daily
        var_x = float(x.var(ddof=1))
        if not np.isfinite(var_x) or var_x == 0.0:
            return np.nan
        cov_xy = float(x.cov(y))
        beta = cov_xy / var_x
        if not np.isfinite(beta) or beta == 0.0:
            return np.nan
        # 4) Annualize portfolio return over the same window
        n = len(data)
        total_ret = float((1.0 + data["asset"]).prod() - 1.0)
        ann_port = (1.0 + total_ret) ** (float(periods_per_year) / float(n)) - 1.0
        # 5) Treynor
        return float((ann_port - ann_rf) / beta)

    @staticmethod
    def information_ratio(
        daily_returns: pd.Series,
        benchmark_daily_returns: pd.Series,
        periods_per_year: int = DEFAULT_TRADING_DAYS,
    ) -> float:
        """Ex-post Information Ratio on aligned series with guards."""
        data = pd.concat(
            [pd.Series(daily_returns, name="p"), pd.Series(benchmark_daily_returns, name="b")],
            axis=1,
        ).dropna()
        if len(data) < 2:
            return np.nan
        active = data["p"] - data["b"]
        te = float(active.std(ddof=1))
        if not np.isfinite(te) or te == 0.0:
            return np.nan
        return float((active.mean() / te) * np.sqrt(periods_per_year))

    @staticmethod
    def omega_ratio(daily_returns: pd.Series, threshold_daily: float = 0.0) -> float:
        """Omega ratio using discrete estimator at a daily threshold.

        Returns inf if losses==0 and gains>0; NaN if both gains and losses are zero.
        """
        r = pd.Series(daily_returns).dropna().astype(float)
        if r.empty:
            return np.nan
        excess = r - float(threshold_daily)
        gains = float(np.maximum(excess, 0.0).sum())
        losses = float(np.maximum(-excess, 0.0).sum())
        if losses == 0.0:
            return np.inf if gains > 0.0 else np.nan
        return float(gains / losses)

    @staticmethod
    def omega_ratio_from_annual(
        daily_returns: pd.Series,
        mar_annual: float = 0.0,
        periods_per_year: int = DEFAULT_TRADING_DAYS,
    ) -> float:
        """Omega ratio with an annual MAR converted geometrically to daily."""
        r = pd.Series(daily_returns).dropna().astype(float)
        if r.empty:
            return np.nan
        mar_daily = (1.0 + float(mar_annual)) ** (1.0 / float(periods_per_year)) - 1.0
        excess = r - mar_daily
        gains = float(np.maximum(excess, 0.0).sum())
        losses = float(np.maximum(-excess, 0.0).sum())
        if losses == 0.0:
            return np.inf if gains > 0.0 else np.nan
        return float(gains / losses)

    @staticmethod
    def sterling_ratio(annual_return: float, max_drawdown: float, adj: float = 1.1) -> float:
        denom = abs(max_drawdown) * adj
        if denom == 0:
            return np.inf
        return float(annual_return / denom)

    @staticmethod
    def cagr_from_returns(daily_returns: pd.Series, periods_per_year: int = DEFAULT_TRADING_DAYS) -> float:
        return ReturnsCalculator.annualized_return(daily_returns, trading_days=periods_per_year)

    @staticmethod
    def drawdown_series(equity: pd.Series) -> pd.Series:
        cummax = equity.cummax()
        safe = cummax.replace(0, np.nan)
        return equity / safe - 1.0

    @staticmethod
    def sterling_ratio_from_returns(daily_returns: pd.Series, periods_per_year: int = DEFAULT_TRADING_DAYS) -> float:
        r = pd.Series(daily_returns).dropna().astype(float)
        if r.empty:
            return np.nan
        equity = (1.0 + r).cumprod()
        dd = PerformanceCalculator.drawdown_series(equity)
        try:
            yearly = dd.groupby(dd.index.to_period('Y')).min().astype(float)
        except Exception:
            # Fallback: treat entire sample as one year
            yearly = pd.Series([float(dd.min())])
        if yearly.empty:
            return np.nan
        avg_annual_mdd = float(np.abs(yearly).mean())
        if avg_annual_mdd == 0.0:
            return np.inf
        cagr = PerformanceCalculator.cagr_from_returns(r, periods_per_year)
        if not np.isfinite(cagr):
            return np.nan
        return float(cagr / avg_annual_mdd)

    @staticmethod
    # Removed modified Sterling variant to keep a single canonical API.

    @staticmethod
    def _equity_curve(daily_returns: pd.Series) -> pd.Series:
        r = pd.Series(daily_returns).dropna().astype(float)
        return (1.0 + r).cumprod()

    @staticmethod
    def _drawdown_magnitudes(equity: pd.Series) -> np.ndarray:
        if equity is None or equity.empty:
            return np.array([], dtype=float)
        vals = equity.astype(float).values
        peak = vals[0]
        trough = vals[0]
        in_dd = False
        mags: list[float] = []
        for px in vals[1:]:
            if px >= peak:
                if in_dd:
                    mag = (trough / peak) - 1.0  # negative
                    mags.append(abs(float(mag)))
                    in_dd = False
                peak = px
                trough = px
            else:
                in_dd = True
                if px < trough:
                    trough = px
        if in_dd:
            mag = (trough / peak) - 1.0
            mags.append(abs(float(mag)))
        return np.array(mags, dtype=float)

    @staticmethod
    def burke_ratio(daily_returns: pd.Series, periods_per_year: int = DEFAULT_TRADING_DAYS) -> float:
        r = pd.Series(daily_returns).dropna().astype(float)
        if len(r) < 2:
            return np.nan
        equity = PerformanceCalculator._equity_curve(r)
        mags = PerformanceCalculator._drawdown_magnitudes(equity)
        denom = float(np.sqrt(np.sum(mags ** 2))) if mags.size else 0.0
        cagr = PerformanceCalculator.cagr_from_returns(r, periods_per_year)
        if not np.isfinite(cagr):
            return np.nan
        if denom == 0.0:
            return np.inf if cagr > 0.0 else np.nan
        return float(cagr / denom)

    @staticmethod
    def martin_ratio(
        daily_returns: pd.Series,
        rf_annual: float = 0.0,
        periods_per_year: int = DEFAULT_TRADING_DAYS,
    ) -> float:
        r = pd.Series(daily_returns).dropna().astype(float)
        if len(r) < 2:
            return np.nan
        # Equity curve and Ulcer Index (drawdowns as fractions)
        equity = (1.0 + r).cumprod()
        dd = equity / equity.cummax() - 1.0
        ulcer_index = float(np.sqrt(np.mean(np.square(dd))))
        # Annualized return (CAGR on same window)
        n = len(r)
        total = float((1.0 + r).prod() - 1.0)
        ann_ret = (1.0 + total) ** (float(periods_per_year) / float(n)) - 1.0
        # Annual risk-free (already annual input)
        ann_rf = float(rf_annual)
        ann_excess = ann_ret - ann_rf
        if not np.isfinite(ulcer_index) or ulcer_index == 0.0:
            return np.inf if ann_excess > 0.0 else np.nan
        return float(ann_excess / ulcer_index)

    @staticmethod
    def kappa_ratio(
        daily_returns: pd.Series,
        target_daily: float = 0.04 / 252,
        moment: int = 3,
    ) -> float:
        if daily_returns.empty:
            return np.nan
        excess = daily_returns - target_daily
        downside = excess[excess < 0]
        if len(downside) == 0:
            return np.inf
        lpm = np.mean(np.abs(downside) ** moment) ** (1 / moment)
        if lpm == 0:
            return np.nan
        return float(excess.mean() / lpm)

    @staticmethod
    def alpha(
        daily_returns: pd.Series,
        market_daily_returns: pd.Series,
        risk_free_daily: float = (1.0 + DEFAULT_RF_ANNUAL)**(1.0/DEFAULT_TRADING_DAYS) - 1.0,
        trading_days: int = DEFAULT_TRADING_DAYS,
    ) -> float:
        """Backward-compatible wrapper that calls Jensen's alpha (regression intercept).

        Converts daily RF to annual via geometric compounding and delegates to alpha_jensen.
        """
        rf_annual = (1.0 + float(risk_free_daily)) ** float(trading_days) - 1.0
        return PerformanceCalculator.alpha_jensen(
            daily_returns=daily_returns,
            market_daily_returns=market_daily_returns,
            rf_annual=rf_annual,
            periods_per_year=trading_days,
        )

    @staticmethod
    def alpha_jensen(
        daily_returns: pd.Series,
        market_daily_returns: pd.Series,
        rf_annual: float = DEFAULT_RF_ANNUAL,
        periods_per_year: int = DEFAULT_TRADING_DAYS,
    ) -> float:
        """Jensen's alpha via regression intercept on aligned excess returns.

        Returns annualized alpha (alpha_daily * periods_per_year). Requires ≥20 obs.
        """
        df = pd.concat(
            [pd.Series(daily_returns, name="p"), pd.Series(market_daily_returns, name="m")],
            axis=1,
        ).dropna()
        if len(df) < 20:
            return np.nan
        rf_daily = (1.0 + float(rf_annual)) ** (1.0 / float(periods_per_year)) - 1.0
        y = df["p"].astype(float) - rf_daily
        x = df["m"].astype(float) - rf_daily
        # Design matrix with intercept
        X = np.column_stack([np.ones(len(x), dtype=float), x.values.astype(float)])
        Y = y.values.astype(float)
        try:
            coef, *_ = np.linalg.lstsq(X, Y, rcond=None)
            alpha_daily = float(coef[0])
        except Exception:
            return np.nan
        if not np.isfinite(alpha_daily):
            return np.nan
        return float(alpha_daily * float(periods_per_year))

    @staticmethod
    def capture_ratios(
        period_returns: pd.Series,
        benchmark_period_returns: pd.Series,
        periods_per_year: int | None = None,
        strict_zero_split: bool = True,
    ) -> tuple[float, float]:
        """Up/Down capture ratios with geometric means within regimes.

        - If periods_per_year is provided (e.g., 12 for monthly, 252 for daily),
          annualizes regime geometric means before taking the ratio.
        - If strict_zero_split is True: up if bench > 0, down if bench < 0; else up if bench ≥ 0.
        """
        df = pd.concat(
            [pd.Series(period_returns, name="fund"), pd.Series(benchmark_period_returns, name="bench")],
            axis=1,
        ).dropna()
        if df.empty:
            return (np.nan, np.nan)
        bench = df["bench"].astype(float)
        fund = df["fund"].astype(float)
        if strict_zero_split:
            up_mask = bench > 0.0
            down_mask = bench < 0.0
        else:
            up_mask = bench >= 0.0
            down_mask = bench < 0.0

        def regime_capture(mask: pd.Series) -> float:
            n = int(mask.sum())
            if n == 0:
                return np.nan
            f = fund[mask]
            b = bench[mask]
            # Compound within regime
            f_prod = float((1.0 + f).prod())
            b_prod = float((1.0 + b).prod())
            if not np.isfinite(f_prod) or not np.isfinite(b_prod) or b_prod <= 0.0:
                return np.nan
            f_gm = f_prod ** (1.0 / float(n)) - 1.0
            b_gm = b_prod ** (1.0 / float(n)) - 1.0
            if not np.isfinite(b_gm) or b_gm == 0.0:
                return np.nan
            if periods_per_year and periods_per_year > 0:
                f_ann = (1.0 + f_gm) ** float(periods_per_year) - 1.0
                b_ann = (1.0 + b_gm) ** float(periods_per_year) - 1.0
                return float(f_ann / b_ann) if b_ann != 0.0 and np.isfinite(b_ann) else np.nan
            return float(f_gm / b_gm)

        up_capture = regime_capture(up_mask)
        down_capture = regime_capture(down_mask)
        return (up_capture, down_capture)

    @staticmethod
    def win_rate(
        daily_returns: pd.Series,
        threshold: float = 0.0,
        include_zeros_in_denominator: bool = False,
        count_zero_as_win: bool = False,
    ) -> float:
        r = pd.Series(daily_returns).dropna().astype(float)
        if r.empty:
            return np.nan
        wins = int((r > float(threshold)).sum())
        zeros = int((r == float(threshold)).sum())
        if count_zero_as_win:
            wins += zeros
        denom = int(len(r)) if include_zeros_in_denominator else int(len(r) - zeros)
        if denom <= 0:
            return np.nan
        return float(wins / denom)

    @staticmethod
    def profit_factor_from_returns(daily_returns: pd.Series) -> float:
        r = pd.Series(daily_returns).dropna().astype(float)
        if r.empty:
            return np.nan
        gross_profits = float(r[r > 0.0].sum())
        gross_losses = float(-r[r < 0.0].sum())
        if gross_losses == 0.0:
            return np.inf if gross_profits > 0.0 else np.nan
        return float(gross_profits / gross_losses)

    @staticmethod
    def profit_factor(daily_returns: pd.Series, start_equity: float = 1.0) -> float:
        r = pd.Series(daily_returns).dropna().astype(float)
        if r.empty:
            return np.nan
        equity = float(start_equity)
        gross_profits = 0.0
        gross_losses = 0.0
        for rt in r.values:
            pnl = equity * float(rt)
            if rt > 0.0:
                gross_profits += pnl
            elif rt < 0.0:
                gross_losses += -pnl
            equity *= (1.0 + float(rt))
        if gross_losses == 0.0:
            return np.inf if gross_profits > 0.0 else np.nan
        return float(gross_profits / gross_losses)

    @staticmethod
    def profit_factor_from_pnl(trade_pnl: pd.Series) -> float:
        x = pd.Series(trade_pnl).dropna().astype(float)
        if x.empty:
            return np.nan
        gross_profits = float(x[x > 0.0].sum())
        gross_losses = float(-x[x < 0.0].sum())
        if gross_losses == 0.0:
            return np.inf if gross_profits > 0.0 else np.nan
        return float(gross_profits / gross_losses)

    @staticmethod
    def pain_index(daily_returns: pd.Series) -> float:
        r = pd.Series(daily_returns).dropna().astype(float)
        if r.empty:
            return np.nan
        equity = (1.0 + r).cumprod()
        dd = equity / equity.cummax() - 1.0
        return float(np.abs(dd).mean())

    @staticmethod
    def tail_ratio(daily_returns: pd.Series, q: float = 5.0) -> float:
        """Tail ratio: |upper tail| / |lower tail| using (100-q)th and qth percentiles."""
        r = pd.Series(daily_returns).dropna().astype(float)
        if r.empty or not (0.0 < float(q) < 50.0):
            return np.nan
        p_low = float(np.nanpercentile(r, float(q)))
        p_high = float(np.nanpercentile(r, 100.0 - float(q)))
        # Degenerate regimes
        if (p_low >= 0.0) and (p_high > 0.0):
            return np.inf
        if (p_high <= 0.0) and (p_low < 0.0):
            return 0.0
        denom = abs(p_low)
        if denom == 0.0:
            return np.inf if p_high > 0.0 else np.nan
        return float(abs(p_high) / denom)

    @staticmethod
    def gain_loss_ratio(
        daily_returns: pd.Series,
        threshold: float = 0.0,
        method: str = "mean",
    ) -> float:
        r = pd.Series(daily_returns).dropna().astype(float)
        if r.empty:
            return np.nan
        gains = (r[r > float(threshold)] - float(threshold))
        losses = (float(threshold) - r[r < float(threshold)])  # positive magnitudes
        if gains.empty and losses.empty:
            return np.nan
        if losses.empty:
            return np.inf
        if method == "mean":
            num, den = float(gains.mean()) if not gains.empty else 0.0, float(losses.mean())
        elif method == "sum":
            num, den = float(gains.sum()) if not gains.empty else 0.0, float(losses.sum())
        elif method == "median":
            num, den = float(gains.median()) if not gains.empty else 0.0, float(losses.median())
        else:
            raise ValueError("method must be 'mean', 'sum', or 'median'")
        if den == 0.0:
            return np.inf
        return float(num / den)

    @staticmethod
    def ulcer_index(
        daily_returns: pd.Series,
        window: int | None = None,
        as_percent: bool = False,
    ) -> float:
        r = pd.Series(daily_returns).dropna().astype(float)
        if r.empty:
            return np.nan
        if window is not None and window > 0:
            r = r.iloc[-int(window):]
        equity = (1.0 + r).cumprod()
        dd = equity / equity.cummax() - 1.0
        scale = 100.0 if as_percent else 1.0
        ui = float(np.sqrt(np.mean((dd * scale) ** 2)))
        return ui

    @staticmethod
    def ulcer_index_from_prices(
        prices: pd.Series,
        window: int | None = None,
        as_percent: bool = False,
    ) -> float:
        # Delegate to price-based Ulcer Index in RiskCalculator; ignore window/as_percent to keep parity
        return RiskCalculator.ulcer_index(prices)

    @staticmethod
    def ulcer_index_monthly(
        daily_returns: pd.Series,
        as_percent: bool = False,
    ) -> float:
        r = pd.Series(daily_returns).dropna().astype(float)
        if r.empty:
            return np.nan
        try:
            monthly = (1.0 + r).resample("ME").prod() - 1.0
        except Exception:
            return np.nan
        if monthly.empty:
            return np.nan
        equity_m = (1.0 + monthly).cumprod()
        dd_m = equity_m / equity_m.cummax() - 1.0
        scale = 100.0 if as_percent else 1.0
        return float(np.sqrt(np.mean((dd_m * scale) ** 2)))

    @staticmethod
    def tracking_error(
        daily_returns: pd.Series,
        benchmark_daily_returns: pd.Series,
        periods_per_year: int = DEFAULT_TRADING_DAYS,
    ) -> float:
        """Tracking error - annualized std dev of active returns (aligned series)."""
        df = pd.concat(
            [pd.Series(daily_returns, name="p"), pd.Series(benchmark_daily_returns, name="b")],
            axis=1,
        ).dropna().astype(float)
        if len(df) < 2:
            return np.nan
        active = df["p"] - df["b"]
        te = float(active.std(ddof=1))
        if not np.isfinite(te):
            return np.nan
        return float(te * np.sqrt(float(periods_per_year)))

    @staticmethod
    def appraisal_ratio(
        daily_returns: pd.Series,
        market_daily_returns: pd.Series,
        rf_annual: float = DEFAULT_RF_ANNUAL,
        periods_per_year: int = DEFAULT_TRADING_DAYS,
    ) -> float:
        """Appraisal ratio = annualized alpha / annualized residual risk (aligned excess returns)."""
        df = pd.concat(
            [pd.Series(daily_returns, name="p"), pd.Series(market_daily_returns, name="m")],
            axis=1,
        ).dropna().astype(float)
        if len(df) < 20:
            return np.nan
        rf_d = (1.0 + float(rf_annual)) ** (1.0 / float(periods_per_year)) - 1.0
        y = df["p"] - rf_d
        x = df["m"] - rf_d
        var_x = float(x.var(ddof=1))
        if not np.isfinite(var_x) or var_x == 0.0:
            return np.nan
        cov_xy = float(x.cov(y))
        beta = cov_xy / var_x
        if not np.isfinite(beta):
            return np.nan
        y_mean = float(y.mean())
        x_mean = float(x.mean())
        alpha_daily = y_mean - beta * x_mean
        # Residuals and residual std (daily)
        resid = y - (alpha_daily + beta * x)
        resid_std_daily = float(resid.std(ddof=1))
        if not np.isfinite(resid_std_daily) or resid_std_daily == 0.0:
            return np.nan
        alpha_ann = float(alpha_daily * float(periods_per_year))
        resid_std_ann = float(resid_std_daily * np.sqrt(float(periods_per_year)))
        return float(alpha_ann / resid_std_ann)


if __name__ == "__main__":
    from datetime import datetime, timedelta, timezone
    from backend.src.calculations_v2.core.data_service import DataService

    try:
        # Parameters
        test_tickers = [
            "AAPL", "MSFT", "AMZN", "GOOGL", "NVDA",
            "META", "TSLA", "JPM", "JNJ", "XOM",
        ]
        benchmark = "SPY"
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=252 * 3)

        # Bulk fetch closing price series via DataService
        ds = DataService()
        series_map = ds.get_bulk_close_series(test_tickers + [benchmark], start, end)
        mkt = series_map.get(benchmark)
        if mkt is None or mkt.empty:
            raise RuntimeError("Benchmark series not available")
        rm = mkt.astype(float).pct_change(fill_method=None).dropna()

        rows: list[dict[str, float]] = []
        for t in test_tickers:
            try:
                s = series_map.get(t)
                if s is None or s.empty:
                    rows.append({"ticker": t})
                    continue
                r = s.astype(float).pct_change(fill_method=None).dropna()

                # Core risk-adjusted metrics
                sharpe = PerformanceCalculator.sharpe_ratio(r, rf_annual=DEFAULT_RF_ANNUAL, periods_per_year=DEFAULT_TRADING_DAYS)
                sortino = PerformanceCalculator.sortino_ratio(r, mar_annual=DEFAULT_RF_ANNUAL, periods_per_year=DEFAULT_TRADING_DAYS)
                treynor = PerformanceCalculator.treynor_ratio(r, rm, rf_annual=DEFAULT_RF_ANNUAL, periods_per_year=DEFAULT_TRADING_DAYS)
                info = PerformanceCalculator.information_ratio(r, rm, periods_per_year=DEFAULT_TRADING_DAYS)
                omega = PerformanceCalculator.omega_ratio_from_annual(r, mar_annual=0.0, periods_per_year=DEFAULT_TRADING_DAYS)
                sterling = PerformanceCalculator.sterling_ratio_from_returns(r, periods_per_year=DEFAULT_TRADING_DAYS)
                burke = PerformanceCalculator.burke_ratio(r, periods_per_year=DEFAULT_TRADING_DAYS)
                martin = PerformanceCalculator.martin_ratio(r, rf_annual=DEFAULT_RF_ANNUAL, periods_per_year=DEFAULT_TRADING_DAYS)
                alpha = PerformanceCalculator.alpha_jensen(r, rm, rf_annual=DEFAULT_RF_ANNUAL, periods_per_year=DEFAULT_TRADING_DAYS)

                # Capture ratios (daily per-period ratio and annualized monthly-style)
                up_cap_daily, down_cap_daily = PerformanceCalculator.capture_ratios(r, rm, periods_per_year=None, strict_zero_split=True)
                up_cap_ann, down_cap_ann = PerformanceCalculator.capture_ratios(r, rm, periods_per_year=DEFAULT_TRADING_DAYS, strict_zero_split=True)

                # Hit ratio and profit factor variants
                hit = PerformanceCalculator.win_rate(r, threshold=0.0, include_zeros_in_denominator=False, count_zero_as_win=False)
                pf_ret = PerformanceCalculator.profit_factor_from_returns(r)
                pf_eq = PerformanceCalculator.profit_factor(r, start_equity=1.0)

                # Other diagnostics
                pain = PerformanceCalculator.pain_index(r)
                tail = PerformanceCalculator.tail_ratio(r, q=5.0)
                gl_mean = PerformanceCalculator.gain_loss_ratio(r, threshold=0.0, method="mean")
                ui = PerformanceCalculator.ulcer_index(r, window=None, as_percent=False)
                ui_pct = PerformanceCalculator.ulcer_index(r, window=DEFAULT_TRADING_DAYS, as_percent=True)

                rows.append({
                    "ticker": t,
                    "sharpe": float(sharpe) if np.isfinite(sharpe) else np.nan,
                    "sortino": float(sortino) if np.isfinite(sortino) else np.nan,
                    "treynor": float(treynor) if np.isfinite(treynor) else np.nan,
                    "info": float(info) if np.isfinite(info) else np.nan,
                    "omega": float(omega) if np.isfinite(omega) else np.nan,
                    "sterling": float(sterling) if np.isfinite(sterling) else np.nan,
                    "burke": float(burke) if np.isfinite(burke) else np.nan,
                    "martin": float(martin) if np.isfinite(martin) else np.nan,
                    "alpha": float(alpha) if np.isfinite(alpha) else np.nan,
                    "up_cap_daily": float(up_cap_daily) if up_cap_daily is not None and np.isfinite(up_cap_daily) else np.nan,
                    "down_cap_daily": float(down_cap_daily) if down_cap_daily is not None and np.isfinite(down_cap_daily) else np.nan,
                    "up_cap_ann": float(up_cap_ann) if up_cap_ann is not None and np.isfinite(up_cap_ann) else np.nan,
                    "down_cap_ann": float(down_cap_ann) if down_cap_ann is not None and np.isfinite(down_cap_ann) else np.nan,
                    "win_rate": float(hit) if np.isfinite(hit) else np.nan,
                    "pf_ret": float(pf_ret) if np.isfinite(pf_ret) else np.nan,
                    "pf_eq": float(pf_eq) if np.isfinite(pf_eq) else np.nan,
                    "pain": float(pain) if np.isfinite(pain) else np.nan,
                    "tail_ratio": float(tail) if np.isfinite(tail) else np.nan,
                    "gain_loss": float(gl_mean) if np.isfinite(gl_mean) else np.nan,
                    "ulcer": float(ui) if np.isfinite(ui) else np.nan,
                    "ulcer_252pct": float(ui_pct) if np.isfinite(ui_pct) else np.nan,
                })
            except Exception:
                rows.append({"ticker": t})

        out = pd.DataFrame(rows)
        if not out.empty:
            cols = [
                "ticker",
                "sharpe", "sortino", "treynor", "info", "alpha",
                "omega", "sterling", "burke", "martin",
                "up_cap_daily", "down_cap_daily", "up_cap_ann", "down_cap_ann",
                "win_rate", "pf_ret", "pf_eq", "pain", "tail_ratio", "gain_loss",
                "ulcer", "ulcer_252pct",
            ]
            print(out[cols].to_string(index=False))
        else:
            print("No results")
    except Exception as e:
        print(f"[error] Failed to compute performance ratios: {e}")