"""Live/paper trading runner — framework version.

Subscribes to the ZMQ bar stream, batches bars by timestamp, and drives
the same Alpha -> PCM -> Risk -> Execution pipeline as
``EventDrivenBacktest``. The user constructs an ``Algorithm`` with a
``BrokerExecutionModel`` so the pipeline terminates at real broker
orders; the runner calls the broker directly only for lifecycle work
(startup snapshot + hydrate).

Lifecycle:

    await runner.warmup(history_provider)   # pre-warm alpha state
    await runner.hydrate()                   # pull broker snapshot
    await runner.run()                       # ingest the bar stream

Restarts are safe: ``hydrate()`` reads open positions from the broker
and seeds the Portfolio so execution diffs don't try to re-open already-
held names.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

import pandas as pd

from prophitai_algo_trading.cost_model import CostModel
from prophitai_algo_trading.data.stream.subscriber import async_subscribe
from prophitai_algo_trading.framework.models import AlgorithmContext
from prophitai_algo_trading.portfolio import Portfolio, Position

if TYPE_CHECKING:
    from prophitai_algo_trading.broker.alpaca import Alpaca
    from prophitai_algo_trading.framework.algorithm import Algorithm


logger = logging.getLogger(__name__)

HistoryProvider = Callable[[str], pd.DataFrame]


#     ================================
# --> Helper funcs
#     ================================

def _ingest_bar(
    frame: pd.DataFrame, bar: dict,
) -> pd.DataFrame:
    """Append one streamed bar to a ticker's rolling DataFrame."""
    row = pd.DataFrame([{
        "open": float(bar["open"]),
        "high": float(bar["high"]),
        "low": float(bar["low"]),
        "close": float(bar["close"]),
        "volume": float(bar["volume"]),
    }], index=pd.to_datetime([bar["date"]]))
    row.index.name = "date"

    keep_cols = [c for c in frame.columns if c in row.columns]
    base = frame[keep_cols] if keep_cols else frame

    combined = pd.concat([base, row])

    return combined[~combined.index.duplicated(keep="last")].sort_index()


def _position_snapshot(portfolio: Portfolio) -> dict[str, int]:
    """Symbol -> signed direction (±1 for open, 0 for flat)."""
    return {
        symbol: pos.direction
        for symbol, pos in portfolio.positions.items()
    }


#     ================================
# --> Runner
#     ================================

