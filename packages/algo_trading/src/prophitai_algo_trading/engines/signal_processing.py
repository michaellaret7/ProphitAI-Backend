"""Shared bar-processing pipeline for event-driven engines.

Extracts the signal generation → rule checking → exit/entry classification →
trade routing → equity recording pipeline shared by BacktestEngine and
LiveRunner into composable functions.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime

import pandas as pd

from prophitai_algo_trading.engines.trade_routing import process_exits_and_entries
from prophitai_algo_trading.engines.utils import REASON_TO_DIRECTION, resolve_signal
from prophitai_algo_trading.execution.models import Direction, TradeCandidate
from prophitai_algo_trading.execution.portfolio_tracker import PortfolioTracker
from prophitai_algo_trading.execution.position_tracker import PositionTracker
from prophitai_algo_trading.rules.engine import RuleEngine
from prophitai_algo_trading.sizing import BasePositionSizer
from prophitai_algo_trading.strategies.base import BaseStrategy

logger = logging.getLogger(__name__)


# ================================
# --> Helper funcs
# ================================


def generate_ticker_signal(
    strategy: BaseStrategy,
    symbol: str,
    df: pd.DataFrame,
    current_position: int,
    timestamp: datetime | pd.Timestamp,
) -> tuple[int, float, TradeCandidate | None] | None:
    """Generate a signal for a single ticker and resolve to a target position.

    Calls the strategy's signal generator, resolves the 4-way signal into a
    target position (1/0/-1), and builds a standardized trade candidate for
    entries when the target differs from the current position.

    Args:
        strategy: Strategy instance for this ticker.
        symbol: Ticker symbol for this row.
        df: Ticker's OHLCV + indicator DataFrame.
        current_position: Current position state (1, 0, or -1).
        timestamp: Current bar timestamp.

    Returns:
        (target_position, entry_score, trade_candidate) if a trade is needed.
        Exits return ``trade_candidate=None``.
    """
    signals = strategy.generate_signals(df)
    le = bool(signals["long_entry"].iloc[-1])
    lx = bool(signals["long_exit"].iloc[-1])
    se = bool(signals["short_entry"].iloc[-1])
    sx = bool(signals["short_exit"].iloc[-1])

    target = resolve_signal(le, lx, se, sx, current_position)

    if target == current_position:
        return None

    score = float(strategy.score_entries(df).iloc[-1]) if target != 0 else 0.0
    candidate = None
    if target != 0:
        candidate = strategy.build_trade_candidate(
            symbol=symbol,
            row=df.iloc[-1],
            target_position=target,
            timestamp=timestamp,
            score=score,
        )
    return target, score, candidate


def build_rule_trade_callback(
    rule_engine: RuleEngine,
    inner_callback: Callable[[str, dict], None] | None = None,
) -> Callable[[str, dict], None]:
    """Build an on_trade callback that notifies the rule engine of entries/exits.

    Wraps an optional inner callback (e.g. verbose logging) so both fire.

    Args:
        rule_engine: Active rule engine to notify.
        inner_callback: Optional additional callback to chain.

    Returns:
        Composite on_trade callback.
    """
    def on_trade(ticker: str, instr: dict) -> None:
        reason = instr["reason"]
        price = instr["price"]
        ts = instr["timestamp"]
        direction = REASON_TO_DIRECTION[reason]
        if reason in ("open_long", "open_short"):
            rule_engine.notify_entry(ticker, price, ts, direction)
        elif reason in ("close_long", "close_short"):
            rule_engine.notify_exit(ticker, price, ts, direction)
        if inner_callback is not None:
            inner_callback(ticker, instr)

    return on_trade


def classify_signals(
    bar_signals: dict[str, tuple[int, float, float, TradeCandidate | None]],
) -> tuple[list[tuple[str, int, float]], list[TradeCandidate]]:
    """Split a signal map into exits and score-sorted entries.

    Args:
        bar_signals: Mapping of ticker → (target, price, score, candidate).

    Returns:
        Tuple of (exits, trade candidates) where entries are sorted by score
        descending.
    """
    exits = [
        (t, target, price)
        for t, (target, price, _score, _candidate) in bar_signals.items()
        if target == 0
    ]
    entries = sorted(
        [
            candidate
            for _ticker, (target, _price, _score, candidate) in bar_signals.items()
            if target != 0 and candidate is not None
        ],
        key=lambda candidate: candidate.score,
        reverse=True,
    )
    return exits, entries


def process_bar_batch(
    tickers_with_data: list[tuple[str, pd.DataFrame]],
    strategies: dict[str, BaseStrategy],
    position_trackers: dict[str, PositionTracker],
    portfolio_tracker: PortfolioTracker,
    rule_engine: RuleEngine | None,
    sizer: BasePositionSizer,
    all_close_prices: dict[str, pd.Series],
    max_positions: int,
    timestamp: datetime | pd.Timestamp,
    latest_prices: dict[str, float],
    on_trade: Callable[[str, dict], None] | None = None,
    on_error: Callable[[str, dict, Exception], None] | None = None,
    swallow_signal_errors: bool = False,
) -> None:
    """Process a batch of tickers for a single timestamp.

    For each ticker: generates signals, applies rule checks, classifies into
    exits/entries, prepares the sizer, routes trades via process_exits_and_entries,
    and records portfolio equity.

    Args:
        tickers_with_data: List of (ticker, current_df) pairs to process.
        strategies: Per-ticker strategy instances.
        position_trackers: Per-ticker position state machines.
        portfolio_tracker: Shared portfolio tracker.
        rule_engine: Rule engine (may be None or inactive).
        sizer: Position sizer instance.
        all_close_prices: Ticker → close Series for sizer.prepare_for_bar().
        max_positions: Max concurrent open positions.
        timestamp: Current bar timestamp.
        latest_prices: Most recent prices for equity recording.
        on_trade: Optional trade callback (compose with build_rule_trade_callback).
        on_error: Optional error callback (None = exceptions propagate).
        swallow_signal_errors: If True, catch signal generation exceptions and
                               skip the ticker. If False, exceptions propagate.
    """
    has_rules = rule_engine is not None and rule_engine.active
    signal_map = {1: "LONG", -1: "SHORT", 0: "FLAT"}
    bar_signals: dict[str, tuple[int, float, float, TradeCandidate | None]] = {}
    portfolio_tracker.update_market_prices(latest_prices)

    for ticker, df in tickers_with_data:
        try:
            price = df["close"].iloc[-1]

            # Notify rules of new bar
            if has_rules:
                rule_engine.notify_bar(ticker, price, timestamp)

            # Check if rules force an exit on an open position
            if has_rules and position_trackers[ticker].position != 0:
                if rule_engine.check_forced_exit(
                    ticker, price, timestamp, df, portfolio_tracker,
                ):
                    bar_signals[ticker] = (0, price, 0.0, None)
                    continue

            # Generate signal and resolve target position
            result = generate_ticker_signal(
                strategies[ticker],
                ticker,
                df,
                position_trackers[ticker].position,
                timestamp,
            )
            if result is None:
                continue

            target, score, candidate = result
            logger.info(
                "[%s] %s  close=%.2f  signal=%s",
                timestamp, ticker, price, signal_map.get(target, target),
            )

            # Check if rules block an entry
            if has_rules and target != 0:
                if not rule_engine.check_entry(
                    ticker, price, timestamp, df, portfolio_tracker,
                    target=target, score=score,
                ):
                    continue

            bar_signals[ticker] = (target, price, score, candidate)

        except Exception:
            if swallow_signal_errors:
                logger.exception(
                    "Signal processing failed for %s — skipping", ticker,
                )
            else:
                raise

    exits, entries = classify_signals(bar_signals)

    # Reason: only refresh sizer state when entries exist (sizing only matters for new positions)
    if entries:
        sizer.prepare_for_bar(
            all_close_prices,
            latest_prices=latest_prices,
            strategy_data={ticker: df for ticker, df in tickers_with_data},
            timestamp=timestamp,
        )

    process_exits_and_entries(
        exits, entries, position_trackers, portfolio_tracker,
        sizer, max_positions, timestamp, on_trade=on_trade, on_error=on_error,
    )

    portfolio_tracker.record_equity(timestamp, latest_prices)
