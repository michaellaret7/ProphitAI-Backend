"""Factory helpers for the strategy scaffold."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from prophitai_algo_trading.data.repository.price_data import get_price_data_df
from prophitai_algo_trading.engines import (
    EventDrivenBacktestEngine,
    VectorizedBacktestEngine,
)
from prophitai_algo_trading.execution.cost_model import CostModel
from prophitai_algo_trading.risk.base import RiskControl
from prophitai_algo_trading.strategies.template.config import (
    TemplateBacktestConfig,
    TemplateLiveConfig,
    TemplateRiskControlConfig,
    TemplateSizingConfig,
    TemplateStrategyConfig,
)
from prophitai_algo_trading.strategies.template.risk_controls import (
    build_template_risk_controls,
)
from prophitai_algo_trading.strategies.template.sizing import (
    TemplatePositionSizer,
)
from prophitai_algo_trading.strategies.template.strategy import TemplateStrategy

if TYPE_CHECKING:
    from prophitai_algo_trading.broker.alpaca import Alpaca
    from prophitai_algo_trading.engines.live import LiveRunner
    from prophitai_algo_trading.sizing.base import BasePositionSizer


# ================================
# --> Helper funcs
# ================================

def _build_cost_model(ptc: float, ftc: float) -> CostModel:
    """Build a transaction cost model from runner config values."""
    return CostModel(ptc=ptc, ftc=ftc)


def load_backtest_data(config: TemplateBacktestConfig | None = None) -> dict[str, pd.DataFrame]:
    """Fetch real OHLCV data for the scaffold backtest runners."""
    backtest_config = config or TemplateBacktestConfig()
    data: dict[str, pd.DataFrame] = {}

    for ticker in backtest_config.tickers:
        df = get_price_data_df(
            symbol=ticker,
            start_date=backtest_config.start,
            end_date=backtest_config.end,
            interval=backtest_config.interval,
        )
        if not df.empty:
            data[ticker] = df

    return data


def build_strategy(config: TemplateStrategyConfig | None = None) -> TemplateStrategy:
    """Instantiate the scaffold strategy."""
    return TemplateStrategy(config=config)


def build_position_sizer(
    config: TemplateSizingConfig | None = None,
    cost_model: CostModel | None = None,
) -> BasePositionSizer:
    """Build the default position sizer for the scaffold strategy."""
    sizing_config = config or TemplateSizingConfig()
    return TemplatePositionSizer(
        base_equity_pct=sizing_config.base_equity_pct,
        max_equity_pct=sizing_config.max_equity_pct,
        conviction_scale=sizing_config.conviction_scale,
        cost_model=cost_model,
    )


def build_risk_controls(
    config: TemplateRiskControlConfig | None = None,
) -> list[RiskControl]:
    """Build the execution-layer risk controls for the scaffold strategy."""
    return build_template_risk_controls(config or TemplateRiskControlConfig())


def build_event_backtest_engine(
    strategy_config: TemplateStrategyConfig | None = None,
    backtest_config: TemplateBacktestConfig | None = None,
    sizing_config: TemplateSizingConfig | None = None,
    risk_control_config: TemplateRiskControlConfig | None = None,
) -> EventDrivenBacktestEngine:
    """Build an event-driven backtest engine configured for the scaffold."""
    runner_config = backtest_config or TemplateBacktestConfig()
    cost_model = _build_cost_model(
        ptc=runner_config.cost_ptc,
        ftc=runner_config.cost_ftc,
    )
    return EventDrivenBacktestEngine(
        strategy=build_strategy(strategy_config),
        initial_capital=runner_config.initial_capital,
        cost_model=cost_model,
        sizer=build_position_sizer(sizing_config, cost_model),
        warmup_bars=runner_config.warmup_bars,
        max_positions=runner_config.max_positions,
        risk_controls=build_risk_controls(risk_control_config),
    )


def build_vectorized_backtest_engine(
    strategy_config: TemplateStrategyConfig | None = None,
    backtest_config: TemplateBacktestConfig | None = None,
    sizing_config: TemplateSizingConfig | None = None,
) -> VectorizedBacktestEngine:
    """Build a vectorized backtest engine configured for the scaffold."""
    runner_config = backtest_config or TemplateBacktestConfig()
    cost_model = _build_cost_model(
        ptc=runner_config.cost_ptc,
        ftc=runner_config.cost_ftc,
    )
    return VectorizedBacktestEngine(
        strategy=build_strategy(strategy_config),
        initial_capital=runner_config.initial_capital,
        cost_model=cost_model,
        sizer=build_position_sizer(sizing_config, cost_model),
        warmup_bars=runner_config.warmup_bars,
        max_positions=runner_config.max_positions,
    )


def build_broker(config: TemplateLiveConfig | None = None) -> Alpaca:
    """Build the default paper/live broker for the scaffold."""
    from prophitai_algo_trading.broker.alpaca import Alpaca

    live_config = config or TemplateLiveConfig()
    return Alpaca(paper=live_config.paper)


def build_live_runner(
    broker: Alpaca,
    strategy_config: TemplateStrategyConfig | None = None,
    live_config: TemplateLiveConfig | None = None,
    sizing_config: TemplateSizingConfig | None = None,
    risk_control_config: TemplateRiskControlConfig | None = None,
) -> LiveRunner:
    """Build a live/paper trading runner for the scaffold strategy."""
    from prophitai_algo_trading.engines.live import LiveRunner

    runner_config = live_config or TemplateLiveConfig()
    cost_model = _build_cost_model(
        ptc=runner_config.cost_ptc,
        ftc=runner_config.cost_ftc,
    )
    return LiveRunner(
        strategy=build_strategy(strategy_config),
        broker=broker,
        tickers=list(runner_config.tickers),
        sizer=build_position_sizer(sizing_config, cost_model),
        cost_model=cost_model,
        data_interval=runner_config.data_interval,
        warmup_bars=runner_config.warmup_bars,
        max_positions=runner_config.max_positions,
        risk_controls=build_risk_controls(risk_control_config),
    )
