"""Event-driven backtest engine for a multi-ticker universe.

Processes bars one at a time across all tickers in the universe, mirroring
what LiveRunner does against a live stream. Each ticker gets its own
strategy instance and position tracker; a shared PortfolioTracker manages
capital allocation with a configurable max-positions cap.
"""

from copy import deepcopy

import pandas as pd

from prophitai_algo_trading.engines.trade_routing import (
    process_exits_and_entries,
    force_close_open_positions,
    compile_backtest_result,
)
from prophitai_algo_trading.engines.backtest.models import BacktestResult
from prophitai_algo_trading.engines.utils import (
    resolve_signal,
    align_multi_ticker_data,
    validate_engine_data,
    resolve_warmup,
)
from prophitai_algo_trading.execution import PortfolioTracker, PositionTracker, CostModel
from prophitai_algo_trading.execution.position_sizer import BasePositionSizer, PercentOfEquitySizer
from prophitai_algo_trading.strategies.base import BaseStrategy


class BacktestEngine:
    """Bar-by-bar backtest engine for a multi-ticker universe.

    Processes each bar sequentially across all tickers: appends data, updates
    indicators incrementally, generates signals, and executes trades through a
    shared PortfolioTracker. Exits are processed first to free capital/slots,
    then entries are ranked by signal strength (score_entries) for fill priority.

    Args:
        strategy: A BaseStrategy instance — deepcopied per ticker internally.
        initial_capital: Starting portfolio value.
        cost_model: Transaction cost model.
        sizer: Position sizing strategy (defaults to PercentOfEquitySizer).
        warmup_bars: Number of initial bars to skip
                     (defaults to strategy.min_bars_required).
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
        """Validate input data.

        Args:
            data: Mapping of ticker → OHLCV DataFrame.

        Raises:
            ValueError: If any DataFrame fails validation.
        """
        validate_engine_data(data)

    def _init_trackers(
        self,
        tickers: list[str],
    ) -> tuple[dict[str, BaseStrategy], dict[str, PositionTracker], PortfolioTracker]:
        """Create per-ticker strategies, position trackers, and shared portfolio tracker.

        Args:
            tickers: List of ticker symbols.

        Returns:
            Tuple of (strategies dict, position_trackers dict, portfolio_tracker).
        """
        strategies: dict[str, BaseStrategy] = {
            t: deepcopy(self._strategy_template) for t in tickers
        }
        position_trackers: dict[str, PositionTracker] = {
            t: PositionTracker() for t in tickers
        }
        portfolio_tracker = PortfolioTracker(
            initial_capital=self.initial_capital,
            sizer=self._sizer,
            cost_model=self._cost_model,
        )
        return strategies, position_trackers, portfolio_tracker

    def _warmup_indicators(
        self,
        tickers: list[str],
        aligned: dict[str, pd.DataFrame],
        strategies: dict[str, BaseStrategy],
        warmup: int,
        verbose: bool,
    ) -> tuple[dict[str, pd.DataFrame], dict[str, float]]:
        """Batch calculate indicators on warmup bars for each ticker.

        Args:
            tickers: List of ticker symbols.
            aligned: Aligned DataFrames with _has_bar column.
            strategies: Per-ticker strategy instances.
            warmup: Number of warmup bars.
            verbose: If True, print progress.

        Returns:
            Tuple of (ticker_dfs for incremental updates, latest_prices dict).
        """
        if verbose:
            print(f"[1/3] Warmup: calculating indicators on {warmup} bars "
                  f"for {len(tickers)} tickers...")

        ticker_dfs: dict[str, pd.DataFrame] = {}
        latest_prices: dict[str, float] = {}

        for ticker in tickers:
            warmup_data = aligned[ticker].iloc[:warmup].copy()
            # Reason: drop rows without real data before warmup calculation
            warmup_real = warmup_data[warmup_data["_has_bar"]].drop(columns=["_has_bar"])
            if warmup_real.empty:
                continue
            ticker_dfs[ticker] = strategies[ticker].calculate_indicators(warmup_real)
            if not ticker_dfs[ticker].empty:
                latest_prices[ticker] = ticker_dfs[ticker]["close"].iloc[-1]

        return ticker_dfs, latest_prices

    def _simulate_bar_by_bar(
        self,
        common_index: pd.DatetimeIndex,
        aligned: dict[str, pd.DataFrame],
        tickers: list[str],
        strategies: dict[str, BaseStrategy],
        position_trackers: dict[str, PositionTracker],
        portfolio_tracker: PortfolioTracker,
        ticker_dfs: dict[str, pd.DataFrame],
        latest_prices: dict[str, float],
        warmup: int,
        verbose: bool,
    ) -> None:
        """Process bars one at a time, executing trades with exits-first ordering.

        Mutates portfolio_tracker, position_trackers, ticker_dfs, and
        latest_prices in place.

        Args:
            common_index: Unified datetime index across all tickers.
            aligned: Aligned DataFrames with _has_bar column.
            tickers: List of ticker symbols.
            strategies: Per-ticker strategy instances.
            position_trackers: Per-ticker position state machines.
            portfolio_tracker: Shared portfolio tracker.
            ticker_dfs: Per-ticker DataFrames for incremental indicator updates.
            latest_prices: Most recent price per ticker (mutated in place).
            warmup: Number of warmup bars already processed.
            verbose: If True, print trade-by-trade details.
        """
        if verbose:
            print(f"[2/3] Trading: processing {len(common_index) - warmup} bars "
                  f"bar-by-bar across {len(tickers)} tickers...")

        for i in range(warmup, len(common_index)):
            timestamp = common_index[i]

            # Reason: first pass — update data and compute signals for all tickers,
            # then classify into exits/entries for deterministic ordering.
            bar_signals: dict[str, tuple[int, float, float]] = {}

            for ticker in tickers:
                row = aligned[ticker].iloc[i]

                # Reason: update latest close for mark-to-market even on non-real bars
                if pd.notna(row["close"]):
                    latest_prices[ticker] = row["close"]

                if not row["_has_bar"]:
                    continue

                if ticker not in ticker_dfs:
                    ticker_dfs[ticker] = pd.DataFrame()

                # Append real bar (without _has_bar column)
                bar = row.drop("_has_bar").to_frame().T
                bar.index = [timestamp]
                ticker_dfs[ticker] = pd.concat([ticker_dfs[ticker], bar])

                # Incrementally update indicators
                ticker_dfs[ticker] = strategies[ticker].update_indicators(
                    ticker_dfs[ticker],
                )

                # Generate signals from latest bar
                signals = strategies[ticker].generate_signals(ticker_dfs[ticker])
                le = bool(signals["long_entry"].iloc[-1])
                lx = bool(signals["long_exit"].iloc[-1])
                se = bool(signals["short_entry"].iloc[-1])
                sx = bool(signals["short_exit"].iloc[-1])

                price = ticker_dfs[ticker]["close"].iloc[-1]

                target = resolve_signal(
                    le, lx, se, sx, position_trackers[ticker].position,
                )

                if target == position_trackers[ticker].position:
                    continue

                score = float(strategies[ticker].score_entries(ticker_dfs[ticker]).iloc[-1])
                bar_signals[ticker] = (target, price, score)

            # Reason: exits first to free capital/slots, then entries ranked by score
            exits = [
                (t, target, price)
                for t, (target, price, _score) in bar_signals.items()
                if target == 0
            ]
            entries = sorted(
                [
                    (t, target, price, score)
                    for t, (target, price, score) in bar_signals.items()
                    if target != 0
                ],
                key=lambda x: x[3],
                reverse=True,
            )

            # Reason: only refresh sizer state when entries exist (sizing only matters for new positions)
            if entries and ticker_dfs:
                self._sizer.prepare_for_bar({t: ticker_dfs[t]["close"] for t in ticker_dfs})

            # Reason: verbose callback captures latest_prices for equity logging
            on_trade = None
            
            if verbose:
                def on_trade(ticker: str, instr: dict) -> None:
                    reason = instr["reason"]
                    equity = portfolio_tracker.get_total_equity(latest_prices)
                    print(f"  [{timestamp}]  {ticker}  ${instr['price']:.2f}  "
                          f"{reason.upper()}  equity=${equity:,.2f}")

            process_exits_and_entries(
                exits, entries, position_trackers, portfolio_tracker,
                self._max_positions, timestamp, on_trade=on_trade,
            )

            portfolio_tracker.record_equity(timestamp, latest_prices)

    # ================================
    # --> Public API
    # ================================

    def run(
        self,
        data: dict[str, pd.DataFrame],
        warmup_bars: int | None = None,
        plot: bool = False,
        verbose: bool = False,
    ) -> BacktestResult:
        """Run the backtest over historical data for multiple tickers.

        Args:
            data: Mapping of ticker → OHLCV DataFrame with datetime index.
            warmup_bars: Override for warmup bar count.
            plot: If True, display equity curve chart.
            verbose: If True, print step-by-step execution details.

        Returns:
            BacktestResult with metrics, equity curve, trades, and
            strategy_data=None (not applicable for multi-ticker).
        """
        self._validate(data)
        warmup = resolve_warmup(
            warmup_bars, self._warmup_bars,
            self._strategy_template.min_bars_required,
        )

        tickers = list(data.keys())
        common_index, aligned = align_multi_ticker_data(data)

        strategies, position_trackers, portfolio_tracker = self._init_trackers(tickers)

        ticker_dfs, latest_prices = self._warmup_indicators(
            tickers, aligned, strategies, warmup, verbose,
        )

        self._simulate_bar_by_bar(
            common_index, aligned, tickers, strategies, position_trackers,
            portfolio_tracker, ticker_dfs, latest_prices, warmup, verbose,
        )

        force_close_open_positions(
            portfolio_tracker, position_trackers, latest_prices,
            common_index[-1], verbose,
        )

        result = compile_backtest_result(portfolio_tracker, len(tickers), verbose)
        if plot:
            self._plot_backtest_results(result)
        return result

    def _plot_backtest_results(self, result: BacktestResult) -> None:
        """Plot equity curve and trade P&L from a backtest result."""
        # Reason: lazy import to avoid ~200ms matplotlib load for non-plotting runs
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates

        fig, (ax_equity, ax_pnl) = plt.subplots(
            2, 1, figsize=(14, 8),
            gridspec_kw={"height_ratios": [3, 1]}, sharex=True,
        )

        equity = result.equity_curve[
            ~result.equity_curve.index.duplicated(keep="last")
        ]

        ax_equity.plot(
            equity.index, equity["equity"], color="steelblue", linewidth=1.2,
        )
        ax_equity.set_title("Universe Backtest — Equity Curve", fontsize=13)
        ax_equity.set_ylabel("Portfolio Value ($)")
        ax_equity.grid(True, alpha=0.3)

        trades = result.trades
        if not trades.empty:
            colors = ["green" if p > 0 else "red" for p in trades["pnl"]]
            ax_pnl.bar(
                trades["exit_date"], trades["pnl"],
                color=colors, width=2, alpha=0.8,
            )
            ax_pnl.axhline(0, color="black", linewidth=0.5)

        ax_pnl.set_title("Trade P&L", fontsize=13)
        ax_pnl.set_ylabel("P&L ($)")
        ax_pnl.set_xlabel("Date")
        ax_pnl.grid(True, alpha=0.3)

        ax_pnl.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        fig.autofmt_xdate(rotation=30)
        fig.tight_layout()
        plt.show()
