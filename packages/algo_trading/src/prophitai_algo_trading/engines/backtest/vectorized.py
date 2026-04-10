"""Vectorized backtest engine for a multi-ticker universe."""

import pandas as pd

from prophitai_algo_trading.engines.backtest.models import BacktestResult
from prophitai_algo_trading.engines.backtest.vectorized_helpers import (
    build_simulation_arrays,
    generate_vectorized_signals,
    simulate_vectorized_portfolio,
    validate_vectorized_data,
)
from prophitai_algo_trading.engines.data_utils import (
    align_multi_ticker_data,
    resolve_warmup,
    validate_engine_data,
)
from prophitai_algo_trading.engines.trade_routing import (
    compile_backtest_result,
    force_close_open_positions,
)
from prophitai_algo_trading.execution.cost_model import CostModel
from prophitai_algo_trading.sizing import BasePositionSizer, PercentOfEquitySizer
from prophitai_algo_trading.strategies.base import BaseStrategy


class VectorizedBacktestEngine:
    """Fast vectorized backtest engine for a multi-ticker universe."""

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

    def run(
        self,
        data: dict[str, pd.DataFrame],
        warmup_bars: int | None = None,
        verbose: bool = False,
    ) -> BacktestResult:
        """Run the vectorized backtest over historical data for multiple tickers."""
        validate_vectorized_data(data, self._cost_model, validate_engine_data)
        warmup = resolve_warmup(
            warmup_bars, self._warmup_bars, self._strategy_template.min_bars_required,
        )
        signal_data = generate_vectorized_signals(
            self._strategy_template, data, warmup, verbose, align_multi_ticker_data,
        )
        arrays = build_simulation_arrays(signal_data)
        portfolio_tracker, position_trackers, latest_prices = simulate_vectorized_portfolio(
            signal_data, arrays, self.initial_capital, self._sizer, self._cost_model,
            self._max_positions, verbose,
        )
        force_close_open_positions(
            portfolio_tracker, position_trackers, latest_prices, signal_data.common_index[-1],
        )

        return compile_backtest_result(
            portfolio_tracker, len(signal_data.raw_positions), verbose,
        )