class LiveRunner:
    """Drives an ``Algorithm`` against a live ZMQ bar stream.

    Args:
        algorithm: Fully-configured ``Algorithm``. The ``execution`` field
            should be a ``BrokerExecutionModel(broker)`` that references
            the same broker passed into this runner.
        broker: Alpaca wrapper — used for startup snapshot + hydrate.
            Execution goes through ``algorithm.execution``, not directly
            through the broker.
        tickers: Universe to subscribe to on the ZMQ stream.
        cost_model: Transaction cost model for the mirror Portfolio.
    """

    def __init__(
        self,
        algorithm: "Algorithm",
        broker: "Alpaca",
        tickers: list[str],
        cost_model: CostModel | None = None,
    ):
        self.algorithm = algorithm
        self.broker = broker
        self.tickers = list(tickers)
        self.cost_model = cost_model or CostModel()

        self._frames: dict[str, pd.DataFrame] = {
            t: pd.DataFrame() for t in self.tickers
        }
        self._portfolio: Portfolio | None = None
        self._bar_count: int = 0

        self._current_batch_ts = None
        self._batch_tickers: set[str] = set()

    async def warmup(
        self,
        history: HistoryProvider | dict[str, pd.DataFrame],
    ) -> None:
        """Seed each ticker's rolling frame with historical bars.

        Args:
            history: Either ``{ticker: DataFrame}`` or callable
                ``ticker -> DataFrame``. Tickers with empty history are
                dropped from the active universe.
        """
        active: list[str] = []

        for ticker in self.tickers:
            df = (
                history(ticker) if callable(history)
                else history.get(ticker, pd.DataFrame())
            )

            if df is None or df.empty:
                logger.warning(
                    "No warmup data for %s — removing from universe", ticker,
                )
                continue

            self._frames[ticker] = df
            active.append(ticker)

        for dropped in set(self.tickers) - set(active):
            self._frames.pop(dropped, None)

        self.tickers = active

        if not self.tickers:
            raise RuntimeError(
                "All tickers failed warmup — cannot start live trading",
            )

        print(
            f"Live runner universe warmed up: {len(self.tickers)} tickers active",
        )

    async def hydrate(self) -> None:
        """Pull broker snapshot, seed mirror portfolio + seed positions."""
        snapshot = await asyncio.to_thread(self.broker.get_startup_snapshot)

        self._portfolio = Portfolio(snapshot.equity, self.cost_model)
        self._portfolio.cash = snapshot.cash

        managed = set(self.tickers)
        unmanaged = [p for p in snapshot.positions if p.symbol not in managed]

        if unmanaged:
            names = ", ".join(p.symbol for p in unmanaged)
            raise RuntimeError(
                f"Unmanaged broker positions found: {names}. "
                "Either add them to the universe or close them manually."
            )

        for pos in snapshot.positions:
            direction = 1 if pos.direction.value == "long" else -1

            self._portfolio.positions[pos.symbol] = Position(
                symbol=pos.symbol,
                shares=pos.shares,
                direction=direction,
                entry_price=pos.entry_price,
                entry_time=pos.entry_date,
                entry_cost=0.0,
            )

        logger.info(
            "Hydrated — cash=%.2f equity=%.2f positions=%d",
            snapshot.cash, snapshot.equity, len(snapshot.positions),
        )

    async def run(self) -> None:
        """Subscribe to the bar stream and drive the pipeline per batch."""
        if self._portfolio is None:
            raise RuntimeError("Call hydrate() before run().")

        async for bar in async_subscribe(symbol_filter=self.tickers):
            ticker = bar.get("symbol")

            if ticker not in self._frames:
                continue

            bar_ts = bar.get("date")

            if (
                self._current_batch_ts is not None
                and bar_ts != self._current_batch_ts
            ):
                self._execute_batch(self._current_batch_ts)
                self._batch_tickers.clear()

            self._current_batch_ts = bar_ts

            try:
                self._frames[ticker] = _ingest_bar(self._frames[ticker], bar)
                self._batch_tickers.add(ticker)
            except Exception:
                logger.exception("Bar ingest failed for %s", ticker)

            if self._batch_tickers == set(self.tickers):
                self._execute_batch(self._current_batch_ts)
                self._batch_tickers.clear()
                self._current_batch_ts = None

        if self._current_batch_ts is not None and self._batch_tickers:
            self._execute_batch(self._current_batch_ts)

    #     ================================
    # --> Per-batch pipeline
    #     ================================

    def _execute_batch(self, timestamp) -> None:
        """Run one timestamp's worth of bars through the pipeline."""
        if self._portfolio is None:
            return

        batch_data: dict[str, pd.DataFrame] = {
            t: self._frames[t]
            for t in self._batch_tickers
            if not self._frames[t].empty
        }

        if not batch_data:
            return

        prices = {t: float(df["close"].iloc[-1]) for t, df in batch_data.items()}
        self._portfolio.mark(prices)

        self._bar_count += 1

        ctx = AlgorithmContext(
            timestamp=timestamp,
            portfolio=self._portfolio,
            data=batch_data,
            warmup=self._bar_count <= self.algorithm.max_lookback,
        )

        insights: list = []

        for alpha in self.algorithm.alphas:
            insights.extend(alpha.update(ctx))

        targets = self.algorithm.portfolio_construction.create_targets(ctx, insights)
        targets = self.algorithm.risk_management.manage(ctx, targets)

        positions_before = _position_snapshot(self._portfolio)
        trades_before = len(self._portfolio.trades)

        self.algorithm.execution.execute(ctx, targets)

        self._notify_position_changes(ctx, positions_before, trades_before)

        self._portfolio.record_equity(timestamp, prices)

    #     ================================
    # --> Notify diffing (shared shape with backtest)
    #     ================================

    def _notify_position_changes(
        self,
        ctx: AlgorithmContext,
        before: dict[str, int],
        trades_before: int,
    ) -> None:
        risk = self.algorithm.risk_management

        notify_entry = getattr(risk, "notify_entry", None)
        notify_exit = getattr(risk, "notify_exit", None)

        if notify_entry is None and notify_exit is None:
            return

        assert self._portfolio is not None

        after = _position_snapshot(self._portfolio)

        new_trades = self._portfolio.trades[trades_before:]
        pnl_by_symbol: dict[str, float] = {
            trade.symbol: trade.pnl for trade in new_trades
        }

        for symbol in set(before) | set(after):
            before_dir = before.get(symbol, 0)
            after_dir = after.get(symbol, 0)

            was_flat = before_dir == 0
            is_flat = after_dir == 0
            flipped = (
                not was_flat and not is_flat and before_dir * after_dir < 0
            )

            closed = not was_flat and (is_flat or flipped)
            opened = not is_flat and (was_flat or flipped)

            if closed and notify_exit is not None:
                notify_exit(ctx, symbol, pnl_by_symbol.get(symbol, 0.0))

            if opened and notify_entry is not None:
                notify_entry(ctx, symbol)
