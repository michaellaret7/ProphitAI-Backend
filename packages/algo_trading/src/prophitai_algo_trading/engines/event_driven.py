"""Event-driven backtest engine — framework version.

Takes an ``Algorithm`` (alphas + PCM + risk + execution) and drives its
pipeline bar-by-bar over historical price data. The same ``Algorithm``
instance also runs live — only the ``ExecutionModel`` differs.

Per-bar flow::

    1. Slice each ticker's history up to ``timestamp``.
    2. Mark portfolio to current prices.
    3. Build AlgorithmContext (warmup True until max_lookback bars).
    4. Alphas -> list[Insight]   (concat across alphas)
    5. PortfolioConstructionModel -> list[PortfolioTarget]
    6. RiskManagementModel -> list[PortfolioTarget]
    7. Snapshot positions pre-execute.
    8. ExecutionModel.execute()  (mutates portfolio)
    9. Diff positions; fire notify_entry / notify_exit on risk model
       so stateful rules (TrailingStopExit, TimeStop,
       ConsecutiveLossCooldown) see the open/close events.
    10. Record equity for the bar.

After the last bar, remaining positions are force-closed at last prices
so realized P&L appears in the trade log and equity curve.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from prophitai_algo_trading.cost_model import CostModel
from prophitai_algo_trading.framework.models import AlgorithmContext
from prophitai_algo_trading.metrics import BacktestResult, calculate_metrics
from prophitai_algo_trading.portfolio import Portfolio

if TYPE_CHECKING:
    from datetime import datetime

    from prophitai_algo_trading.framework.algorithm import Algorithm


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


def _position_snapshot(portfolio: Portfolio) -> dict[str, int]:
    """Symbol -> signed direction (±1 for open, 0 for flat)."""
    return {
        symbol: pos.direction
        for symbol, pos in portfolio.positions.items()
    }


#     ================================
# --> Engine
#     ================================

class EventDrivenBacktest:
    """Bar-by-bar backtest driving an ``Algorithm``'s pipeline.

    Args:
        algorithm: Fully-configured ``Algorithm`` (alphas + PCM + risk +
            execution — typically ``SimulatedExecutionModel`` for backtests).
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

        for bar_idx, timestamp in enumerate(common_index):
            bar_data = _bar_slice(data, timestamp)

            if not bar_data:
                portfolio.record_equity(timestamp, {})
                continue

            prices = {t: float(d["close"].iloc[-1]) for t, d in bar_data.items()}
            portfolio.mark(prices)

            ctx = AlgorithmContext(
                timestamp=timestamp.to_pydatetime() if hasattr(timestamp, "to_pydatetime") else timestamp,
                portfolio=portfolio,
                data=bar_data,
                warmup=bar_idx < max_lookback,
            )

            self._run_pipeline(ctx)

            portfolio.record_equity(timestamp, prices)

        self._force_close_all(portfolio, common_index[-1])

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

    #     ================================
    # --> Per-bar pipeline
    #     ================================

    def _run_pipeline(self, ctx: AlgorithmContext) -> None:
        insights: list = []

        for alpha in self.algorithm.alphas:
            insights.extend(alpha.update(ctx))

        targets = self.algorithm.portfolio_construction.create_targets(ctx, insights)
        targets = self.algorithm.risk_management.manage(ctx, targets)

        positions_before = _position_snapshot(ctx.portfolio)
        trades_before = len(ctx.portfolio.trades)

        self.algorithm.execution.execute(ctx, targets)

        self._notify_position_changes(
            ctx, positions_before, trades_before,
        )

    #     ================================
    # --> Notify diffing
    #     ================================

    def _notify_position_changes(
        self,
        ctx: AlgorithmContext,
        before: dict[str, int],
        trades_before: int,
    ) -> None:
        """Fire notify_entry / notify_exit on the risk model based on the
        diff between pre- and post-execute position state."""
        risk = self.algorithm.risk_management

        notify_entry = getattr(risk, "notify_entry", None)
        notify_exit = getattr(risk, "notify_exit", None)

        if notify_entry is None and notify_exit is None:
            return

        after = _position_snapshot(ctx.portfolio)

        new_trades = ctx.portfolio.trades[trades_before:]
        pnl_by_symbol: dict[str, float] = {
            trade.symbol: trade.pnl for trade in new_trades
        }

        all_symbols = set(before) | set(after)

        for symbol in all_symbols:
            before_dir = before.get(symbol, 0)
            after_dir = after.get(symbol, 0)

            # Reason: a flip registers as BOTH close-then-open — fire both.
            was_flat = before_dir == 0
            is_flat = after_dir == 0
            flipped = (
                not was_flat and not is_flat and before_dir * after_dir < 0
            )

            closed = not was_flat and (is_flat or flipped)
            opened = not is_flat and (was_flat or flipped)

            if closed and notify_exit is not None:
                pnl = pnl_by_symbol.get(symbol, 0.0)
                notify_exit(ctx, symbol, pnl)

            if opened and notify_entry is not None:
                notify_entry(ctx, symbol)

    #     ================================
    # --> End-of-run cleanup
    #     ================================

    def _force_close_all(
        self, portfolio: Portfolio, last_timestamp,
    ) -> None:
        """Close any still-open positions at final prices so realized P&L
        appears in the trade log and equity curve."""
        if not portfolio.positions:
            return

        prices = portfolio.latest_prices

        for symbol in list(portfolio.positions.keys()):
            price = prices.get(symbol, portfolio.positions[symbol].entry_price)
            portfolio.close(symbol, price, last_timestamp)

        portfolio.record_equity(last_timestamp, prices)
