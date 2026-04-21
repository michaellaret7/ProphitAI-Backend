"""Pure functions for computing backtest performance metrics.

Takes equity curve and trades DataFrames produced by SimulatedPortfolio
and returns a dictionary of all computed metrics.
"""

import numpy as np
import pandas as pd

from prophitai_calculations.config import DEFAULT_RF_ANNUAL
from prophitai_calculations.risk.benchmark import calc_beta

# Reason: Sharpe and Jensen's alpha read the same risk-free rate from
# calculations.config. Default is 0, so both metrics judge strategies on
# raw return / vol rather than penalizing against a hardcoded UST yield.
RISK_FREE_RATE = DEFAULT_RF_ANNUAL
SECONDS_PER_YEAR = 365.25 * 86_400
EPSILON = 1e-9


def calculate_metrics(
    equity_curve: pd.DataFrame,
    trades: pd.DataFrame,
    benchmark_prices: pd.Series | None = None,
    warmup: int = 0,
) -> dict:
    """Calculate all performance metrics from backtest results.

    Args:
        equity_curve: DataFrame with 'equity' column, datetime-indexed.
        trades: DataFrame with one row per round-trip trade, must have
            'pnl', 'return_pct', and 'direction' columns.
        benchmark_prices: Optional Series of benchmark close prices (e.g. SPY),
            datetime-indexed. When provided, Jensen's alpha is computed.
        warmup: Number of leading bars to exclude from return/risk/benchmark
            metrics. Indicators with long lookbacks (e.g. 504-bar z-scores)
            produce a flat equity curve during warmup that artificially
            depresses Sharpe — slicing those bars gives an honest measure of
            the strategy's post-warmup behaviour. Per-trade metrics are
            unaffected. Default 0 (no slicing) for backwards compatibility.

    Returns:
        Dictionary of metric name to value.
    """
    # Reason: force_close_open_positions records equity at the last bar that
    # was already recorded by the simulation loop. Deduping keeps the LAST
    # entry so post-force-close commission drag is preserved, and prevents
    # the duplicate from inflating bars_per_year.
    equity_curve = equity_curve[~equity_curve.index.duplicated(keep="last")].sort_index()

    # Reason: validate equity FIRST — a non-positive curve makes CAGR's
    # negative-base power raise RuntimeWarning and returns NaN, and makes
    # log-returns undefined in Sharpe. Fail loud up front.
    _validate_equity(equity_curve["equity"])

    # Reason: slice warmup bars from the front so the flat no-positions phase
    # doesn't depress Sharpe or distort annualized return. Guard against a
    # warmup that would leave fewer than 2 bars — in that case we fall back
    # to the full curve so metrics are still computable (the strategy just
    # won't be trusted downstream anyway).
    effective_curve = equity_curve
    if warmup > 0 and warmup < len(equity_curve) - 1:
        effective_curve = equity_curve.iloc[warmup:]

    # Reason: derive years from actual calendar span so intraday bars are not
    # counted as separate trading days.
    time_span = (effective_curve.index[-1] - effective_curve.index[0]).total_seconds()
    years = time_span / SECONDS_PER_YEAR
    bars_per_year = len(effective_curve) / max(years, EPSILON)

    metrics = {}

    metrics.update(_return_metrics(effective_curve, years))
    metrics.update(_risk_metrics(effective_curve, bars_per_year))
    metrics.update(_trade_metrics(trades))
    metrics.update(_benchmark_metrics(effective_curve, benchmark_prices, years))

    return metrics


def _validate_equity(equity: pd.Series) -> None:
    """Raise loudly when the equity curve is corrupted."""
    if (equity <= 0).any():
        first_bad = equity[equity <= 0].index[0]
        raise ValueError(
            f"Equity curve contains non-positive values at {first_bad} "
            f"(min={equity.min():.2f}). Portfolio tracker accounting is "
            f"corrupted — metrics are undefined. Investigate the tracker, "
            f"do not silence this check."
        )


def _return_metrics(equity_curve: pd.DataFrame, years: float) -> dict:
    """Compute return-based metrics from the equity curve.

    Args:
        equity_curve: DataFrame with 'equity' column, datetime-indexed.
        years: Calendar duration of the equity curve in years.
    """
    equity = equity_curve["equity"]
    initial = equity.iloc[0]
    final = equity.iloc[-1]

    total_return_pct = ((final - initial) / initial) * 100

    if len(equity) > 1:
        annualized_return_pct = ((final / initial) ** (1 / max(years, EPSILON)) - 1) * 100
    else:
        annualized_return_pct = 0.0

    return {
        "total_return_pct": round(total_return_pct, 2),
        "annualized_return_pct": round(annualized_return_pct, 2),
    }


