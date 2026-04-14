"""Helper functions for VectorizedBacktestEngine."""

from __future__ import annotations

from copy import deepcopy

import numpy as np
import pandas as pd

from prophitai_algo_trading.engines.backtest.models import SignalData, SimulationArrays
from prophitai_algo_trading.engines.signal_resolution import resolve_positions
from prophitai_algo_trading.engines.trade_routing import process_exits_and_entries
from prophitai_algo_trading.execution.cost_model import CostModel
from prophitai_algo_trading.execution.portfolio_tracker import PortfolioTracker
from prophitai_algo_trading.execution.position_tracker import PositionTracker
from prophitai_algo_trading.strategies.base import BaseStrategy
from prophitai_algo_trading.utils.math_utils import compute_rolling_volatilities_bulk


def validate_vectorized_data(
    data: dict[str, pd.DataFrame],
    cost_model: CostModel,
    validate_engine_data,
) -> None:
    """Validate input data and vectorized-engine constraints."""
    validate_engine_data(data)
    if cost_model.ftc != 0:
        raise ValueError(
            "VectorizedBacktestEngine does not support fixed transaction costs (ftc). "
            "Use EventDrivenBacktestEngine for ftc > 0."
        )


def build_full_candidate_arrays(
    strategy: BaseStrategy,
    ticker: str,
    real_data: pd.DataFrame,
    warmup: int,
    common_index: pd.DatetimeIndex,
    real_pos: np.ndarray,
    real_scores: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build full-length position, score, and candidate arrays for one ticker."""

    real_indices = real_data.index[warmup:]
    mapped_indices = common_index.searchsorted(real_indices)

    full_positions = np.zeros(len(common_index), dtype=np.int8)
    full_scores = np.zeros(len(common_index), dtype=np.float64)
    full_candidates = np.empty(len(common_index), dtype=object)
    full_candidates[:] = None
    full_positions[mapped_indices] = real_pos
    full_scores[mapped_indices] = real_scores

    warm_slice = real_data.iloc[warmup:]

    real_candidates = np.empty(len(real_indices), dtype=object)
    real_candidates[:] = None

    signal_indices = np.nonzero(real_pos)[0]

    for idx in signal_indices:
        real_candidates[idx] = strategy.build_entry_candidate(
            symbol=ticker,
            row=warm_slice.iloc[idx],
            target_position=int(real_pos[idx]),
            timestamp=real_indices[idx],
            score=float(real_scores[idx]),
        )

    full_candidates[mapped_indices] = real_candidates

    return full_positions, full_scores, full_candidates


def generate_vectorized_signals(
    strategy_template: BaseStrategy,
    data: dict[str, pd.DataFrame],
    warmup: int,
    verbose: bool,
    align_multi_ticker_data,
) -> SignalData:
    """Compute per-ticker signals in bulk."""

    tickers = list(data.keys())

    if verbose:
        print(f"[Phase 1] Computing signals for {len(tickers)} tickers (vectorized)...")

    strategies = {ticker: deepcopy(strategy_template) for ticker in tickers}
    strategy_frames: dict[str, pd.DataFrame] = {}

    raw_positions: dict[str, np.ndarray] = {}
    entry_scores: dict[str, np.ndarray] = {}

    entry_candidates: dict[str, np.ndarray] = {}
    common_index, aligned = align_multi_ticker_data(data)

    for ticker in tickers:
        real_data = aligned[ticker][aligned[ticker]["_has_bar"]].drop(columns=["_has_bar"]).copy()

        if len(real_data) < warmup + 2:
            if verbose:
                print(f"  Skipping {ticker}: insufficient data after warmup")

            continue

        strategy_frames[ticker] = strategies[ticker].calculate_indicators(real_data).copy()
        signals = strategies[ticker].generate_signals(strategy_frames[ticker])

        scores = strategies[ticker].score_entries(strategy_frames[ticker])

        real_pos = resolve_positions(
            signals["long_entry"].iloc[warmup:].fillna(False).values.astype(np.int8),
            signals["long_exit"].iloc[warmup:].fillna(False).values.astype(np.int8),
            signals["short_entry"].iloc[warmup:].fillna(False).values.astype(np.int8),
            signals["short_exit"].iloc[warmup:].fillna(False).values.astype(np.int8),
        )

        real_scores = scores.iloc[warmup:].fillna(0.0).values.astype(np.float64)

        arrays = build_full_candidate_arrays(
            strategies[ticker], ticker, strategy_frames[ticker], warmup, common_index, real_pos, real_scores,
        )

        raw_positions[ticker], entry_scores[ticker], entry_candidates[ticker] = arrays

    if not raw_positions:
        raise ValueError("No tickers had sufficient data for backtesting.")

    return SignalData(common_index, aligned, strategy_frames, raw_positions, entry_scores, entry_candidates)


def build_simulation_arrays(signal_data: SignalData) -> SimulationArrays:
    """Pre-build numpy matrices for portfolio simulation."""
    ticker_list = list(signal_data.raw_positions.keys())

    close_matrix = np.column_stack([signal_data.aligned[ticker]["close"].values for ticker in ticker_list])

    # Reason: forward-fill closes so the simulation loop can read latest prices
    # directly from a row instead of maintaining an incremental dict per bar
    ffilled_close_matrix = pd.DataFrame(close_matrix).ffill().values

    vol_matrix = compute_rolling_volatilities_bulk(close_matrix)
    positions_matrix = np.column_stack([signal_data.raw_positions[ticker] for ticker in ticker_list])
    score_matrix = np.column_stack([signal_data.entry_scores[ticker] for ticker in ticker_list])
    candidate_matrix = np.column_stack([signal_data.entry_candidates[ticker] for ticker in ticker_list])

    return SimulationArrays(
        close_matrix, ffilled_close_matrix, vol_matrix,
        positions_matrix, score_matrix, candidate_matrix, ticker_list,
    )


def prepare_sizer_history(
    signal_data: SignalData,
    ticker_list: list[str],
    timestamp,
    window: int = 40,
):
    """Prepare close and strategy history for context-aware sizers.

    Uses binary search (searchsorted) and a fixed-size window instead of
    expanding .loc[:timestamp] slices to avoid O(n²) degradation.
    """
    close_history: dict[str, pd.Series] = {}
    strategy_history: dict[str, pd.DataFrame] = {}

    for ticker in ticker_list:
        frame = signal_data.strategy_frames.get(ticker)

        if frame is None or frame.empty:
            continue

        # Reason: searchsorted is O(log n) vs .loc[:timestamp] which is O(n)
        idx = frame.index.searchsorted(timestamp, side="right")

        if idx == 0:
            continue

        start = max(0, idx - window)
        sliced = frame.iloc[start:idx]

        close_history[ticker] = sliced["close"]
        strategy_history[ticker] = sliced

    return close_history, strategy_history


def classify_vectorized_orders(
    arrays: SimulationArrays,
    position_trackers: dict[str, PositionTracker],
    latest_prices: dict[str, float],
    bar_index: int,
) -> tuple[list[tuple[str, int, float]], list]:
    """Split one bar into exits and score-ranked entries."""
    exits: list[tuple[str, int, float]] = []

    entries = []

    for idx, ticker in enumerate(arrays.ticker_list):
        target_pos = int(arrays.positions_matrix[bar_index, idx])

        if target_pos == position_trackers[ticker].position:
            continue

        price = latest_prices.get(ticker)

        if price is None:
            continue

        if target_pos == 0:
            exits.append((ticker, target_pos, price))
            continue

        candidate = arrays.candidate_matrix[bar_index, idx]
        
        if candidate is None:
            continue

        if candidate.volatility is None and not np.isnan(arrays.vol_matrix[bar_index, idx]):
            candidate.volatility = float(arrays.vol_matrix[bar_index, idx])

        entries.append(candidate)

    entries.sort(key=lambda candidate: candidate.score, reverse=True)

    return exits, entries


def simulate_vectorized_portfolio(
    signal_data: SignalData,
    arrays: SimulationArrays,
    initial_capital: float,
    sizer,
    cost_model: CostModel,
    max_positions: int,
    verbose: bool,
) -> tuple[PortfolioTracker, dict[str, PositionTracker], dict[str, float]]:
    """Walk the unified timeline executing trades."""

    common_index = signal_data.common_index
    n_tickers = len(arrays.ticker_list)

    if verbose:
        print(f"[Phase 2] Simulating portfolio across {len(common_index)} bars...")

    portfolio_tracker = PortfolioTracker(initial_capital=initial_capital, sizer=sizer, cost_model=cost_model)
    position_trackers = {ticker: PositionTracker() for ticker in arrays.ticker_list}

    for i, timestamp in enumerate(common_index):
        # Reason: forward-filled matrix lets us build latest_prices from a single
        # row instead of maintaining an incremental dict across bars
        row = arrays.ffilled_close_matrix[i]
        latest_prices = {
            arrays.ticker_list[j]: row[j]
            for j in range(n_tickers)
            if not np.isnan(row[j])
        }

        exits, entries = classify_vectorized_orders(arrays, position_trackers, latest_prices, i)

        if entries:
            close_history, strategy_history = prepare_sizer_history(
                signal_data, arrays.ticker_list, timestamp,
            )

            sizer.prepare_for_bar(
                close_history, latest_prices=latest_prices, strategy_data=strategy_history, timestamp=timestamp,
            )

        process_exits_and_entries(
            exits, entries, position_trackers, portfolio_tracker, sizer, max_positions, timestamp,
        )

        portfolio_tracker.record_equity(timestamp, latest_prices)
        
    return portfolio_tracker, position_trackers, latest_prices
