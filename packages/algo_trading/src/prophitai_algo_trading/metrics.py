"""Backtest performance metrics.

Computes return, risk, and per-trade metrics from an equity curve and a
trade log. No SPY auto-fetch — if you want alpha-vs-benchmark, pass prices
explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from prophitai_calculations.risk.benchmark import calc_beta


SECONDS_PER_YEAR = 365.25 * 86_400
EPSILON = 1e-9


@dataclass
class BacktestResult:
    """Container for a backtest's outputs."""

    equity_curve: pd.DataFrame
    trades: pd.DataFrame
    metrics: dict[str, float | int] = field(default_factory=dict)


def calculate_metrics(
    equity_curve: pd.DataFrame,
    trades: pd.DataFrame,
    benchmark: pd.Series | None = None,
    risk_free_rate: float = 0.0,
    warmup: int = 0,
) -> dict[str, float | int | None]:
    """Compute return, risk, trade, and benchmark-relative metrics.

    Args:
        equity_curve: DataFrame with 'equity' column, datetime-indexed.
        trades: DataFrame with pnl, return_pct, direction columns.
        benchmark: Optional benchmark price series indexed on the same
            timeline (e.g., SPY close, or an equal-weighted universe
            proxy). Enables beta + Jensen's alpha.
        risk_free_rate: Annual risk-free rate for Sharpe and Jensen's alpha.
        warmup: Bars to skip from the front of the equity curve before
            computing return/risk metrics (flat warmup phase depresses Sharpe).

    Returns:
        Dict of metric name -> value. Benchmark-relative metrics appear
        when ``benchmark`` is provided; otherwise they are absent.
    """
    curve = equity_curve[~equity_curve.index.duplicated(keep="last")].sort_index()

    if (curve["equity"] <= 0).any():
        raise ValueError("Equity curve has non-positive values — accounting is broken.")

    effective = curve

    if 0 < warmup < len(curve) - 1:
        effective = curve.iloc[warmup:]

    span_seconds = (effective.index[-1] - effective.index[0]).total_seconds()
    years = max(span_seconds / SECONDS_PER_YEAR, EPSILON)
    bars_per_year = len(effective) / years

    metrics: dict[str, float | int | None] = {
        **_return_metrics(effective, years),
        **_risk_metrics(effective, bars_per_year, risk_free_rate),
        **_trade_metrics(trades),
    }

    if benchmark is not None:
        metrics.update(
            _benchmark_metrics(effective, benchmark, years, risk_free_rate),
        )

    return metrics


def _return_metrics(curve: pd.DataFrame, years: float) -> dict[str, float]:
    """Total and annualized return."""
    equity = curve["equity"]
    initial = float(equity.iloc[0])
    final = float(equity.iloc[-1])

    total = (final / initial - 1.0) * 100.0
    annualized = ((final / initial) ** (1.0 / years) - 1.0) * 100.0 if len(equity) > 1 else 0.0

    return {
        "total_return_pct": round(total, 2),
        "annualized_return_pct": round(annualized, 2),
    }


def _risk_metrics(
    curve: pd.DataFrame, bars_per_year: float, rf_annual: float,
) -> dict[str, float]:
    """Max drawdown and annualized Sharpe (log returns)."""
    equity = curve["equity"]

    cum_max = equity.cummax()
    drawdown = (equity - cum_max) / cum_max
    max_dd = round(float(drawdown.min()) * 100.0, 2)

    log_returns = np.log(equity).diff().dropna()
    std = float(log_returns.std())

    if len(log_returns) > 1 and std > 1e-10:
        rf_per_bar = np.log(1.0 + rf_annual) / bars_per_year
        excess = log_returns - rf_per_bar
        sharpe = round(float((excess.mean() / std) * np.sqrt(bars_per_year)), 2)
    else:
        sharpe = 0.0

    return {
        "max_drawdown_pct": max_dd,
        "sharpe_ratio": sharpe,
    }


