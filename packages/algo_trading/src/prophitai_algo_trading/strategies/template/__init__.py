"""Canonical strategy scaffold for downstream strategy generation."""

from prophitai_algo_trading.strategies.template.config import (
    DEFAULT_TEMPLATE_TICKERS,
    TemplateBacktestConfig,
    TemplateLiveConfig,
    TemplateRiskControlConfig,
    TemplateSizingConfig,
    TemplateStrategyConfig,
)
from prophitai_algo_trading.strategies.template.strategy import TemplateStrategy
from prophitai_algo_trading.strategies.template.wiring import (
    build_broker,
    build_event_backtest_engine,
    build_live_runner,
    build_position_sizer,
    build_risk_controls,
    build_strategy,
    build_vectorized_backtest_engine,
    load_backtest_data,
)

__all__ = [
    "DEFAULT_TEMPLATE_TICKERS",
    "TemplateStrategyConfig",
    "TemplateRiskControlConfig",
    "TemplateSizingConfig",
    "TemplateBacktestConfig",
    "TemplateLiveConfig",
    "TemplateStrategy",
    "build_strategy",
    "build_position_sizer",
    "build_risk_controls",
    "build_event_backtest_engine",
    "build_vectorized_backtest_engine",
    "build_broker",
    "build_live_runner",
    "load_backtest_data",
]
