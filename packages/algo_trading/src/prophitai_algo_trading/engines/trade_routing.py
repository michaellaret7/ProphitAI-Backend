"""Shared trade routing logic for all engine types.

Contains the exits-first + score-ranked entries routing loop,
force-close logic, and backtest result compilation used by
VectorizedBacktestEngine, BacktestEngine, and LiveRunner.
"""

from collections.abc import Callable
from datetime import datetime

import pandas as pd

from prophitai_algo_trading.engines.backtest.metrics import calculate_metrics
from prophitai_algo_trading.engines.backtest.models import BacktestResult
from prophitai_algo_trading.engines.utils import is_entry_instruction
from prophitai_algo_trading.execution.models import TradeCandidate
from prophitai_algo_trading.execution.portfolio_tracker import PortfolioTracker
from prophitai_algo_trading.execution.position_tracker import PositionTracker
from prophitai_algo_trading.sizing import BasePositionSizer


# ================================
# --> Helper funcs
# ================================

def _execute_instruction(
    portfolio_tracker: PortfolioTracker,
    instr: dict,
    ticker: str,
    on_trade: Callable[[str, dict], None] | None,
    on_error: Callable[[str, dict, Exception], None] | None,
) -> bool:
    """Execute a single instruction with optional callbacks.

    Args:
        portfolio_tracker: Shared portfolio tracker.
        instr: Trade instruction dict from PositionTracker.
        ticker: Symbol being traded.
        on_trade: Called after successful execution with (ticker, instr).
        on_error: Called on exception with (ticker, instr, exc).
                  If None, exceptions propagate.

    Returns:
        True if the instruction executed successfully, False if caught by on_error.
    """
    if on_error is not None:
        try:
            portfolio_tracker.execute_instruction(instr, ticker)
        except Exception as exc:
            on_error(ticker, instr, exc)
            return False
    else:
        portfolio_tracker.execute_instruction(instr, ticker)

    if on_trade is not None:
        on_trade(ticker, instr)

    return True


def process_exits_and_entries(
    exits: list[tuple[str, int, float]],
    entries: list[TradeCandidate],
    position_trackers: dict[str, PositionTracker],
    portfolio_tracker: PortfolioTracker,
    sizer: BasePositionSizer,
    max_positions: int,
    timestamp: datetime | pd.Timestamp,
    on_trade: Callable[[str, dict], None] | None = None,
    on_error: Callable[[str, dict, Exception], None] | None = None,
) -> None:
    """Route trade instructions with exits-first + score-ranked entry ordering.

    Exits are processed first to free capital and position slots. Entries are
    then processed in order (caller must pre-sort by score descending), gated
    by max_positions.

    Args:
        exits: List of (ticker, target_position, price) for positions closing to flat.
        entries: Standardized trade candidates, pre-sorted by score descending.
        position_trackers: Per-ticker position state machines.
        portfolio_tracker: Shared portfolio tracker.
        sizer: Position sizer used to convert candidates into target shares.
        max_positions: Maximum number of concurrent open positions.
        timestamp: Bar timestamp for the trade log.
        on_trade: Optional callback fired after each successful execution.
        on_error: Optional callback fired on execution errors. If None,
                  exceptions propagate (backtest behavior).
    """
    # Process exits first — free capital and position slots
    for ticker, target, price in exits:
        instructions = position_trackers[ticker].plan_transition(target, price, timestamp)
        for instr in instructions:
            success = _execute_instruction(
                portfolio_tracker, instr, ticker, on_trade, on_error,
            )
            if success:
                position_trackers[ticker].apply_instruction(instr)

    # Process entries ranked by signal strength — strongest conviction fills first
    for candidate in entries:
        ticker = candidate.symbol
        instructions = position_trackers[ticker].plan_transition(
            candidate.target_position,
            candidate.price,
            candidate.timestamp,
        )
        for instr in instructions:
            if is_entry_instruction(instr):
                if portfolio_tracker.open_position_count >= max_positions:
                    continue

                context = portfolio_tracker.build_portfolio_context(
                    prices={ticker: candidate.price},
                    timestamp=candidate.timestamp,
                )
                decision = sizer.size_trade(candidate, context)
                if decision.shares <= 0:
                    continue
                instr["target_shares"] = decision.shares
                instr["trade_candidate"] = candidate
                instr["sizing_decision"] = decision

            success = _execute_instruction(
                portfolio_tracker, instr, ticker, on_trade, on_error,
            )
            if success:
                position_trackers[ticker].apply_instruction(instr)


def force_close_open_positions(
    portfolio_tracker: PortfolioTracker,
    position_trackers: dict[str, PositionTracker],
    latest_prices: dict[str, float],
    last_timestamp: datetime | pd.Timestamp,
    verbose: bool = False,
) -> None:
    """Close all remaining open positions at the last bar.

    Args:
        portfolio_tracker: Portfolio state tracker.
        position_trackers: Per-ticker position state machines.
        latest_prices: Most recent price per ticker.
        last_timestamp: Timestamp of the final bar.
        verbose: If True, print progress information.
    """
    if not portfolio_tracker.has_open_positions:
        if verbose:
            print("[3/3] No open positions to force-close.")
        return

    if verbose:
        print(f"[3/3] Force-closing {portfolio_tracker.open_position_count} "
              f"open position(s)...")

    for ticker in portfolio_tracker.open_symbols:
        price = latest_prices.get(ticker, 0.0)
        instructions = position_trackers[ticker].plan_transition(0, price, last_timestamp)
        for instr in instructions:
            portfolio_tracker.execute_instruction(instr, ticker)
            position_trackers[ticker].apply_instruction(instr)

    portfolio_tracker.record_equity(last_timestamp, latest_prices)


def compile_backtest_result(
    portfolio_tracker: PortfolioTracker,
    ticker_count: int,
    verbose: bool = False,
) -> BacktestResult:
    """Package portfolio tracker outputs into a BacktestResult.

    Args:
        portfolio_tracker: Completed portfolio tracker.
        ticker_count: Number of tickers in the universe (for verbose logging).
        verbose: If True, print summary.

    Returns:
        BacktestResult with metrics, equity curve, and trades.
    """
    equity_curve = portfolio_tracker.get_equity_curve()
    trades = portfolio_tracker.get_trades_df()
    metrics = calculate_metrics(equity_curve, trades)

    if verbose:
        print(f"\nDone: {len(trades)} trades across {ticker_count} tickers, "
              f"final equity=${equity_curve['equity'].iloc[-1]:,.2f}")

    return BacktestResult(
        metrics=metrics,
        equity_curve=equity_curve,
        trades=trades,
        strategy_data=None,
    )
