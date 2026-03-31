"""Vectorized backtest engine for a multi-ticker universe.

Two-phase approach for fast batch evaluation:
  Phase 1 — Fully vectorized per-ticker signal generation (the expensive part).
  Phase 2 — Sequential portfolio simulation across tickers (fast because
             signals are pre-computed; just reading arrays and doing cash math).

Gives 10-50x speedup over BacktestEngine for research and screening.
"""

import numpy as np
import pandas as pd

from copy import deepcopy

from prophitai_algo_trading.engines.trade_routing import (
    process_exits_and_entries,
    force_close_open_positions,
    compile_backtest_result,
)
from prophitai_algo_trading.engines.backtest.models import BacktestResult, SignalData, SimulationArrays
from prophitai_algo_trading.engines.utils import (
    resolve_positions,
    align_multi_ticker_data,
    validate_engine_data,
    resolve_warmup,
)
from prophitai_algo_trading.utils.math_utils import compute_rolling_volatilities_bulk
from prophitai_algo_trading.execution.portfolio_tracker import PortfolioTracker
from prophitai_algo_trading.execution.position_tracker import PositionTracker
from prophitai_algo_trading.execution.cost_model import CostModel
from prophitai_algo_trading.sizing import BasePositionSizer, PercentOfEquitySizer
from prophitai_algo_trading.strategies.base import BaseStrategy


