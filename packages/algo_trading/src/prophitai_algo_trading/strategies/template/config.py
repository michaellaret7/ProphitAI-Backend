"""Configuration models for the strategy scaffold."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


DEFAULT_TEMPLATE_TICKERS = (
    "AAPL",
    "MSFT",
    "NVDA",
    "GOOGL",
    "META",
    "JPM",
    "XOM",
    "PG",
)


@dataclass(frozen=True)
class TemplateStrategyConfig:
    """Strategy-local parameters the agent is expected to customize."""

    fast_ema_period: int = 20
    slow_ema_period: int = 50
    rsi_period: int = 14
    rsi_long_entry_threshold: float = 55.0
    rsi_short_entry_threshold: float = 45.0
    allow_shorts: bool = True


@dataclass(frozen=True)
class TemplateRiskControlConfig:
    """Execution-layer guardrails for the scaffold strategy."""

    enable_reentry_cooldown: bool = False
    reentry_cooldown_bars: int = 8
    enable_trailing_stop: bool = False
    trailing_stop_pct: float = 0.05


@dataclass(frozen=True)
class TemplateSizingConfig:
    """Position sizing parameters for the scaffold strategy."""

    base_equity_pct: float = 0.10
    max_equity_pct: float = 0.20
    conviction_scale: float = 2.0


@dataclass(frozen=True)
class TemplateBacktestConfig:
    """Settings shared by the event-driven and vectorized backtest runners."""

    tickers: tuple[str, ...] = DEFAULT_TEMPLATE_TICKERS
    start: datetime = datetime(2024, 1, 1)
    end: datetime = datetime(2026, 1, 1)
    interval: str = "15min"
    initial_capital: float = 100_000.0
    max_positions: int = 5
    warmup_bars: int | None = None
    plot: bool = False
    verbose: bool = True
    cost_ptc: float = 0.0005
    cost_ftc: float = 0.0


@dataclass(frozen=True)
class TemplateLiveConfig:
    """Settings for the live/paper trading runner."""

    tickers: tuple[str, ...] = DEFAULT_TEMPLATE_TICKERS
    data_interval: str = "1min"
    max_positions: int = 5
    warmup_bars: int | None = None
    paper: bool = True
    cost_ptc: float = 0.0005
    cost_ftc: float = 0.0
