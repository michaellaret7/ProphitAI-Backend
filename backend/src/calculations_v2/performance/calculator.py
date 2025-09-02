from __future__ import annotations

import numpy as np
import pandas as pd


class PerformanceCalculator:
    """Core performance ratios based on a daily returns series."""

    @staticmethod
    def sharpe_ratio(daily_returns: pd.Series, risk_free_daily: float = 0.04 / 252, trading_days: int = 252) -> float:
        if daily_returns.empty:
            return 0.0
        excess = daily_returns - risk_free_daily
        std = excess.std(ddof=1)
        if std == 0 or np.isnan(std):
            return np.nan
        return float((excess.mean() / std) * np.sqrt(trading_days))

    @staticmethod
    def sortino_ratio(daily_returns: pd.Series, target_daily: float = 0.04 / 252, trading_days: int = 252) -> float:
        if daily_returns.empty:
            return 0.0
        downside = (daily_returns[daily_returns < target_daily] - target_daily)
        if len(downside) == 0:
            return np.inf
        downside_dev = np.sqrt(np.mean(downside**2))
        if downside_dev == 0:
            return np.nan
        ann_excess = (daily_returns.mean() - target_daily) * trading_days
        return float(ann_excess / (downside_dev * np.sqrt(trading_days)))

    @staticmethod
    def calmar_ratio(annual_return: float, max_drawdown: float) -> float:
        md = abs(max_drawdown)
        if md == 0:
            return np.inf
        return float(annual_return / md)

    # ------------------------------------------------------------------
    # Additional performance metrics (Phase 2)
    # ------------------------------------------------------------------

    @staticmethod
    def treynor_ratio(
        daily_returns: pd.Series,
        market_daily_returns: pd.Series,
        risk_free_daily: float = 0.04 / 252,
        trading_days: int = 252,
    ) -> float:
        from backend.src.calculations_v2.risk.calculator import RiskCalculator

        if daily_returns.empty or market_daily_returns.empty:
            return np.nan
        # Annualized portfolio return
        n = len(daily_returns)
        total = (1 + daily_returns).prod() - 1
        ann_port = (1 + total) ** (trading_days / n) - 1 if n > 0 else 0.0
        ann_rf = risk_free_daily * trading_days
        beta = RiskCalculator.beta(daily_returns, market_daily_returns)
        if beta == 0 or np.isnan(beta):
            return np.nan
        return float((ann_port - ann_rf) / beta)

    @staticmethod
    def information_ratio(
        daily_returns: pd.Series,
        benchmark_daily_returns: pd.Series,
        trading_days: int = 252,
    ) -> float:
        active = (daily_returns - benchmark_daily_returns).dropna()
        if active.empty:
            return np.nan
        te = active.std(ddof=1)
        if te == 0 or np.isnan(te):
            return np.nan
        return float((active.mean() * np.sqrt(trading_days)) / te)

    @staticmethod
    def omega_ratio(daily_returns: pd.Series, threshold_daily: float = 0.0) -> float:
        if daily_returns.empty:
            return np.nan
        excess = daily_returns - threshold_daily
        gains = excess[excess > 0].sum()
        losses = -excess[excess < 0].sum()
        if losses == 0:
            return np.inf
        return float(gains / losses)

    @staticmethod
    def sterling_ratio(annual_return: float, max_drawdown: float, adj: float = 1.1) -> float:
        denom = abs(max_drawdown) * adj
        if denom == 0:
            return np.inf
        return float(annual_return / denom)

    @staticmethod
    def burke_ratio(daily_returns: pd.Series, trading_days: int = 252) -> float:
        if daily_returns.empty:
            return np.nan
        cumulative = (1 + daily_returns).cumprod()
        running_max = cumulative.cummax()
        dd = (cumulative - running_max) / running_max
        sum_sq = np.sum(np.square(dd.values))
        if sum_sq == 0:
            return np.inf
        # Annualized return
        n = len(daily_returns)
        total = (1 + daily_returns).prod() - 1
        ann_ret = (1 + total) ** (trading_days / n) - 1 if n > 0 else 0.0
        return float(ann_ret / np.sqrt(sum_sq))

    @staticmethod
    def martin_ratio(daily_returns: pd.Series, trading_days: int = 252) -> float:
        if daily_returns.empty:
            return np.nan
        cumulative = (1 + daily_returns).cumprod()
        running_max = cumulative.cummax()
        dd = (cumulative - running_max) / running_max
        ulcer_index = np.sqrt(np.mean(np.square(dd.values)))
        if ulcer_index == 0:
            return np.inf
        # Annualized return
        n = len(daily_returns)
        total = (1 + daily_returns).prod() - 1
        ann_ret = (1 + total) ** (trading_days / n) - 1 if n > 0 else 0.0
        return float(ann_ret / ulcer_index)

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
        risk_free_daily: float = 0.04 / 252,
        trading_days: int = 252,
    ) -> float:
        from backend.src.calculations_v2.risk.calculator import RiskCalculator

        if daily_returns.empty or market_daily_returns.empty:
            return np.nan
        # Annualized returns
        n_p = len(daily_returns)
        total_p = (1 + daily_returns).prod() - 1
        ann_p = (1 + total_p) ** (trading_days / n_p) - 1 if n_p > 0 else 0.0

        n_m = len(market_daily_returns)
        total_m = (1 + market_daily_returns).prod() - 1
        ann_m = (1 + total_m) ** (trading_days / n_m) - 1 if n_m > 0 else 0.0

        beta = RiskCalculator.beta(daily_returns, market_daily_returns)
        ann_rf = risk_free_daily * trading_days
        expected = ann_rf + beta * (ann_m - ann_rf) if not np.isnan(beta) else np.nan
        if np.isnan(expected):
            return np.nan
        return float(ann_p - expected)

    @staticmethod
    def capture_ratios(
        daily_returns: pd.Series,
        benchmark_daily_returns: pd.Series,
    ) -> tuple[float, float]:
        df = pd.concat([daily_returns, benchmark_daily_returns], axis=1).dropna()
        if df.empty:
            return (np.nan, np.nan)
        fund = df.iloc[:, 0]
        bench = df.iloc[:, 1]

        up_mask = bench >= 0
        down_mask = bench < 0

        if up_mask.sum() == 0:
            up = np.nan
        else:
            fu = (1 + fund[up_mask]).prod() ** (1 / up_mask.sum()) - 1
            bu = (1 + bench[up_mask]).prod() ** (1 / up_mask.sum()) - 1
            up = float(fu / bu) if bu != 0 else np.nan

        if down_mask.sum() == 0:
            down = np.nan
        else:
            fd = (1 + fund[down_mask]).prod() ** (1 / down_mask.sum()) - 1
            bd = (1 + bench[down_mask]).prod() ** (1 / down_mask.sum()) - 1
            down = float(fd / bd) if bd != 0 else np.nan

        return (up, down)

    @staticmethod
    def win_rate(daily_returns: pd.Series) -> float:
        if len(daily_returns) == 0:
            return 0.0
        return float((daily_returns > 0).sum() / len(daily_returns))

    @staticmethod
    def profit_factor(daily_returns: pd.Series) -> float:
        if len(daily_returns) == 0:
            return 0.0
        gross_profits = daily_returns[daily_returns > 0].sum()
        gross_losses = -daily_returns[daily_returns < 0].sum()
        if gross_losses == 0:
            return np.inf
        return float(gross_profits / gross_losses)

    @staticmethod
    def appraisal_ratio(
        daily_returns: pd.Series,
        market_daily_returns: pd.Series,
        risk_free_daily: float = 0.04 / 252,
        trading_days: int = 252,
    ) -> float:
        """Appraisal ratio = alpha / residual risk (annualized).

        Alpha is CAPM alpha (annualized). Residual risk is std dev of regression residuals (annualized).
        """
        if daily_returns.empty or market_daily_returns.empty:
            return np.nan
        df = pd.concat([daily_returns, market_daily_returns], axis=1).dropna()
        if df.empty:
            return np.nan
        y = df.iloc[:, 0] - risk_free_daily
        x = df.iloc[:, 1] - risk_free_daily
        # OLS beta and alpha on daily basis
        var_x = x.var(ddof=1)
        if var_x == 0 or np.isnan(var_x):
            return np.nan
        cov_xy = x.cov(y)
        beta = cov_xy / var_x
        alpha_daily = y.mean() - beta * x.mean()
        # Residuals and residual std
        residuals = y - (alpha_daily + beta * x)
        resid_std_daily = residuals.std(ddof=1)
        if resid_std_daily == 0 or np.isnan(resid_std_daily):
            return np.nan
        # Annualize alpha and residual risk
        alpha_ann = alpha_daily * trading_days
        resid_std_ann = resid_std_daily * np.sqrt(trading_days)
        return float(alpha_ann / resid_std_ann)