def _risk_metrics(equity_curve: pd.DataFrame, bars_per_year: float) -> dict:
    """Compute risk metrics: max drawdown and Sharpe ratio.

    Args:
        equity_curve: DataFrame with 'equity' column, datetime-indexed.
        bars_per_year: Number of bars that correspond to one calendar year,
            derived from the actual datetime span of the data.
    """
    equity = equity_curve["equity"]

    cumulative_max = equity.cummax()
    drawdown = (equity - cumulative_max) / cumulative_max
    max_drawdown_pct = round(drawdown.min() * 100, 2)

    # Reason: log returns are numerically stable (no sign-flip pathology), and
    # their annualized Sharpe — (mean/std) * sqrt(bars_per_year) — is the
    # standard continuous-compounding formulation. The rf subtraction is a
    # no-op at the default RISK_FREE_RATE=0 but preserved so callers can
    # configure a non-zero rf via calculations.config if needed. AM ≥ GM
    # guarantees a positive Sharpe whenever CAGR > rf.
    log_returns = np.log(equity).diff().dropna()

    # Reason: floating-point noise from cumulative compounding makes a
    # constant-drift equity curve's log-return std ≈ 1e-16 instead of 0.
    # Dividing by that produces a 1e12-scale bogus Sharpe. Treat anything
    # below a reasonable floor as zero-variance (Sharpe=0.0) — this matches
    # the mathematical definition (no risk → Sharpe undefined).
    std = float(log_returns.std())
    if len(log_returns) > 1 and std > 1e-10:
        risk_free_per_bar = np.log(1.0 + RISK_FREE_RATE) / bars_per_year
        excess_returns = log_returns - risk_free_per_bar
        sharpe_ratio = round(
            (excess_returns.mean() / std) * np.sqrt(bars_per_year),
            2,
        )
    else:
        sharpe_ratio = 0.0

    return {
        "max_drawdown_pct": max_drawdown_pct,
        "sharpe_ratio": sharpe_ratio,
    }


def _trade_metrics(trades: pd.DataFrame) -> dict:
    """Compute trade-level metrics from the trade log."""
    total_trades = len(trades)

    if total_trades == 0:
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

    win_rate_pct = round((len(winners) / total_trades) * 100, 2)

    gross_profit = winners["pnl"].sum() if len(winners) > 0 else 0.0
    gross_loss = abs(losers["pnl"].sum()) if len(losers) > 0 else 0.0
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else float("inf")

    avg_trade_return_pct = round(trades["return_pct"].mean(), 2)
    avg_win_pct = round(winners["return_pct"].mean(), 2) if len(winners) > 0 else 0.0
    avg_loss_pct = round(losers["return_pct"].mean(), 2) if len(losers) > 0 else 0.0

    largest_win = round(trades["pnl"].max(), 2)
    largest_loss = round(trades["pnl"].min(), 2)

    long_trades = len(trades[trades["direction"] == "long"])
    short_trades = len(trades[trades["direction"] == "short"])

    return {
        "total_trades": total_trades,
        "win_rate_pct": win_rate_pct,
        "profit_factor": profit_factor,
        "avg_trade_return_pct": avg_trade_return_pct,
        "avg_win_pct": avg_win_pct,
        "avg_loss_pct": avg_loss_pct,
        "largest_win": largest_win,
        "largest_loss": largest_loss,
        "long_trades": long_trades,
        "short_trades": short_trades,
    }


def _benchmark_metrics(
    equity_curve: pd.DataFrame,
    benchmark_prices: pd.Series | None,
    years: float,
) -> dict:
    """Compute benchmark-relative metrics (Jensen's alpha vs SPY).

    Args:
        equity_curve: DataFrame with 'equity' column, datetime-indexed.
        benchmark_prices: Series of benchmark close prices, datetime-indexed.
            If None, alpha is reported as None.
        years: Calendar duration of the backtest in years — used to annualize
            both the portfolio and benchmark returns at the same horizon,
            independent of bar frequency.
    """
    if benchmark_prices is None or len(benchmark_prices) < 2 or years <= 0:
        return {"alpha_vs_spy": None}

    equity = equity_curve["equity"]

    if (equity <= 0).any() or (benchmark_prices <= 0).any():
        return {"alpha_vs_spy": None}

    # Reason: annualize via calendar years (not assumed 252 trading days) so
    # the math is correct for intraday, hourly, and daily backtests alike.
    rp = (equity.iloc[-1] / equity.iloc[0]) ** (1.0 / years) - 1.0
    rm = (benchmark_prices.iloc[-1] / benchmark_prices.iloc[0]) ** (1.0 / years) - 1.0

    # Reason: beta is frequency-invariant (cov/var of same-frequency returns),
    # so bar-level pct_change is fine for beta even on intraday data. Log
    # returns would also work but require equity > 0 (already guarded above).
    portfolio_returns = equity.pct_change().dropna()
    benchmark_returns = benchmark_prices.pct_change().dropna()

    beta = calc_beta(portfolio_returns, benchmark_returns)

    if beta is None:
        return {"alpha_vs_spy": None}

    expected_return = RISK_FREE_RATE + beta * (rm - RISK_FREE_RATE)
    alpha = rp - expected_return

    return {"alpha_vs_spy": round(alpha * 100, 2)}
