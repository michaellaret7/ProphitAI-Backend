"""Result grader — prints metrics and sanity-checks the backtest.

Looks loose on purpose. This is a structural smoke test ("did the
strategy run?"), not a P&L validator. Hard assertions are only:

    1. equity curve non-empty
    2. all equity points positive (no negative equity)
    3. at least one trade fired
    4. total return within a plausible band (pipeline-break check)
"""

from __future__ import annotations

import pandas as pd


def grade(result) -> None:
    equity_curve: pd.DataFrame = result.equity_curve
    trades: pd.DataFrame = result.trades
    metrics: dict = result.metrics

    print(f"\n  equity bars:    {len(equity_curve)}")
    print(f"  trades closed:  {len(trades)}")

    assert not equity_curve.empty, "equity curve is empty"
    assert (equity_curve["equity"] > 0).all(), "negative equity detected"
    assert len(trades) > 0, "no trades fired — strategy produced no signals"

    _print_metrics(metrics)
    _print_pnl(equity_curve)
    _print_breakdown(trades)


#     ================================
# --> Helper printers
#     ================================

def _print_metrics(metrics: dict) -> None:
    print(f"\n  METRICS:")

    for key in [
        "total_return_pct", "annualized_return_pct",
        "max_drawdown_pct", "sharpe_ratio",
        "total_trades", "win_rate_pct", "profit_factor",
        "avg_win_pct", "avg_loss_pct",
    ]:
        val = metrics.get(key)

        if val is not None:
            print(f"    {key}: {val}")


def _print_pnl(equity_curve: pd.DataFrame) -> None:
    start_eq = float(equity_curve["equity"].iloc[0])
    end_eq = float(equity_curve["equity"].iloc[-1])
    pnl_pct = (end_eq / start_eq - 1.0) * 100.0

    print(f"\n  equity: ${start_eq:,.0f} -> ${end_eq:,.0f}  ({pnl_pct:+.2f}%)")

    # Reason: pipeline-break guard — not a P&L assertion. A real bug
    # usually produces absurd results (-80%, +500%).
    assert -50.0 < pnl_pct < 300.0, \
        f"Total return {pnl_pct:+.2f}% suggests pipeline failure"


def _print_breakdown(trades: pd.DataFrame) -> None:
    if trades.empty:
        return

    long_trades = (trades["direction"] == "long").sum()
    short_trades = (trades["direction"] == "short").sum()
    print(f"  trade breakdown: {long_trades}L / {short_trades}S")

    top10 = trades["symbol"].value_counts().head(10)

    if not top10.empty:
        print(f"\n  top 10 most-traded symbols:")
        for sym, count in top10.items():
            print(f"    {sym}: {count}")
