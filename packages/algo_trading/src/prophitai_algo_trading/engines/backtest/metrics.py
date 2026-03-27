"""Pure functions for computing backtest performance metrics.

Takes equity curve and trades DataFrames produced by SimulatedPortfolio
and returns a dictionary of all computed metrics.
"""

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252
RISK_FREE_RATE = 0.04
SECONDS_PER_YEAR = 365.25 * 86_400
EPSILON = 1e-9

def calculate_metrics(equity_curve: pd.DataFrame, trades: pd.DataFrame) -> dict:
    """Calculate all performance metrics from backtest results.

    Args:
        equity_curve: DataFrame with 'equity' column, datetime-indexed.
        trades: DataFrame with one row per round-trip trade, must have
            'pnl', 'return_pct', and 'direction' columns.

    Returns:
        Dictionary of metric name to value.
    """
    # Reason: derive years from actual calendar span so intraday bars are not
    # counted as separate trading days.
    time_span = (equity_curve.index[-1] - equity_curve.index[0]).total_seconds()
    years = time_span / SECONDS_PER_YEAR
    bars_per_year = len(equity_curve) / max(years, EPSILON)

    metrics = {}

    metrics.update(_return_metrics(equity_curve, years))
    metrics.update(_risk_metrics(equity_curve, bars_per_year))
    metrics.update(_trade_metrics(trades))

    return metrics


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

    # Max drawdown
    cumulative_max = equity.cummax()
    drawdown = (equity - cumulative_max) / cumulative_max
    max_drawdown_pct = round(drawdown.min() * 100, 2)

    # Sharpe ratio (annualized)
    bar_returns = equity.pct_change().dropna()
    if len(bar_returns) > 1 and bar_returns.std() > 0:
        risk_free_per_bar = RISK_FREE_RATE / bars_per_year
        excess_returns = bar_returns - risk_free_per_bar
        sharpe_ratio = round(
            (excess_returns.mean() / excess_returns.std()) * np.sqrt(bars_per_year),
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
