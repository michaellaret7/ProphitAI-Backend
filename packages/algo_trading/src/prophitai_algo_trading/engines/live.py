"""Live/Paper trading engine for a multi-ticker universe.

Runs the same strategy (deepcopied) across multiple tickers simultaneously,
with shared capital allocation via a single PortfolioTracker and configurable
max concurrent positions. Bars are batched by timestamp so that all tickers
for the same interval are processed together with exits-first + score-ranked
entry ordering — matching backtest execution semantics exactly.
"""

from __future__ import annotations

import asyncio
import logging
from copy import deepcopy
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import pandas as pd

from prophitai_algo_trading.data.clients.alpaca_data import AlpacaDataClient
from prophitai_algo_trading.data.stream.subscriber import async_subscribe
from prophitai_algo_trading.engines.signal_processing import (
    build_risk_trade_callback,
    process_bar_batch,
)
from prophitai_algo_trading.engines.utils import append_bar, bars_to_calendar_days
from prophitai_algo_trading.execution.portfolio_tracker import PortfolioTracker
from prophitai_algo_trading.execution.position_tracker import PositionTracker
from prophitai_algo_trading.execution.cost_model import CostModel
from prophitai_algo_trading.sizing import BasePositionSizer, PercentOfEquitySizer
from prophitai_shared import get_current_utc_time

from prophitai_algo_trading.risk.engine import RiskEngine

if TYPE_CHECKING:
    from prophitai_algo_trading.broker.alpaca import Alpaca
    from prophitai_algo_trading.risk.base import RiskControl
    from prophitai_algo_trading.strategies.base import BaseStrategy

logger = logging.getLogger(__name__)


