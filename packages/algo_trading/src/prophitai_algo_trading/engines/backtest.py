"""Event-driven backtest engine — thin wrapper around ``BarRunner``.

Owns the bar-acquisition concern: sorting + union-ing every ticker's
DatetimeIndex, slicing each ticker's history up to the current bar,
building ``AlgorithmContext``, and recording per-bar equity. The actual
pipeline (alphas → PCM → risk → execution → lifecycle) lives in
``BarRunner.step``.

After the final bar, ``BarRunner.force_flatten`` closes any remaining
positions through the normal execution + lifecycle path so realized
P&L appears in the trade log and the final equity point reflects the
fully-closed book.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from prophitai_algo_trading.portfolio.cost_model import CostModel
from prophitai_algo_trading.engines.runner import BarRunner
from prophitai_algo_trading.core.models import AlgorithmContext
from prophitai_algo_trading.analytics.metrics import BacktestResult, calculate_metrics
from prophitai_algo_trading.portfolio.portfolio import Portfolio

if TYPE_CHECKING:
    from datetime import datetime

    from prophitai_algo_trading.algorithm.event import Algorithm


#     ================================
# --> Helper funcs
#     ================================

def _union_index(data: dict[str, pd.DataFrame]) -> pd.DatetimeIndex:
    """Sorted union of every ticker's datetime index."""
    all_ts: set = set()

    for df in data.values():
        all_ts.update(df.index)

    return pd.DatetimeIndex(sorted(all_ts))


def _bar_slice(
    data: dict[str, pd.DataFrame], timestamp: "datetime",
) -> dict[str, pd.DataFrame]:
    """For every ticker with a bar at or before ``timestamp``, return the
    slice up to and including that bar."""
    out: dict[str, pd.DataFrame] = {}

    for ticker, df in data.items():
        if timestamp not in df.index:
            continue

        idx_pos = df.index.get_loc(timestamp)
        out[ticker] = df.iloc[: idx_pos + 1]

    return out


#     ================================
# --> Backtest
#     ================================

class Backtest:
    """Bar-by-bar backtest driving an ``Algorithm``'s pipeline.

    Args:
        algorithm: Fully-configured ``Algorithm`` — typically wired with
            ``ExecutionModel(sink=PortfolioSink())`` for backtest.
        initial_capital: Starting equity.
        cost_model: Transaction cost model attached to the Portfolio.
            Defaults to zero-cost ``CostModel()``.
    """

    def __init__(
        self,
        algorithm: "Algorithm",
        initial_capital: float = 100_000.0,
        cost_model: CostModel | None = None,
    ):
        self.algorithm = algorithm
        self.initial_capital = initial_capital
        self.cost_model = cost_model or CostModel()
        self._runner = BarRunner(algorithm)

    def run(
        self,
        data: dict[str, pd.DataFrame],
        benchmark: pd.Series | None = None,
    ) -> BacktestResult:
        """Run the backtest.

        Args:
            data: ``{ticker: OHLCV DataFrame}`` — each DatetimeIndex'd.
            benchmark: Optional benchmark price series for beta + alpha.
        """
        if not data:
            raise ValueError("data is empty — nothing to backtest.")

        portfolio = Portfolio(self.initial_capital, self.cost_model)

        common_index = _union_index(data)
        max_lookback = self.algorithm.max_lookback

        last_ctx: AlgorithmContext | None = None

        for bar_idx, timestamp in enumerate(common_index):
            bar_data = _bar_slice(data, timestamp)

            if not bar_data:
                portfolio.record_equity(timestamp, {})
                continue

            prices = {t: float(d["close"].iloc[-1]) for t, d in bar_data.items()}
            portfolio.mark(prices)

            ctx = AlgorithmContext(
                timestamp=(
                    timestamp.to_pydatetime()
                    if hasattr(timestamp, "to_pydatetime") else timestamp
                ),
                portfolio=portfolio,
                data=bar_data,
                warmup=bar_idx < max_lookback,
            )

            self._runner.step(ctx)

            portfolio.record_equity(timestamp, prices)

            last_ctx = ctx

        if last_ctx is not None:
            self._runner.force_flatten(last_ctx)
            portfolio.record_equity(common_index[-1], portfolio.latest_prices)

        equity_curve = portfolio.equity_curve()
        trades = portfolio.trades_df()

        metrics = calculate_metrics(
            equity_curve, trades,
            benchmark=benchmark,
            warmup=max_lookback,
        )

        return BacktestResult(
            equity_curve=equity_curve,
            trades=trades,
            metrics=metrics,
        )