def _benchmark_metrics(
    curve: pd.DataFrame,
    benchmark: pd.Series,
    years: float,
    rf_annual: float,
) -> dict[str, float | None]:
    """Beta and Jensen's alpha of the portfolio vs a benchmark price series.

    Both series are strictly intersected on their datetime indexes before
    any returns or annualizations are computed. The same common date
    range drives portfolio annualization, benchmark annualization, and
    the return pair fed into ``calc_beta`` — so beta, alphas, and the
    annualization horizon are internally consistent.

    Args:
        curve: Post-warmup equity DataFrame (must have 'equity' column).
        benchmark: Price series (not returns) at any cadence.
        years: Horizon used for annualization — passed in so it matches
            the same effective span used by the return/risk metrics.
        rf_annual: Annual risk-free rate.
    """
    none_result = {
        "benchmark_return_pct": None,
        "beta_vs_benchmark": None,
        "alpha_vs_benchmark_pct": None,
    }

    if benchmark is None or benchmark.empty or len(benchmark) < 2:
        return none_result

    benchmark = benchmark.dropna()

    if (benchmark <= 0).any():
        return none_result

    equity = curve["equity"]

    # Reason: inner-join the two series on date so start/end and returns all
    #         come from the identical sample — no ffill magic, no hidden shifts.
    common = equity.index.intersection(benchmark.index)

    if len(common) < 2:
        return none_result

    equity_aligned = equity.loc[common]
    bench_aligned = benchmark.loc[common]

    bench_start = float(bench_aligned.iloc[0])
    bench_end = float(bench_aligned.iloc[-1])
    port_start = float(equity_aligned.iloc[0])
    port_end = float(equity_aligned.iloc[-1])

    bench_total_return_pct = (bench_end / bench_start - 1.0) * 100.0

    if years <= 0 or port_start <= 0 or bench_start <= 0:
        return {
            "benchmark_return_pct": round(bench_total_return_pct, 2),
            "beta_vs_benchmark": None,
            "alpha_vs_benchmark_pct": None,
        }

    bench_annualized = (bench_end / bench_start) ** (1.0 / years) - 1.0
    port_annualized = (port_end / port_start) ** (1.0 / years) - 1.0

    port_returns = equity_aligned.pct_change().dropna()
    bench_returns = bench_aligned.pct_change().dropna()

    beta = calc_beta(port_returns, bench_returns)

    if beta is None:
        alpha_pct = None
    else:
        expected = rf_annual + beta * (bench_annualized - rf_annual)
        alpha_pct = (port_annualized - expected) * 100.0

    return {
        "benchmark_return_pct": round(bench_total_return_pct, 2),
        "beta_vs_benchmark": round(beta, 3) if beta is not None else None,
        "alpha_vs_benchmark_pct": round(alpha_pct, 2) if alpha_pct is not None else None,
    }


def _trade_metrics(trades: pd.DataFrame) -> dict[str, float | int]:
    """Per-trade stats: count, win rate, profit factor, averages, extremes."""
    total = len(trades)

    if total == 0:
        return {
            "total_trades": 0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "avg_trade_return_pct": 0.0,
            "avg_win_pct": 0.0,
            "avg_loss_pct": 0.0,
            "largest_win": 0.0,
            "largest_loss": 0.0,
            "long_trades": 0,
            "short_trades": 0,
        }

    winners = trades[trades["pnl"] > 0]
    losers = trades[trades["pnl"] < 0]

    gross_profit = float(winners["pnl"].sum()) if len(winners) else 0.0
    gross_loss = float(abs(losers["pnl"].sum())) if len(losers) else 0.0

    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else float("inf")

    return {
        "total_trades": total,
        "win_rate_pct": round(len(winners) / total * 100.0, 2),
        "profit_factor": profit_factor,
        "avg_trade_return_pct": round(float(trades["return_pct"].mean()), 2),
        "avg_win_pct": round(float(winners["return_pct"].mean()), 2) if len(winners) else 0.0,
        "avg_loss_pct": round(float(losers["return_pct"].mean()), 2) if len(losers) else 0.0,
        "largest_win": round(float(trades["pnl"].max()), 2),
        "largest_loss": round(float(trades["pnl"].min()), 2),
        "long_trades": int((trades["direction"] == "long").sum()),
        "short_trades": int((trades["direction"] == "short").sum()),
    }