class LiveRunner:
    """Runs a strategy across a universe of tickers against a live data stream.

    Bars are batched by timestamp: all tickers for the same interval are
    collected, then processed together with exits-first + score-ranked entry
    ordering. This matches backtest execution semantics exactly.

    Args:
        strategy: A BaseStrategy instance — deepcopied per ticker internally.
        broker: Alpaca broker instance for order routing.
        tickers: List of symbols to trade.
        sizer: Position sizing strategy (defaults to PercentOfEquitySizer).
        cost_model: Transaction cost model.
        data_interval: Bar interval for warmup data.
        warmup_bars: Number of historical bars for warmup
                     (defaults to strategy.min_bars_required).
        max_positions: Maximum number of concurrent open positions.
        risk_controls: Risk controls evaluated per bar (entry gating, forced exits).
    """

    def __init__(
        self,
        strategy: BaseStrategy,
        broker: Alpaca,
        tickers: list[str],
        sizer: BasePositionSizer | None = None,
        cost_model: CostModel | None = None,
        data_interval: str = '1min',
        warmup_bars: int | None = None,
        max_positions: int = 10,
        risk_controls: list[RiskControl] | None = None,
    ):
        self._broker = broker
        self._tickers = list(tickers)
        self._cost_model = cost_model or CostModel()
        self._sizer = sizer or PercentOfEquitySizer(
            pct=1 / max_positions, cost_model=self._cost_model,
        )
        self._data_interval = data_interval
        self._warmup_bars = warmup_bars or strategy.min_bars_required
        self._max_positions = max_positions
        self._risk_engine = RiskEngine(risk_controls or [])

        self._strategies: dict[str, BaseStrategy] = {
            t: deepcopy(strategy) for t in tickers
        }
        self._data: dict[str, pd.DataFrame] = {t: pd.DataFrame() for t in tickers}
        self._position_trackers: dict[str, PositionTracker] = {
            t: PositionTracker() for t in tickers
        }
        self._latest_prices: dict[str, float] = {}

        # Reason: batch state for collecting bars by timestamp
        self._current_batch_ts: datetime | None = None
        self._batch_tickers: set[str] = set()

    # ================================
    # --> Helper funcs
    # ================================

    def _warmup_ticker(
        self,
        ticker: str,
        client: AlpacaDataClient,
        start_date: datetime,
        end_date: datetime,
    ) -> bool:
        """Fetch and prepare warmup data for a single ticker.

        Args:
            ticker: Symbol to warm up.
            client: Data client for fetching historical bars.
            start_date: Start of warmup window.
            end_date: End of warmup window.

        Returns:
            True if warmup succeeded, False if ticker should be removed.
        """
        raw_data = client.get_intraday_prices_for_ticker(
            ticker, start_date, end_date, self._data_interval,
        )

        if not raw_data:
            logger.warning("No warmup data for %s — removing from universe", ticker)
            return False

        df = pd.DataFrame(raw_data)
        df['symbol'] = ticker
        df = df[['date', 'symbol', 'open', 'high', 'low', 'close', 'volume']]
        df = df.set_index('date')
        df = df.sort_index()

        df = self._strategies[ticker].calculate_indicators(df)
        df = df.dropna()
        self._data[ticker] = df

        if not df.empty:
            self._latest_prices[ticker] = df['close'].iloc[-1]

        return True

    def _ingest_bar(self, bar: dict) -> None:
        """Append a bar to its ticker's DataFrame and update indicators.

        Updates the ticker's data and latest price without generating
        signals or executing trades. Signal generation happens later
        during batch execution.

        Args:
            bar: Bar dict with date, symbol, OHLCV fields.
        """
        ticker = bar["symbol"]

        self._data[ticker] = append_bar(self._data[ticker], bar)
        self._data[ticker] = self._strategies[ticker].update_indicators(
            self._data[ticker],
        )

        price = self._data[ticker]['close'].iloc[-1]
        self._latest_prices[ticker] = price

    def _execute_batch(
        self,
        portfolio_tracker: PortfolioTracker,
        timestamp: datetime,
    ) -> None:
        """Execute the current batch with exits-first + score-ranked entries.

        Generates signals for all tickers in the batch, classifies into
        exits and entries, then processes exits first to free capital/slots
        before filling entries ranked by signal strength.

        Args:
            portfolio_tracker: Shared portfolio tracker.
            timestamp: Bar timestamp for this batch.
        """
        tickers_with_data = [
            (t, self._data[t]) for t in self._batch_tickers
            if not self._data[t].empty
        ]

        on_trade = None
        if self._risk_engine.active:
            on_trade = build_risk_trade_callback(self._risk_engine)

        def on_error(ticker: str, instr: dict, _exc: Exception) -> None:
            logger.exception(
                "Order execution failed for %s | %s",
                ticker, instr["reason"],
            )

        process_bar_batch(
            tickers_with_data=tickers_with_data,
            strategies=self._strategies,
            position_trackers=self._position_trackers,
            portfolio_tracker=portfolio_tracker,
            risk_engine=self._risk_engine,
            sizer=self._sizer,
            all_close_prices={
                t: self._data[t]["close"]
                for t in self._tickers if not self._data[t].empty
            },
            max_positions=self._max_positions,
            timestamp=timestamp,
            latest_prices=self._latest_prices,
            on_trade=on_trade,
            on_error=on_error,
            swallow_signal_errors=True,
        )

    # ================================
    # --> Public API
    # ================================

    async def warmup(self) -> None:
        """Fetch historical data and calculate initial indicators for each ticker.

        Fetches all tickers concurrently via asyncio.to_thread so HTTP I/O
        overlaps across the universe.
        """
        lookback_days = bars_to_calendar_days(self._warmup_bars, self._data_interval)
        start_date = get_current_utc_time() - timedelta(days=lookback_days)
        end_date = get_current_utc_time()

        client = AlpacaDataClient()

        # Reason: fetch all tickers concurrently — each HTTP call runs in a thread
        results = await asyncio.gather(*(
            asyncio.to_thread(
                self._warmup_ticker, ticker, client, start_date, end_date,
            )
            for ticker in self._tickers
        ))

        # Reason: rebuild ticker list in one pass, then clean up failed entries
        active = [t for t, ok in zip(self._tickers, results) if ok]
        failed = set(self._tickers) - set(active)

        for t in failed:
            del self._strategies[t]
            del self._data[t]
            del self._position_trackers[t]
            
        self._tickers = active

        if not self._tickers:
            raise RuntimeError("All tickers failed warmup — cannot start live trading")

        name = self._strategies[self._tickers[0]].__class__.__name__
        
        print(f"{name} universe warmed up: {len(self._tickers)} tickers active")

    async def run(self) -> None:
        """Subscribe to live data and run the strategy loop across all tickers.

        Bars are batched by timestamp: when a bar arrives with a new timestamp,
        the previous batch is flushed with exits-first + score-ranked entry
        ordering. This matches backtest execution semantics exactly.
        """
        if all(df.empty for df in self._data.values()):
            await self.warmup()

        portfolio_tracker = PortfolioTracker(
            initial_capital=self._broker.get_equity(),
            sizer=self._sizer,
            cost_model=self._cost_model,
            broker=self._broker,
        )

        async for bar in async_subscribe(symbol_filter=self._tickers):
            ticker = bar.get("symbol")
            if ticker not in self._strategies:
                continue

            bar_ts = bar.get("date")

            # Reason: a new timestamp means the previous batch is complete — flush it
            if self._current_batch_ts is not None and bar_ts != self._current_batch_ts:
                self._execute_batch(portfolio_tracker, self._current_batch_ts)
                self._batch_tickers.clear()

            self._current_batch_ts = bar_ts

            # Reason: ingest bar data (append + indicators) before adding to batch
            try:
                self._ingest_bar(bar)
                self._batch_tickers.add(ticker)
            except Exception:
                logger.exception(
                    "Bar ingestion failed for %s — skipping", ticker,
                )

            # Reason: if all tickers have reported, flush immediately
            if self._batch_tickers == set(self._tickers):
                self._execute_batch(portfolio_tracker, self._current_batch_ts)
                self._batch_tickers.clear()
                self._current_batch_ts = None
