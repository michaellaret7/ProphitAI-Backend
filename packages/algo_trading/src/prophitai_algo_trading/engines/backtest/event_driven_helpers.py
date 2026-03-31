"""Helper functions for EventDrivenBacktestEngine."""

from __future__ import annotations

from copy import deepcopy

import pandas as pd

from prophitai_algo_trading.engines.signal_processing import (
    build_risk_trade_callback,
    process_bar_batch,
)
from prophitai_algo_trading.execution import CostModel, PortfolioTracker, PositionTracker
from prophitai_algo_trading.risk.engine import RiskEngine
from prophitai_algo_trading.strategies.base import BaseStrategy


def init_event_trackers(
    strategy_template: BaseStrategy,
    tickers: list[str],
    initial_capital: float,
    sizer,
    cost_model: CostModel,
) -> tuple[dict[str, BaseStrategy], dict[str, PositionTracker], PortfolioTracker]:
    """Create per-ticker strategies, position trackers, and shared portfolio tracker."""
    strategies = {ticker: deepcopy(strategy_template) for ticker in tickers}
    position_trackers = {ticker: PositionTracker() for ticker in tickers}
    portfolio_tracker = PortfolioTracker(
        initial_capital=initial_capital,
        sizer=sizer,
        cost_model=cost_model,
    )
    return strategies, position_trackers, portfolio_tracker


def warmup_event_indicators(
    tickers: list[str],
    aligned: dict[str, pd.DataFrame],
    strategies: dict[str, BaseStrategy],
    warmup: int,
    verbose: bool,
) -> tuple[dict[str, pd.DataFrame], dict[str, float]]:
    """Batch calculate indicators on warmup bars for each ticker."""
    if verbose:
        print(f"[1/3] Warmup: calculating indicators on {warmup} bars for {len(tickers)} tickers...")
    ticker_dfs: dict[str, pd.DataFrame] = {}
    latest_prices: dict[str, float] = {}
    for ticker in tickers:
        warmup_real = aligned[ticker].iloc[:warmup].copy()
        warmup_real = warmup_real[warmup_real["_has_bar"]].drop(columns=["_has_bar"])
        if warmup_real.empty:
            continue
        ticker_dfs[ticker] = strategies[ticker].calculate_indicators(warmup_real)
        if not ticker_dfs[ticker].empty:
            latest_prices[ticker] = ticker_dfs[ticker]["close"].iloc[-1]
    return ticker_dfs, latest_prices


def update_event_bar_state(
    timestamp,
    tickers: list[str],
    aligned: dict[str, pd.DataFrame],
    ticker_dfs: dict[str, pd.DataFrame],
    strategies: dict[str, BaseStrategy],
    latest_prices: dict[str, float],
    row_index: int,
) -> list[tuple[str, pd.DataFrame]]:
    """Ingest the current aligned row for each ticker."""
    tickers_with_data: list[tuple[str, pd.DataFrame]] = []
    for ticker in tickers:
        row = aligned[ticker].iloc[row_index]
        if pd.notna(row["close"]):
            latest_prices[ticker] = row["close"]
        if not row["_has_bar"]:
            continue
        ticker_dfs.setdefault(ticker, pd.DataFrame())
        bar = row.drop("_has_bar").to_frame().T
        bar.index = [timestamp]
        ticker_dfs[ticker] = pd.concat([ticker_dfs[ticker], bar])
        ticker_dfs[ticker] = strategies[ticker].update_indicators(ticker_dfs[ticker])
        tickers_with_data.append((ticker, ticker_dfs[ticker]))
    return tickers_with_data


def build_event_trade_callback(
    verbose: bool,
    risk_engine: RiskEngine | None,
    portfolio_tracker: PortfolioTracker,
    latest_prices: dict[str, float],
    timestamp,
):
    """Build the optional verbose/risk callback for one timestamp."""
    on_trade = None
    if verbose:
        def on_trade(ticker: str, instr: dict) -> None:
            equity = portfolio_tracker.get_total_equity(latest_prices)
            print(
                f"  [{timestamp}]  {ticker}  ${instr['price']:.2f}  "
                f"{instr['reason'].upper()}  equity=${equity:,.2f}"
            )
    if risk_engine is not None and risk_engine.active:
        on_trade = build_risk_trade_callback(risk_engine, inner_callback=on_trade)
    return on_trade


def simulate_event_bars(
    common_index: pd.DatetimeIndex,
    aligned: dict[str, pd.DataFrame],
    tickers: list[str],
    strategies: dict[str, BaseStrategy],
    position_trackers: dict[str, PositionTracker],
    portfolio_tracker: PortfolioTracker,
    ticker_dfs: dict[str, pd.DataFrame],
    latest_prices: dict[str, float],
    warmup: int,
    verbose: bool,
    risk_engine: RiskEngine | None,
    sizer,
    max_positions: int,
) -> None:
    """Process bars one at a time with exits-first ordering."""
    if verbose:
        print(f"[2/3] Trading: processing {len(common_index) - warmup} bars across {len(tickers)} tickers...")
    for i in range(warmup, len(common_index)):
        timestamp = common_index[i]
        tickers_with_data = update_event_bar_state(
            timestamp, tickers, aligned, ticker_dfs, strategies, latest_prices, i,
        )
        on_trade = build_event_trade_callback(
            verbose, risk_engine, portfolio_tracker, latest_prices, timestamp,
        )
        process_bar_batch(
            tickers_with_data=tickers_with_data,
            strategies=strategies,
            position_trackers=position_trackers,
            portfolio_tracker=portfolio_tracker,
            risk_engine=risk_engine,
            sizer=sizer,
            all_close_prices={ticker: ticker_dfs[ticker]["close"] for ticker in ticker_dfs},
            max_positions=max_positions,
            timestamp=timestamp,
            latest_prices=latest_prices,
            on_trade=on_trade,
            swallow_signal_errors=False,
        )


def plot_event_backtest_results(result) -> None:
    """Plot equity curve and trade P&L from a backtest result."""
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    fig, (ax_equity, ax_pnl) = plt.subplots(
        2, 1, figsize=(14, 8), gridspec_kw={"height_ratios": [3, 1]}, sharex=True,
    )
    equity = result.equity_curve[~result.equity_curve.index.duplicated(keep="last")]
    ax_equity.plot(equity.index, equity["equity"], color="steelblue", linewidth=1.2)
    ax_equity.set_title("Universe Backtest â€” Equity Curve", fontsize=13)
    ax_equity.set_ylabel("Portfolio Value ($)")
    ax_equity.grid(True, alpha=0.3)
    if not result.trades.empty:
        colors = ["green" if pnl > 0 else "red" for pnl in result.trades["pnl"]]
        ax_pnl.bar(result.trades["exit_date"], result.trades["pnl"], color=colors, width=2, alpha=0.8)
        ax_pnl.axhline(0, color="black", linewidth=0.5)
    ax_pnl.set_title("Trade P&L", fontsize=13)
    ax_pnl.set_ylabel("P&L ($)")
    ax_pnl.set_xlabel("Date")
    ax_pnl.grid(True, alpha=0.3)
    ax_pnl.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    fig.autofmt_xdate(rotation=30)
    fig.tight_layout()
    plt.show()
