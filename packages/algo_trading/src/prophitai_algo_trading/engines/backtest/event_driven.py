"""Event-driven backtest engine for a multi-ticker universe."""

import pandas as pd

from prophitai_algo_trading.engines.backtest.event_driven_helpers import (
    init_event_trackers,
    plot_event_backtest_results,
    simulate_event_bars,
    warmup_event_indicators,
)
from prophitai_algo_trading.engines.backtest.models import BacktestResult
from prophitai_algo_trading.engines.data_utils import (
    align_multi_ticker_data,
    resolve_warmup,
    validate_engine_data,
)
from prophitai_algo_trading.engines.trade_routing import (
    compile_backtest_result,
    force_close_open_positions,
)
from prophitai_algo_trading.execution import CostModel
from prophitai_algo_trading.risk.base import RiskControl
from prophitai_algo_trading.risk.engine import RiskEngine
from prophitai_algo_trading.sizing import BasePositionSizer, PercentOfEquitySizer
from prophitai_algo_trading.strategies.base import BaseStrategy


class EventDrivenBacktestEngine:
    """Bar-by-bar backtest engine for a multi-ticker universe."""

    def __init__(
        self,
        strategy: BaseStrategy,
        initial_capital: float = 100_000.0,
        cost_model: CostModel | None = None,
        sizer: BasePositionSizer | None = None,
        warmup_bars: int | None = None,
        max_positions: int = 10,
        risk_controls: list[RiskControl] | None = None,
    ):
        self._strategy_template = strategy
        self.initial_capital = initial_capital
        self._cost_model = cost_model or CostModel()
        self._sizer = sizer or PercentOfEquitySizer(
            pct=1 / max_positions, 
            cost_model=self._cost_model,
        )
        self._warmup_bars = warmup_bars
        self._max_positions = max_positions
        self._risk_engine = RiskEngine(risk_controls or [])

    def run(
        self,
        data: dict[str, pd.DataFrame],
        warmup_bars: int | None = None,
        plot: bool = False,
        verbose: bool = False,
    ) -> BacktestResult:
        """Run the backtest over historical data for multiple tickers."""
        validate_engine_data(data)

        warmup = resolve_warmup(
            warmup_bars, self._warmup_bars, self._strategy_template.min_bars_required,
        )

        tickers = list(data.keys())
        common_index, aligned = align_multi_ticker_data(data)

        strategies, position_trackers, portfolio_tracker = init_event_trackers(
            self._strategy_template, tickers, self.initial_capital, self._sizer, self._cost_model,
        )

        ticker_dfs, latest_prices = warmup_event_indicators(
            tickers, aligned, strategies, warmup, verbose,
        )

        simulate_event_bars(
            common_index, aligned, tickers, strategies, position_trackers,
            portfolio_tracker, ticker_dfs, latest_prices, warmup, verbose,
            self._risk_engine, self._sizer, self._max_positions,
        )

        force_close_open_positions(
            portfolio_tracker, position_trackers, latest_prices, common_index[-1], verbose,
        )

        result = compile_backtest_result(
            portfolio_tracker, len(tickers), verbose, warmup=warmup,
        )

        if plot:
            plot_event_backtest_results(result)

        return result
