"""Vectorized backtest engine.

Pure matrix math. One signal pass per ticker, then a portfolio simulation
built from ``numpy`` operations on aligned position/price matrices. Fast,
suitable for research sweeps. The event-driven engine is the one to use
when you need per-trade cost accounting, custom sizers, or risk rules.

Assumptions:
    - Signal at bar t fills at bar t+1's close (shift by 1).
    - Equal-weight across open positions, capped at ``max_positions``.
    - Ranking is by ``strategy.score(df)`` — ties broken by ticker order.
    - Transaction costs are applied as a proportional hit to turnover.

This engine is intentionally simpler than event-driven: no sizers, no risk
rules, no per-ticker cash accounting. It measures strategy edge, not a
portfolio's behavior under realistic constraints.
"""

from __future__ import annotations

from copy import deepcopy

import numpy as np
import pandas as pd

from prophitai_algo_trading.metrics import BacktestResult, calculate_metrics
from prophitai_algo_trading.strategy import BaseStrategy


class VectorizedBacktest:
    """Vectorized backtest over a universe of tickers.

    Args:
        strategy: Strategy template (deep-copied per ticker).
        initial_capital: Starting equity.
        max_positions: Max concurrent open positions.
        cost_pct: Proportional cost applied to turnover (0.001 = 10 bps per side).
    """

    def __init__(
        self,
        strategy: BaseStrategy,
        initial_capital: float = 100_000.0,
        max_positions: int = 10,
        cost_pct: float = 0.0,
    ):
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.max_positions = max_positions
        self.cost_pct = cost_pct

    def run(
        self,
        data: dict[str, pd.DataFrame],
        benchmark: pd.Series | None = None,
    ) -> BacktestResult:
        """Run the backtest.

        Args:
            data: ``{ticker: OHLCV DataFrame}`` — a DatetimeIndex per ticker.
            benchmark: Optional benchmark price series for beta + Jensen's alpha.
        """
        if not data:
            raise ValueError("data is empty — nothing to backtest.")

        positions, scores, prices = self._build_signal_matrices(data)
        weights = self._compute_weights(positions, scores)
        equity_curve, trades = self._simulate(weights, prices, positions)

        metrics = calculate_metrics(
            equity_curve, trades,
            benchmark=benchmark,
            warmup=self.strategy.min_bars,
        )

        return BacktestResult(
            equity_curve=equity_curve,
            trades=trades,
            metrics=metrics,
        )

    def _build_signal_matrices(
        self, data: dict[str, pd.DataFrame],
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Compute per-ticker signals, then align into (T × N) matrices."""
        positions_list: dict[str, pd.Series] = {}
        scores_list: dict[str, pd.Series] = {}
        prices_list: dict[str, pd.Series] = {}

        for ticker, df in data.items():
            strat = deepcopy(self.strategy)

            enriched = strat.compute_indicators(df.copy())
            signaled = strat.compute_signals(enriched)

            if "position" not in signaled.columns:
                raise ValueError(
                    f"{ticker}: strategy.compute_signals must produce a 'position' column.",
                )

            positions_list[ticker] = signaled["position"].astype(float)
            scores_list[ticker] = strat.score(signaled).astype(float)
            prices_list[ticker] = signaled["close"].astype(float)

        positions = pd.DataFrame(positions_list).sort_index().fillna(0.0)
        scores = pd.DataFrame(scores_list).reindex(positions.index).fillna(0.0)
        prices = pd.DataFrame(prices_list).reindex(positions.index).ffill()

        return positions, scores, prices

    def _compute_weights(
        self, positions: pd.DataFrame, scores: pd.DataFrame,
    ) -> pd.DataFrame:
        """Convert raw positions into a slot-based sticky weight matrix.

        Mirrors the event-driven engine's semantics:
            1. At each bar, existing held positions exit if their signal is 0
               or flip direction.
            2. Freed slots plus any always-free slots are filled by the top
               unheld candidates ranked by ``|position| * score``.
            3. Held positions that keep the same direction signal stay in
               their slot (no forced close to "make room" for a slightly
               higher-scoring newcomer).

        All active holdings share equal weight at ``1 / max_positions`` of
        gross exposure. Ties resolve by column order via stable argsort.
        """
        pos_arr = positions.to_numpy()
        score_arr = scores.to_numpy()
        abs_positions = np.abs(pos_arr)
        ranking_score = abs_positions * score_arr

        n_bars, n_tickers = pos_arr.shape
        slot_weight = 1.0 / self.max_positions

        weights = np.zeros((n_bars, n_tickers), dtype=np.float64)
        state = np.zeros(n_tickers, dtype=np.int64)

        for t in range(n_bars):
            signals = pos_arr[t].astype(np.int64)

            # Step 1: exit or flip held positions whose signal changed.
            for i in range(n_tickers):
                if state[i] == 0:
                    continue

                signal_i = signals[i]

                if signal_i == 0 or signal_i != state[i]:
                    state[i] = 0

            # Step 2: fill free slots with highest-ranked new candidates.
            open_positions = int(np.count_nonzero(state))
            free_slots = self.max_positions - open_positions

            if free_slots > 0:
                candidate_mask = (state == 0) & (abs_positions[t] > 0)
                candidate_indices = np.where(candidate_mask)[0]

                if candidate_indices.size > 0:
                    candidate_scores = ranking_score[t, candidate_indices]
                    order = np.argsort(-candidate_scores, kind="stable")
                    picked = candidate_indices[order[:free_slots]]
                    state[picked] = signals[picked]

            # Step 3: record this bar's weights from sticky state.
            weights[t, :] = state * slot_weight

        return pd.DataFrame(weights, index=positions.index, columns=positions.columns)

    def _simulate(
        self,
        weights: pd.DataFrame,
        prices: pd.DataFrame,
        raw_positions: pd.DataFrame,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Simulate portfolio equity from weights and prices. Returns (equity_curve, trades)."""
        # Reason: shift weights by 1 bar — decisions made at t fill at t+1's close.
        held_weights = weights.shift(1).fillna(0.0)

        bar_returns = prices.pct_change().fillna(0.0)
        gross_return = (held_weights * bar_returns).sum(axis=1)

        turnover = (held_weights - held_weights.shift(1).fillna(0.0)).abs().sum(axis=1)
        cost_drag = turnover * self.cost_pct

        net_return = gross_return - cost_drag

        equity = (1.0 + net_return).cumprod() * self.initial_capital

        equity_curve = pd.DataFrame({
            "equity": equity,
            "gross_return": gross_return,
            "net_return": net_return,
            "turnover": turnover,
        })

        trades = self._extract_trades(held_weights, prices, raw_positions)

        return equity_curve, trades

    def _extract_trades(
        self,
        held_weights: pd.DataFrame,
        prices: pd.DataFrame,
        raw_positions: pd.DataFrame,
    ) -> pd.DataFrame:
        """Extract round-trip trades by scanning held_weights for regime changes per ticker.

        A trade starts the first bar a non-zero weight appears and ends the first bar
        after that when the weight returns to 0 or flips sign.
        """
        rows = []

        for ticker in held_weights.columns:
            weight_series = held_weights[ticker]
            price_series = prices[ticker]

            in_trade = False
            direction = 0
            entry_price = 0.0
            entry_time: pd.Timestamp | None = None
            entry_weight = 0.0

            for ts, w in weight_series.items():
                sign = int(np.sign(w))

                if in_trade:
                    if sign != direction:
                        exit_price = float(price_series.loc[ts])
                        pnl_pct = (exit_price - entry_price) / entry_price * direction

                        rows.append({
                            "symbol": ticker,
                            "direction": "long" if direction == 1 else "short",
                            "entry_time": entry_time,
                            "exit_time": ts,
                            "entry_price": entry_price,
                            "exit_price": exit_price,
                            "shares": abs(entry_weight),
                            "pnl": pnl_pct * abs(entry_weight) * self.initial_capital,
                            "return_pct": pnl_pct * 100.0,
                        })

                        in_trade = False
                        direction = 0

                        if sign != 0:
                            in_trade = True
                            direction = sign
                            entry_price = float(price_series.loc[ts])
                            entry_time = ts  # type: ignore[assignment]
                            entry_weight = float(w)

                elif sign != 0:
                    in_trade = True
                    direction = sign
                    entry_price = float(price_series.loc[ts])
                    entry_time = ts  # type: ignore[assignment]
                    entry_weight = float(w)

            if in_trade:
                last_ts = weight_series.index[-1]
                last_price = float(price_series.iloc[-1])
                pnl_pct = (last_price - entry_price) / entry_price * direction

                rows.append({
                    "symbol": ticker,
                    "direction": "long" if direction == 1 else "short",
                    "entry_time": entry_time,
                    "exit_time": last_ts,
                    "entry_price": entry_price,
                    "exit_price": last_price,
                    "shares": abs(entry_weight),
                    "pnl": pnl_pct * abs(entry_weight) * self.initial_capital,
                    "return_pct": pnl_pct * 100.0,
                })

        if not rows:
            return pd.DataFrame(columns=[
                "symbol", "direction", "entry_time", "exit_time",
                "entry_price", "exit_price", "shares", "pnl", "return_pct",
            ])

        trades_df = pd.DataFrame(rows).sort_values("exit_time").reset_index(drop=True)

        _ = raw_positions  # reserved for future use (tracking regime flips)

        return trades_df
