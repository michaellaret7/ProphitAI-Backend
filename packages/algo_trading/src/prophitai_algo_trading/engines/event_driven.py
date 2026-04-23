"""Event-driven backtest engine.

Walks bar-by-bar across a universe of tickers with a single shared
portfolio. Respects custom sizers and risk rules. Slower than the
vectorized engine — use this when you need realistic cash/cost accounting,
per-trade exits, or per-bar risk gates.

Execution model per bar:
    1. Compute this bar's indicators + signals for every ticker.
    2. Mark the portfolio at the latest prices.
    3. For each open position, apply risk ``force_exit`` rules (exits first).
    4. For each flat ticker, check the raw signal vs. risk ``block_entry`` rules.
    5. Rank surviving entry candidates by the strategy's score.
    6. Fill top-N entries up to ``max_positions``, sized by the sizer.
    7. Record equity.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from prophitai_algo_trading.cost_model import CostModel
from prophitai_algo_trading.metrics import BacktestResult, calculate_metrics
from prophitai_algo_trading.portfolio import Portfolio
from prophitai_algo_trading.risk.base import RiskContext, RiskRule
from prophitai_algo_trading.sizing import BaseSizer, PercentOfEquitySizer, SizingInput
from prophitai_algo_trading.strategy import BaseStrategy


@dataclass
class _EntryCandidate:
    """Entry candidate surviving risk gates for this bar."""

    symbol: str
    direction: int
    price: float
    score: float
    df: pd.DataFrame


class EventDrivenBacktest:
    """Bar-by-bar backtest with shared capital and realistic accounting.

    Args:
        strategy: Strategy template (deep-copied per ticker).
        initial_capital: Starting equity.
        max_positions: Max concurrent open positions.
        sizer: Position sizer (default PercentOfEquity at 1/max_positions).
        cost_model: Transaction cost model.
        risk_rules: List of RiskRule instances (evaluated in order).
    """

    def __init__(
        self,
        strategy: BaseStrategy,
        initial_capital: float = 100_000.0,
        max_positions: int = 10,
        sizer: BaseSizer | None = None,
        cost_model: CostModel | None = None,
        risk_rules: list[RiskRule] | None = None,
    ):
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.max_positions = max_positions
        self.cost_model = cost_model or CostModel()
        self.sizer = sizer or PercentOfEquitySizer(
            pct=1.0 / max_positions, cost_model=self.cost_model,
        )
        self.risk_rules = risk_rules or []

    def run(
        self,
        data: dict[str, pd.DataFrame],
        benchmark: pd.Series | None = None,
    ) -> BacktestResult:
        """Run the backtest.

        Args:
            data: ``{ticker: OHLCV DataFrame}`` — each with a DatetimeIndex.
            benchmark: Optional benchmark price series for beta + Jensen's alpha.
        """
        if not data:
            raise ValueError("data is empty — nothing to backtest.")

        strategies, enriched = self._precompute(data)
        portfolio = Portfolio(self.initial_capital, self.cost_model)

        common_index = self._union_index(enriched)
        peak_equity = self.initial_capital

        for timestamp in common_index:
            bar_snapshots = self._bar_snapshots(enriched, timestamp)

            if not bar_snapshots:
                portfolio.record_equity(timestamp, {})
                continue

            prices = {t: float(df["close"].iloc[-1]) for t, df in bar_snapshots.items()}
            portfolio.mark(prices)

            equity = portfolio.equity(prices)
            peak_equity = max(peak_equity, equity)

            self._bar_hooks(bar_snapshots, timestamp, prices, portfolio, peak_equity)
            self._process_exits(bar_snapshots, timestamp, prices, portfolio, peak_equity)

            # Reason: exits first, then entries — matches backtest + live semantics.
            equity = portfolio.equity(prices)
            peak_equity = max(peak_equity, equity)

            candidates = self._gather_entries(
                strategies, bar_snapshots, timestamp, prices, portfolio, peak_equity,
            )
            self._fill_entries(candidates, timestamp, portfolio)

            portfolio.record_equity(timestamp, prices)

        self._force_close_all(portfolio, common_index[-1])

        equity_curve = portfolio.equity_curve()
        trades = portfolio.trades_df()
        metrics = calculate_metrics(
            equity_curve, trades,
            benchmark=benchmark,
            warmup=self.strategy.min_bars,
        )

        return BacktestResult(equity_curve=equity_curve, trades=trades, metrics=metrics)

    def _precompute(
        self, data: dict[str, pd.DataFrame],
    ) -> tuple[dict[str, BaseStrategy], dict[str, pd.DataFrame]]:
        """Pre-compute indicators and signals for every ticker."""
        strategies: dict[str, BaseStrategy] = {}
        enriched: dict[str, pd.DataFrame] = {}

        for ticker, df in data.items():
            strat = deepcopy(self.strategy)
            strategies[ticker] = strat

            frame = strat.compute_indicators(df.copy())
            frame = strat.compute_signals(frame)

            if "position" not in frame.columns:
                raise ValueError(
                    f"{ticker}: strategy.compute_signals must produce a 'position' column.",
                )

            frame["_score"] = strat.score(frame).astype(float)
            enriched[ticker] = frame

        return strategies, enriched

    @staticmethod
    def _union_index(enriched: dict[str, pd.DataFrame]) -> pd.DatetimeIndex:
        """Sorted union of every ticker's datetime index."""
        all_ts: set = set()

        for df in enriched.values():
            all_ts.update(df.index)

        return pd.DatetimeIndex(sorted(all_ts))

    @staticmethod
    def _bar_snapshots(
        enriched: dict[str, pd.DataFrame], timestamp: datetime,
    ) -> dict[str, pd.DataFrame]:
        """For each ticker that has a bar at or before ``timestamp``, return the slice up to that bar."""
        snapshots: dict[str, pd.DataFrame] = {}

        for ticker, df in enriched.items():
            if timestamp not in df.index:
                continue

            idx_pos = df.index.get_loc(timestamp)
            snapshots[ticker] = df.iloc[: idx_pos + 1]

        return snapshots

    def _bar_hooks(
        self,
        snapshots: dict[str, pd.DataFrame],
        timestamp: datetime,
        prices: dict[str, float],
        portfolio: Portfolio,
        peak_equity: float,
    ) -> None:
        """Fire ``on_bar`` for every registered risk rule."""
        if not self.risk_rules:
            return

        equity = portfolio.equity(prices)

        for ticker, df in snapshots.items():
            ctx = self._context(
                ticker, df, timestamp, prices[ticker], portfolio, equity, peak_equity,
            )

            for rule in self.risk_rules:
                rule.on_bar(ctx)

    def _process_exits(
        self,
        snapshots: dict[str, pd.DataFrame],
        timestamp: datetime,
        prices: dict[str, float],
        portfolio: Portfolio,
        peak_equity: float,
    ) -> None:
        """Close positions whose signal flipped to 0 or whose risk rules force exit."""
        equity = portfolio.equity(prices)
        open_symbols = list(portfolio.positions.keys())

        for ticker in open_symbols:
            if ticker not in snapshots:
                continue

            df = snapshots[ticker]
            price = prices[ticker]
            current_pos = portfolio.get_position(ticker)
            signaled = int(df["position"].iloc[-1])

            ctx = self._context(
                ticker, df, timestamp, price, portfolio, equity, peak_equity,
            )

            forced = any(rule.force_exit(ctx) for rule in self.risk_rules)
            flipped = signaled != current_pos

            if not forced and not flipped:
                continue

            trade = portfolio.close(ticker, price, timestamp)

            for rule in self.risk_rules:
                rule.on_exit(ctx, trade.pnl if trade else 0.0)

    def _gather_entries(
        self,
        strategies: dict[str, BaseStrategy],
        snapshots: dict[str, pd.DataFrame],
        timestamp: datetime,
        prices: dict[str, float],
        portfolio: Portfolio,
        peak_equity: float,
    ) -> list[_EntryCandidate]:
        """Collect signal-eligible entries after risk gates. Sorted by score desc."""
        _ = strategies  # sizers/rules read from the enriched df directly

        equity = portfolio.equity(prices)
        candidates: list[_EntryCandidate] = []

        for ticker, df in snapshots.items():
            if portfolio.get_position(ticker) != 0:
                continue

            if len(df) < max(self.strategy.min_bars, 1):
                continue

            signaled = int(df["position"].iloc[-1])

            if signaled == 0:
                continue

            price = prices[ticker]

            ctx = self._context(
                ticker, df, timestamp, price, portfolio, equity, peak_equity,
                proposed_direction=signaled,
            )

            if any(rule.block_entry(ctx) for rule in self.risk_rules):
                continue

            score = float(df["_score"].iloc[-1]) if "_score" in df.columns else 1.0

            candidates.append(_EntryCandidate(
                symbol=ticker,
                direction=signaled,
                price=price,
                score=score,
                df=df,
            ))

        candidates.sort(key=lambda c: c.score, reverse=True)

        return candidates

    def _fill_entries(
        self,
        candidates: list[_EntryCandidate],
        timestamp: datetime,
        portfolio: Portfolio,
    ) -> None:
        """Open positions for as many candidates as ``max_positions`` allows."""
        for cand in candidates:
            if portfolio.position_count >= self.max_positions:
                break

            request = SizingInput(
                symbol=cand.symbol,
                direction=cand.direction,
                price=cand.price,
                equity=portfolio.equity(),
                cash=portfolio.cash,
                df=cand.df,
            )

            shares = self.sizer.size(request)

            if shares <= 0:
                continue

            opened = portfolio.open(
                cand.symbol, cand.direction, shares, cand.price, timestamp,
            )

            if not opened:
                continue

            ctx = RiskContext(
                symbol=cand.symbol,
                price=cand.price,
                timestamp=timestamp,
                df=cand.df,
                current_position=cand.direction,
                entry_price=cand.price,
                entry_time=timestamp,
                proposed_direction=cand.direction,
                portfolio_equity=portfolio.equity(),
                portfolio_peak=max(portfolio.equity(), self.initial_capital),
            )

            for rule in self.risk_rules:
                rule.on_entry(ctx)

    def _force_close_all(self, portfolio: Portfolio, last_timestamp: datetime) -> None:
        """Close any still-open positions at the final bar to realize PnL."""
        if not portfolio.positions:
            return

        prices = portfolio.latest_prices

        for symbol in list(portfolio.positions.keys()):
            price = prices.get(symbol, portfolio.positions[symbol].entry_price)
            portfolio.close(symbol, price, last_timestamp)

        portfolio.record_equity(last_timestamp, prices)

    def _context(
        self,
        ticker: str,
        df: pd.DataFrame,
        timestamp: datetime,
        price: float,
        portfolio: Portfolio,
        equity: float,
        peak: float,
        proposed_direction: int | None = None,
    ) -> RiskContext:
        """Build a RiskContext for the current bar."""
        pos = portfolio.positions.get(ticker)

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
            portfolio_peak=peak,
        )
