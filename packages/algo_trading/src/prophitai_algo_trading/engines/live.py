"""Live/paper trading runner.

Subscribes to the ZMQ bar stream (published by the Alpaca WebSocket), batches
bars by timestamp, and drives the same exits-first + ranked-entries
semantics as the event-driven backtest. Hydrates portfolio state from the
broker at startup so restarts pick up existing positions without duplicate
fills.

Warmup: each ticker needs ``strategy.min_bars`` of historical bars fetched
from Alpaca Market Data before the first live bar arrives. You supply the
history as a dict of DataFrames (same shape as a backtest input) — this
keeps the live runner agnostic to any particular data provider for history.

Run lifecycle:
    await runner.warmup(history_provider)   # pre-warm indicators
    await runner.hydrate()                   # pull broker snapshot
    await runner.run()                       # start the bar loop
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from copy import deepcopy
from typing import TYPE_CHECKING

import pandas as pd

from prophitai_algo_trading.cost_model import CostModel
from prophitai_algo_trading.data.stream.subscriber import async_subscribe
from prophitai_algo_trading.portfolio import Portfolio, Position
from prophitai_algo_trading.risk.base import RiskContext, RiskRule
from prophitai_algo_trading.sizing import BaseSizer, PercentOfEquitySizer, SizingInput
from prophitai_algo_trading.strategy import BaseStrategy

if TYPE_CHECKING:
    from prophitai_algo_trading.broker.alpaca import Alpaca

logger = logging.getLogger(__name__)


HistoryProvider = Callable[[str], pd.DataFrame]


class LiveRunner:
    """Runs a strategy against a live ZMQ bar stream.

    Args:
        strategy: Strategy template (deep-copied per ticker).
        broker: Alpaca wrapper for order routing + startup snapshot.
        tickers: Universe to trade.
        sizer: Position sizer (default PercentOfEquity).
        cost_model: Local cost model — used for sizing math and mirror accounting.
        max_positions: Max concurrent open positions.
        risk_rules: Per-bar risk rules evaluated before entries and exits.
    """

    def __init__(
        self,
        strategy: BaseStrategy,
        broker: "Alpaca",
        tickers: list[str],
        sizer: BaseSizer | None = None,
        cost_model: CostModel | None = None,
        max_positions: int = 10,
        risk_rules: list[RiskRule] | None = None,
    ):
        self.strategy_template = strategy
        self.broker = broker
        self.tickers = list(tickers)
        self.cost_model = cost_model or CostModel()
        self.sizer = sizer or PercentOfEquitySizer(
            pct=1.0 / max_positions, cost_model=self.cost_model,
        )
        self.max_positions = max_positions
        self.risk_rules = risk_rules or []

        self._strategies: dict[str, BaseStrategy] = {
            t: deepcopy(strategy) for t in self.tickers
        }
        self._frames: dict[str, pd.DataFrame] = {t: pd.DataFrame() for t in self.tickers}
        self._portfolio: Portfolio | None = None
        self._peak_equity: float = 0.0
        self._current_batch_ts = None
        self._batch_tickers: set[str] = set()

    async def warmup(self, history: HistoryProvider | dict[str, pd.DataFrame]) -> None:
        """Populate each ticker's frame with historical bars.

        Args:
            history: Either a dict ``{ticker: DataFrame}`` or a callable
                ``ticker -> DataFrame``. Missing or empty frames drop the
                ticker from the universe.
        """
        active: list[str] = []

        for ticker in self.tickers:
            df = (
                history(ticker) if callable(history)
                else history.get(ticker, pd.DataFrame())
            )

            if df is None or df.empty:
                logger.warning("No warmup data for %s — removing from universe", ticker)
                continue

            enriched = self._strategies[ticker].compute_indicators(df.copy())

            self._frames[ticker] = enriched
            active.append(ticker)

        for dropped in set(self.tickers) - set(active):
            self._strategies.pop(dropped, None)
            self._frames.pop(dropped, None)

        self.tickers = active

        if not self.tickers:
            raise RuntimeError("All tickers failed warmup — cannot start live trading")

        name = self.strategy_template.__class__.__name__
        print(f"{name} universe warmed up: {len(self.tickers)} tickers active")

    async def hydrate(self) -> None:
        """Fetch the broker snapshot and seed portfolio + position state."""
        snapshot = await asyncio.to_thread(self.broker.get_startup_snapshot)

        self._portfolio = Portfolio(snapshot.equity, self.cost_model)
        self._portfolio.cash = snapshot.cash
        self._peak_equity = snapshot.equity

        managed_symbols = set(self.tickers)
        unmanaged = [p for p in snapshot.positions if p.symbol not in managed_symbols]

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
            "Hydrated live state — cash=%.2f equity=%.2f hydrated=%d",
            snapshot.cash, snapshot.equity, len(snapshot.positions),
        )

    async def run(self) -> None:
        """Subscribe to bars and execute the exits-first + ranked-entries loop."""
        if self._portfolio is None:
            raise RuntimeError("Call hydrate() before run().")

        async for bar in async_subscribe(symbol_filter=self.tickers):
            ticker = bar.get("symbol")

            if ticker not in self._strategies:
                continue

            bar_ts = bar.get("date")

            if self._current_batch_ts is not None and bar_ts != self._current_batch_ts:
                self._execute_batch(self._current_batch_ts)
                self._batch_tickers.clear()

            self._current_batch_ts = bar_ts

            try:
                self._ingest(ticker, bar)
                self._batch_tickers.add(ticker)
            except Exception:
                logger.exception("Bar ingest failed for %s", ticker)

            if self._batch_tickers == set(self.tickers):
                self._execute_batch(self._current_batch_ts)
                self._batch_tickers.clear()
                self._current_batch_ts = None

        if self._current_batch_ts and self._batch_tickers:
            self._execute_batch(self._current_batch_ts)

    def _ingest(self, ticker: str, bar: dict) -> None:
        """Append a bar to the ticker frame and refresh indicators."""
        row = pd.DataFrame([{
            "open": float(bar["open"]),
            "high": float(bar["high"]),
            "low": float(bar["low"]),
            "close": float(bar["close"]),
            "volume": float(bar["volume"]),
        }], index=pd.to_datetime([bar["date"]]))
        row.index.name = "date"

        current = self._frames[ticker]

        combined = pd.concat([current.drop(columns=[
            c for c in current.columns
            if c not in ("open", "high", "low", "close", "volume")
        ], errors="ignore"), row])

        combined = combined[~combined.index.duplicated(keep="last")].sort_index()

        self._frames[ticker] = self._strategies[ticker].compute_indicators(combined)

    def _execute_batch(self, timestamp) -> None:
        """Run one timestamp across all batched tickers with exits-first ordering."""
        portfolio = self._portfolio

        if portfolio is None:
            return

        batch_frames: dict[str, pd.DataFrame] = {}

        for ticker in self._batch_tickers:
            frame = self._frames[ticker]

            if frame.empty:
                continue

            # Reason: recompute signals on the latest bar slice — cheap and keeps logic
            #         identical across backtest and live.
            batch_frames[ticker] = self._strategies[ticker].compute_signals(frame.copy())

        if not batch_frames:
            return

        prices = {t: float(df["close"].iloc[-1]) for t, df in batch_frames.items()}
        portfolio.mark(prices)

        equity = portfolio.equity(prices)
        self._peak_equity = max(self._peak_equity, equity)

        self._bar_hooks(batch_frames, timestamp, prices, equity)
        self._process_exits(batch_frames, timestamp, prices, equity)

        equity = portfolio.equity(prices)
        self._peak_equity = max(self._peak_equity, equity)

        candidates = self._gather_entries(batch_frames, timestamp, prices, equity)
        self._fill_entries(candidates, timestamp)

        portfolio.record_equity(timestamp, prices)

    def _bar_hooks(
        self,
        frames: dict[str, pd.DataFrame],
        timestamp,
        prices: dict[str, float],
        equity: float,
    ) -> None:
        if not self.risk_rules:
            return

        for ticker, df in frames.items():
            ctx = self._context(ticker, df, timestamp, prices[ticker], equity)

            for rule in self.risk_rules:
                rule.on_bar(ctx)

    def _process_exits(
        self,
        frames: dict[str, pd.DataFrame],
        timestamp,
        prices: dict[str, float],
        equity: float,
    ) -> None:
        portfolio = self._portfolio
        assert portfolio is not None

        for ticker in list(portfolio.positions.keys()):
            if ticker not in frames:
                continue

            df = frames[ticker]
            price = prices[ticker]
            current = portfolio.get_position(ticker)
            signaled = int(df["position"].iloc[-1])

            ctx = self._context(ticker, df, timestamp, price, equity)

            forced = any(rule.force_exit(ctx) for rule in self.risk_rules)
            flipped = signaled != current

            if not forced and not flipped:
                continue

            try:
                self.broker.close_position(ticker)
            except Exception:
                logger.exception("Broker close failed for %s", ticker)
                continue

            trade = portfolio.close(ticker, price, timestamp)

            for rule in self.risk_rules:
                rule.on_exit(ctx, trade.pnl if trade else 0.0)

    def _gather_entries(
        self,
        frames: dict[str, pd.DataFrame],
        timestamp,
        prices: dict[str, float],
        equity: float,
    ) -> list[tuple[str, int, float, float, pd.DataFrame]]:
        """Return entry candidates sorted by score descending."""
        portfolio = self._portfolio
        assert portfolio is not None

        candidates: list[tuple[str, int, float, float, pd.DataFrame]] = []

        for ticker, df in frames.items():
            if portfolio.get_position(ticker) != 0:
                continue

            signaled = int(df["position"].iloc[-1])

            if signaled == 0:
                continue

            ctx = self._context(
                ticker, df, timestamp, prices[ticker], equity,
                proposed_direction=signaled,
            )

            if any(rule.block_entry(ctx) for rule in self.risk_rules):
                continue

            score = float(self._strategies[ticker].score(df).iloc[-1])

            candidates.append((ticker, signaled, prices[ticker], score, df))

        candidates.sort(key=lambda c: c[3], reverse=True)

        return candidates

    def _fill_entries(self, candidates, timestamp) -> None:
        portfolio = self._portfolio
        assert portfolio is not None

        for ticker, direction, price, _score, df in candidates:
            if portfolio.position_count >= self.max_positions:
                break

            request = SizingInput(
                symbol=ticker,
                direction=direction,
                price=price,
                equity=portfolio.equity(),
                cash=portfolio.cash,
                df=df,
            )

            shares = self.sizer.size(request)

            if shares <= 0:
                continue

            try:
                if direction == 1:
                    self.broker.buy(ticker, qty=shares)
                else:
                    self.broker.sell(ticker, qty=shares)
            except Exception:
                logger.exception("Broker order failed for %s", ticker)
                continue

            portfolio.open(ticker, direction, shares, price, timestamp)

            ctx = self._context(ticker, df, timestamp, price, portfolio.equity(),
                                proposed_direction=direction)

            for rule in self.risk_rules:
                rule.on_entry(ctx)

    def _context(
        self,
        ticker: str,
        df: pd.DataFrame,
        timestamp,
        price: float,
        equity: float,
        proposed_direction: int | None = None,
    ) -> RiskContext:
        assert self._portfolio is not None
        pos = self._portfolio.positions.get(ticker)

        return RiskContext(
            symbol=ticker,
            price=price,
            timestamp=timestamp,
            df=df,
            current_position=pos.direction if pos else 0,
            entry_price=pos.entry_price if pos else None,
            entry_time=pos.entry_time if pos else None,
            proposed_direction=proposed_direction,
            portfolio_equity=equity,
            portfolio_peak=self._peak_equity,
        )