class VectorizedBacktestEngine:
    """Fast vectorized backtest engine for a multi-ticker universe.

    Phase 1 computes all indicator signals per-ticker in bulk (vectorized).
    Phase 2 walks through the unified timeline applying max_positions gating,
    sizing, and execution through PortfolioTracker.

    Note: Only supports proportional transaction costs (ptc). Fixed transaction
    costs (ftc) cannot be modeled precisely in vectorized mode.

    Args:
        strategy: A BaseStrategy instance — deepcopied per ticker internally.
        initial_capital: Starting portfolio value.
        cost_model: Transaction cost model (must have ftc=0).
        sizer: Position sizing strategy (defaults to PercentOfEquitySizer).
        warmup_bars: Override for warmup bar count.
        max_positions: Maximum number of concurrent open positions.
    """

    def __init__(
        self,
        strategy: BaseStrategy,
        initial_capital: float = 100_000.0,
        cost_model: CostModel | None = None,
        sizer: BasePositionSizer | None = None,
        warmup_bars: int | None = None,
        max_positions: int = 10,
    ):
        self._strategy_template = strategy
        self.initial_capital = initial_capital
        self._cost_model = cost_model or CostModel()
        self._sizer = sizer or PercentOfEquitySizer(
            pct=1 / max_positions, cost_model=self._cost_model,
        )
        self._warmup_bars = warmup_bars
        self._max_positions = max_positions

    # ================================
    # --> Helper funcs
    # ================================

    def _validate(self, data: dict[str, pd.DataFrame]) -> None:
        """Validate input data and engine configuration.

        Args:
            data: Mapping of ticker → OHLCV DataFrame.

        Raises:
            ValueError: If any DataFrame fails validation or ftc > 0.
        """
        validate_engine_data(data)

        if self._cost_model.ftc != 0:
            raise ValueError(
                "VectorizedBacktestEngine does not support fixed transaction "
                "costs (ftc). Use BacktestEngine for ftc > 0."
            )

    def _generate_signals(
        self,
        data: dict[str, pd.DataFrame],
        warmup: int,
        verbose: bool,
    ) -> SignalData:
        """Phase 1: Compute per-ticker signals in bulk (vectorized).

        Deepcopies the strategy template per ticker, calculates indicators,
        generates signals, and resolves raw positions (+1/0/-1) mapped onto
        a common datetime index.

        Args:
            data: Mapping of ticker → OHLCV DataFrame.
            warmup: Number of warmup bars to skip.
            verbose: If True, print progress.

        Returns:
            SignalData with common_index, aligned DataFrames, and raw positions.

        Raises:
            ValueError: If no tickers have sufficient data.
        """
        tickers = list(data.keys())

        if verbose:
            print(f"[Phase 1] Computing signals for {len(tickers)} tickers (vectorized)...")

        strategies: dict[str, BaseStrategy] = {
            t: deepcopy(self._strategy_template) for t in tickers
        }

        strategy_frames: dict[str, pd.DataFrame] = {}
        raw_positions: dict[str, np.ndarray] = {}
        entry_scores: dict[str, np.ndarray] = {}
        entry_candidates: dict[str, np.ndarray] = {}
        common_index, aligned = align_multi_ticker_data(data)

        for ticker in tickers:
            ticker_df = aligned[ticker]
            real_data = ticker_df[ticker_df["_has_bar"]].drop(columns=["_has_bar"]).copy()

            if len(real_data) < warmup + 2:
                if verbose:
                    print(f"  Skipping {ticker}: insufficient data after warmup")
                continue

            real_data = strategies[ticker].calculate_indicators(real_data)
            strategy_frames[ticker] = real_data.copy()
            signals = strategies[ticker].generate_signals(real_data)
            scores = strategies[ticker].score_entries(real_data)

            real_le = signals["long_entry"].iloc[warmup:].fillna(False).values.astype(np.int8)
            real_lx = signals["long_exit"].iloc[warmup:].fillna(False).values.astype(np.int8)
            real_se = signals["short_entry"].iloc[warmup:].fillna(False).values.astype(np.int8)
            real_sx = signals["short_exit"].iloc[warmup:].fillna(False).values.astype(np.int8)

            real_pos = resolve_positions(real_le, real_lx, real_se, real_sx)
            real_scores = scores.iloc[warmup:].fillna(0.0).values.astype(np.float64)

            real_indices = real_data.index[warmup:]
            full_positions = np.zeros(len(common_index), dtype=np.int8)
            full_scores = np.zeros(len(common_index), dtype=np.float64)
            full_candidates = np.empty(len(common_index), dtype=object)
            full_candidates[:] = None

            mapped_indices = common_index.searchsorted(real_indices)

            full_positions[mapped_indices] = real_pos
            full_scores[mapped_indices] = real_scores

            real_candidates = np.empty(len(real_indices), dtype=object)
            real_candidates[:] = None
            warm_slice = real_data.iloc[warmup:]

            for idx in range(len(warm_slice)):
                target = int(real_pos[idx])
                if target == 0:
                    continue

                row_series = warm_slice.iloc[idx]

                real_candidates[idx] = strategies[ticker].build_trade_candidate(
                    symbol=ticker,
                    row=row_series,
                    target_position=target,
                    timestamp=real_indices[idx],
                    score=float(real_scores[idx]),
                )

            full_candidates[mapped_indices] = real_candidates

            raw_positions[ticker] = full_positions
            entry_scores[ticker] = full_scores
            entry_candidates[ticker] = full_candidates

        if not raw_positions:
            raise ValueError("No tickers had sufficient data for backtesting.")

        return SignalData(
            common_index,
            aligned,
            strategy_frames,
            raw_positions,
            entry_scores,
            entry_candidates,
        )

    def _build_simulation_arrays(self, signal_data: SignalData) -> SimulationArrays:
        """Pre-build numpy matrices for Phase 2 simulation.

        Extracts close prices, computes rolling volatilities, and stacks
        position arrays into 2D matrices for O(1) per-bar access.

        Args:
            signal_data: Phase 1 outputs.

        Returns:
            SimulationArrays with close, vol, and position matrices.
        """
        ticker_list = list(signal_data.raw_positions.keys())

        close_matrix = np.column_stack([
            signal_data.aligned[t]["close"].values for t in ticker_list
        ])

        vol_matrix = compute_rolling_volatilities_bulk(close_matrix)

        positions_matrix = np.column_stack([
            signal_data.raw_positions[t] for t in ticker_list
        ])

        score_matrix = np.column_stack([
            signal_data.entry_scores[t] for t in ticker_list
        ])

        candidate_matrix = np.column_stack([
            signal_data.entry_candidates[t] for t in ticker_list
        ])

        return SimulationArrays(
            close_matrix,
            vol_matrix,
            positions_matrix,
            score_matrix,
            candidate_matrix,
            ticker_list,
        )

    def _simulate_portfolio(
        self,
        signal_data: SignalData,
        arrays: SimulationArrays,
        verbose: bool,
    ) -> tuple[PortfolioTracker, dict[str, PositionTracker], dict[str, float]]:
        """Phase 2: Walk the unified timeline executing trades.

        Iterates each bar, updates prices, sizes positions, and routes
        trade instructions through PortfolioTracker.

        Args:
            common_index: Unified datetime index across all tickers.
            arrays: Pre-built simulation matrices.
            verbose: If True, print progress.

        Returns:
            Tuple of (PortfolioTracker, position_trackers dict, latest_prices dict).
        """
        common_index = signal_data.common_index
        n_tickers = len(arrays.ticker_list)
        n_bars = len(common_index)

        if verbose:
            print(f"[Phase 2] Simulating portfolio across {n_bars} bars...")

        portfolio_tracker = PortfolioTracker(
            initial_capital=self.initial_capital,
            sizer=self._sizer,
            cost_model=self._cost_model,
        )

        position_trackers: dict[str, PositionTracker] = {
            t: PositionTracker() for t in arrays.ticker_list
        }
        latest_prices: dict[str, float] = {}

        for i in range(n_bars):
            timestamp = common_index[i]

            # Reason: update latest prices from pre-extracted numpy array
            for j in range(n_tickers):
                close_val = arrays.close_matrix[i, j]
                if not np.isnan(close_val):
                    latest_prices[arrays.ticker_list[j]] = close_val

            # Reason: classify tickers into exits and entries for deterministic ordering.
            # Exits run first to free capital/slots; entries are ranked by signal score.
            exits: list[tuple[str, int, float]] = []
            entries = []

            for idx in range(n_tickers):
                target_pos = int(arrays.positions_matrix[i, idx])
                ticker = arrays.ticker_list[idx]
                if target_pos == position_trackers[ticker].position:
                    continue
                price = latest_prices.get(ticker)
                if price is None:
                    continue
                if target_pos == 0:
                    exits.append((ticker, target_pos, price))
                else:
                    candidate = arrays.candidate_matrix[i, idx]
                    if candidate is None:
                        continue
                    if candidate.volatility is None and not np.isnan(arrays.vol_matrix[i, idx]):
                        candidate.volatility = float(arrays.vol_matrix[i, idx])
                    entries.append(candidate)

            entries.sort(key=lambda candidate: candidate.score, reverse=True)

            # Reason: match event-driven/live sizing hooks so wrapped and
            # context-aware sizers see close history, indicator history, and
            # latest prices before entry sizing.
            if entries:
                close_history: dict[str, pd.Series] = {}
                strategy_history: dict[str, pd.DataFrame] = {}
                for ticker in arrays.ticker_list:
                    frame = signal_data.strategy_frames.get(ticker)
                    if frame is None or frame.empty:
                        continue

                    history = frame.loc[:timestamp]
                    if history.empty:
                        continue

                    close_history[ticker] = history["close"]
                    strategy_history[ticker] = history

                self._sizer.prepare_for_bar(
                    close_history,
                    latest_prices=latest_prices,
                    strategy_data=strategy_history,
                    timestamp=timestamp,
                )

            process_exits_and_entries(
                exits, entries, position_trackers, portfolio_tracker,
                self._sizer, self._max_positions, timestamp,
            )

            portfolio_tracker.record_equity(timestamp, latest_prices)

        return portfolio_tracker, position_trackers, latest_prices

    # ================================
    # --> Public API
    # ================================

    def run(
        self,
        data: dict[str, pd.DataFrame],
        warmup_bars: int | None = None,
        verbose: bool = False,
    ) -> BacktestResult:
        """Run the vectorized backtest over historical data for multiple tickers.

        Args:
            data: Mapping of ticker → OHLCV DataFrame with datetime index.
            warmup_bars: Override for warmup bar count.
            verbose: If True, print progress information.

        Returns:
            BacktestResult with metrics, equity curve, trades, and
            strategy_data=None (not applicable for multi-ticker).
        """
        self._validate(data)
        warmup = resolve_warmup(
            warmup_bars, self._warmup_bars,
            self._strategy_template.min_bars_required,
        )

        # Phase 1: Vectorized per-ticker signal generation
        signal_data = self._generate_signals(data, warmup, verbose)

        # Phase 2: Sequential portfolio simulation
        arrays = self._build_simulation_arrays(signal_data)

        portfolio_tracker, position_trackers, latest_prices = self._simulate_portfolio(
            signal_data, arrays, verbose,
        )

        force_close_open_positions(
            portfolio_tracker, position_trackers, latest_prices,
            signal_data.common_index[-1],
        )

        return compile_backtest_result(
            portfolio_tracker, len(signal_data.raw_positions), verbose,
        )
